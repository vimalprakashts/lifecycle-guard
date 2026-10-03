# lifecycle-guard — project guide (CLAUDE.md)

A Claude Code **plugin** that stops AI coding agents from declaring work "done" when
only the happy path is built. It forces a full-lifecycle spec up front, **blocks
completion** until a checklist is satisfied, runs an **independent fresh-context critic
on a different model**, and **learns** new checklist/style rules from your own
corrections over time.

> Thesis (the "Beyond the Happy Path" idea): an agent grading its own work in the same
> session says "done" too early. The fix is three layers that don't share the agent's
> blind spots — a deterministic gate, a different-model critic in fresh context, and a
> checklist that accumulates from real past misses.

- **Plugin root:** `~/claude-plugins/vimal-tools/plugins/lifecycle-guard/` (this dir).
- **Marketplace repo:** `~/claude-plugins/vimal-tools/` (`.claude-plugin/marketplace.json` lists this plugin).
- **Version:** `1.5.0` (see `.claude-plugin/plugin.json`).
- **Author:** Vimal Prakash. Runtime: Python 3 hooks + Markdown skill/agent/commands. No build step.

---

## The three mechanisms

1. **Spec-first workflow (the skill).** On a feature request, the agent writes
   `.lifecycle/<slug>/spec.md` (actors, state machine, per-actor capabilities, failure
   paths, cross-cutting) and a `tasks.md`, then implements against them. See
   `skills/lifecycle-guard/SKILL.md`.

2. **Deterministic Stop gate (no LLM).** `hooks/on_stop.py` refuses to let the turn end
   while an **active** `tasks.md` has open `- [ ]` items, and — even when all are ticked —
   until a `review.md` with `VERDICT: PASS` (or `review: deferred`) exists. This is plain
   Python/regex: it shares zero blind spots with any model and can't be rationalized past.

3. **Independent critic (fresh context, different model).** `agents/lifecycle-reviewer.md`
   is a read-only skeptic (`model: sonnet`, tools `Read/Grep/Glob/Bash`) that reviews a
   just-built feature against its spec + checklists and returns ranked findings. It runs
   on a **different model** than the builder (builder is whatever the main session uses,
   typically Opus) and never sees the build's own reasoning. The main agent fixes; the
   critic never edits.

The role/model pairing is a dial: bigger-builder→smaller-critic (current) or
smaller-builder→bigger-critic both decouple blind spots. The deterministic layer is the
true-independence floor; the critic is the last mile for what tests can't encode.

---

## Repository layout

```
.claude-plugin/plugin.json        name/version/description/author (version lives here)
agents/lifecycle-reviewer.md      the critic subagent (model: sonnet, read-only)
commands/
  audit.md                        /lifecycle-guard:audit [all] — review rules: keep/scope/reword/drop
  bootstrap.md                    /lifecycle-guard:bootstrap — seed KB from ALL past sessions
  learn.md                        /lifecycle-guard:learn [auto] — distill recent prompts/corrections
  lg-status.md                    /lifecycle-guard:lg-status — show learned rules + pending tasks
  review.md                       /lifecycle-guard:review [slug] — run the critic + write verdict
hooks/
  hooks.json                      registers UserPromptSubmit / Stop / SessionEnd
  lg_common.py                    shared helpers: data dir, config, seeding, jsonl logging
  on_prompt.py                    UserPromptSubmit: log prompt, detect correction/feature, nudge
  on_stop.py                      Stop: the definition-of-done gate (see above)
  on_session_end.py               SessionEnd: auto-run /learn in the background when enough piled up
scripts/digest.py                 prepares raw material for /learn (also --bootstrap/--mark/--stats/--audit/--rules/--usage/--project/--prune-logs/--ingest-usage)
skills/lifecycle-guard/
  SKILL.md                        the full-lifecycle workflow the agent follows
  references/review.md            review rubric the critic/`/review` uses
  seed/core.md                    universal checklist — SEED copied to the KB on first run
  seed/style.md                   style/conventions seed
  seed/domains/{auth,notifications,payments}.md  domain checklists seed
tests/test_provenance.py          stdlib unittest: hook origin + audit flags (temp LG_DATA_DIR)
tests/test_prompt_noise.py        stdlib unittest: injected/pasted text never feeds learning
tests/test_rule_usage.py          stdlib unittest: rule ids, Stop-hook usage ingest, audit freshness
tests/test_stop_gate.py           stdlib unittest: every Stop gate case (boxes, review, status, guards)
tests/test_maintenance.py         stdlib unittest: project identity + nested scopes, retention, dupes/size
```

### Important: learned data lives OUTSIDE the plugin
So it survives plugin updates, the knowledge base is at **`~/.claude/lifecycle-guard/`**
(override with `LG_DATA_DIR`). `lg_common.ensure_data_dir()` seeds it from
`skills/lifecycle-guard/seed/` on first run and re-copies `scripts/digest.py` → `bin/digest.py`
on every run so updates propagate.

```
~/.claude/lifecycle-guard/
  core.md            universal lifecycle checklist (seeded, then grows via /learn)
  style.md           your stack/conventions/preferences (learned from prompts)
  domains/*.md       per-domain checklists (payments, auth, notifications, …); auto-created
  prompts.jsonl      every prompt you type (raw material for style learning)
  corrections.jsonl  prompts that look like "you missed X" (raw material for gap rules)
  usage.jsonl        which learned rules each review applied (caught | satisfied), from review.md
  changelog.md       every change /learn made (audit + revert reference)
  backups/           file snapshots taken before each learn
  bin/digest.py      copy of scripts/digest.py (fixed path for commands)
  config.json        toggles + thresholds + last-learn timestamp
  bootstrap/         chunked past-session material (created by digest --bootstrap)
```

`core.md`, `style.md`, and `domains/*.md` each carry a `## Learned` section; items there
are mandatory — each exists because something was missed before, formatted
`- [ ] [scope: <project>] <rule> _(learned YYYY-MM-DD @ <project>: <cause>)_ _(reviewed YYYY-MM-DD)_`.
`@ <project>` = origin (`digest.project_name`: the enclosing git repo's folder name, else the cwd's
name — folder names, not remotes, so labels stay stable); `[scope: X]` (optional) = applies where X is
the project or any enclosing folder below $HOME (`digest.project_scopes`), so an umbrella-folder
scope covers its nested repos; `digest.py --rules` marks the rest `N/A here` (skill + reviewer rely on
that, not prose matching); `_(reviewed …)_` (optional) = last audit keep.
Legacy rules without `@ project` still parse — `digest.py --audit` flags them `no-origin`. The
audit also flags `stale` (older than `review_after_days`, default 90), `looks-project-specific`
(unscoped but names a project from `prompts.jsonl` or a hostname) and `possible-duplicate` (word-set
Jaccard ≥ `duplicate_threshold`, default 0.5 — the real KB's max is ~0.17, so it only fires on true
re-writes; conceptual overlap is /audit's consolidate step), and warns when a file exceeds
`kb_budget_kb` (12). The audit header is one block ending in a blank line — `/lg-status` reads it
with `sed -n '1,/^$/p'`, so never insert a blank line inside it. `/lifecycle-guard:audit` turns
the report into keep / scope / reword / drop decisions (user-confirmed, backed up, changelogged).
**Usage:** a rule's id = first 8 hex of sha1(normalized text) (`digest.py --rules`); rewording gives a
new id, so history restarts (fail-safe: worst case one extra review). The reviewer reports
`RULES APPLIED`, the main agent copies it into review.md `## Rules applied`, and `on_stop.py` ingests it
(`digest.ingest_usage`, idempotent per project|feature|parsed-rules key — prose edits don't recount,
and a re-review listing identical rules+outcomes isn't new evidence; `ts` = review.md mtime; runs
before the loop guard, never affects the gate). Audit freshness = days since max(learned, reviewed, last applied).

---

## Per-feature artifacts (created in the CONSUMER project, not here)

When the plugin is active in some other repo, a feature produces `.lifecycle/<slug>/`:

- **`spec.md`** — goal, actors, entity state machine, per-actor capabilities, failure/edge
  cases, cross-cutting (perms, tenant isolation, audit, notifications, reporting), checklist
  coverage, acceptance criteria, out-of-scope, plus placement/reuse + business-rules sections.
- **`tasks.md`** — header `status: draft|active|done` + checkboxes grouped by area
  (Backend / Customer UI / Admin UI / System-jobs-webhooks / Notifications / Tests / Ops).
  `- [ ]` open, `- [x]` done+verified, `- [~] item — reason` deferred. The Stop gate reads this.
- **`review.md`** — the critic's verdict. Must contain `VERDICT: PASS` (or `review: deferred`)
  before the Stop gate lets the feature be marked done.

Lifecycle of a feature: draft spec+tasks → user approves → `status: active` → implement,
ticking boxes → run critic → fix findings → write `review.md` PASS → `status: done`.

---

## Hooks — exact behavior

- **UserPromptSubmit → `on_prompt.py`** (never blocks): appends the prompt to
  `prompts.jsonl`; if it matches the CORRECTION regex ("you missed / forgot / where is the /
  not done / half-done…") it logs to `corrections.jsonl` and tells the agent to write the
  lesson into the right checklist now; if it matches the FEATURE regex it reminds the agent
  to run the lifecycle workflow. Gated by `feature_nudge`.
- **Stop → `on_stop.py`**: first ingests rule usage from `.lifecycle/*/review.md` (fail-safe), then the gate described above. Guards against infinite loops via
  `stop_hook_active`; respects `stop_gate` config; only fires on active features.
- **SessionEnd → `on_session_end.py`**: if `auto_learn` is on and enough new
  corrections/prompts accumulated since `last_learn_ts` (thresholds in config), spawns a
  **headless** `claude -p /lifecycle-guard:learn auto` run (`LG_HEADLESS=1`, a `.learn.lock`
  file prevents overlap, output to `learn.log`). It edits only files under the KB.

`LG_HEADLESS=1` makes hooks no-op so the background learner can't recurse.

---

## The learning loop

Raw material (`prompts.jsonl` + `corrections.jsonl`) → `scripts/digest.py` formats what's new
since the last learn → `/lifecycle-guard:learn` distills it into `## Learned` rules in
`core.md` / `domains/*.md` (or style rules in `style.md`), backs up first, logs to
`changelog.md`, then `digest.py --mark` records the timestamp. `--bootstrap` mines *all*
past sessions in `~/.claude/projects` into `bootstrap/` chunks for a one-time seed.

Two ways it grows: **in the moment** (a correction → the agent appends a generalized rule
immediately, prompted by `on_prompt.py`) and **in the background** (`on_session_end.py`).

---

## config.json toggles (in the KB, not the plugin)

```
auto_learn                     (true)  run /learn in background at session end
auto_learn_min_corrections     (2)     threshold to trigger background learn
auto_learn_min_prompts         (40)    alternative threshold
stop_gate                      (true)  block "done" while tasks.md has open boxes / no PASS
feature_nudge                  (true)  inject the lifecycle reminder on feature-like prompts
last_learn_ts                  (0)     bookkeeping
```

Defaults live in `lg_common.DEFAULT_CONFIG`; `config.json` overrides them.

---

## Working on this plugin

- **Edit the skill/agent/commands/hooks here;** they take effect on `/reload-plugins` (or a new
  session). The knowledge base in `~/.claude/lifecycle-guard/` is user data — don't ship it in
  the plugin; only `skills/lifecycle-guard/seed/` ships and seeds it.
- **Bump `version` in `.claude-plugin/plugin.json`** on a meaningful change (history: 1.2.0
  entity-coverage → 1.3.0 entity cross-links on every page → 1.4.0 orient-before-building /
  no-duplicate-surface → 1.5.0 business-logic reconciliation → 1.6.0 rule provenance, scoping + /audit → 1.6.1 learn only from the user's own words → 1.7.0 rule usage tracking → 1.8.0 gate tests + fixes, git-root identity, retention, dupes/size;
  full history in the repo-root `CHANGELOG.md`).
- **Releases are automatic:** a version bump merged to `main` triggers `.github/workflows/release.yml`
  (tests → `v<version>` release, notes = bump commit body + commits since last tag). CI
  (`.github/workflows/test.yml`) runs the tests on every push/PR on Python 3.9 and 3.13.
- **Run the tests** before committing: `for t in plugins/lifecycle-guard/tests/test_*.py; do python3 $t; done`.
  `digest.py` honours `LG_DATA_DIR` too, so tests never touch the real KB.
- **Hooks must stay fast and fail-safe** — each wraps `main()` in try/except and prints nothing
  on error (a crashing hook must never break the user's turn). Keep them dependency-free (stdlib
  only) and under the configured timeouts (10–15s).
- **`scripts/digest.py` is the source of truth**; it's copied to `~/.claude/lifecycle-guard/bin/`
  on every hook run, so edit it here, not there. It also owns `clean_prompt()` (what the user
  actually typed: drops `<task-notification>`/`<system-reminder>`/command blocks, `<pasted_content>`
  and `[Image #N]` placeholders) and the single `CORRECTION` regex; the hooks import both via
  `lg_common` (with a safe fallback so a broken import never disables the Stop gate). Old log
  records are filtered at read time — never rewrite the user's jsonl files.
- **Changing seed files** only affects NEW installs (existing KBs already copied them). To push a
  rule to existing users, it has to go through `/learn` or they re-seed.

## Gotchas

- The Stop gate keys off `status: active` in `tasks.md`. A `draft` or `done` feature won't block.
  A feature with all boxes ticked but no `review.md` PASS **still blocks** — that's intentional.
- Deferring is first-class: `- [~] item — reason` satisfies the gate. Don't fake `- [x]`.
- The critic is read-only by design. If it could edit, it would stop being an independent check.
- Project identity is the git root's **folder name** (no subprocess; walks up for `.git`, stopping at
  $HOME). Two repos with the same folder name share a label. Good enough for review and scoping;
  don't build security decisions on it.
- Log retention: SessionEnd prunes `prompts.jsonl`/`corrections.jsonl` older than
  `log_retention_days` (180) but never past `last_learn_ts`, and keeps unparseable lines.
  `usage.jsonl` and `changelog.md` are never pruned.
- The Stop gate reads the `status:` **header line** and a filled-in `VERDICT: PASS` **line** (regexes
  `STATUS` / `VERDICT_OK` in on_stop.py) — a phrase inside a task or the unedited `PASS | FAIL`
  template must not count. `tests/test_stop_gate.py` pins every gate case.
- Everything the hooks log is the user's own prompt text — treat the KB as sensitive (it may
  contain project details); it stays local under `~/.claude/`.
