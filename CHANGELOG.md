# Changelog

All notable changes to lifecycle-guard. Releases: https://github.com/vimalprakashts/lifecycle-guard/releases

## 1.12.0 — 2026-10-31
**Context diet** ([#1](https://github.com/vimalprakashts/lifecycle-guard/issues/1): the plugin was ~26%
of a heavy user's usage). Applies the context techniques from Anthropic's "code execution with MCP" /
Agent Skills posts and Cloudflare's Code Mode: load an index, fetch detail on demand, filter in code,
disclose progressively, and send instructions just in time. Measured on a 61-rule knowledge base:

| Load | 1.10.0 | 1.12.0 |
|---|---|---|
| Checklists, builder (2 domains) | 42 KB (KB files + `--rules`, rules twice) | 15.8 KB |
| `SKILL.md` | 13.2 KB | 7.0 KB (+ 4.5 KB template, read only for a full spec) |
| Always-on descriptions | 1,647 chars every turn | 1,430 |
| Correction note | 1,001 chars | ~630 |

- `digest.py --context --domains a,b`: one compact, de-duplicated load. Domain rules in full; core and
  style rules as a headline index, full text on demand with `--rule <id>,<id>`; `--full` for the
  reviewer, whose context is discarded after the review. Stamps stripped, out-of-scope rules dropped.
- `SKILL.md` keeps the workflow; spec sections, tasks/review templates and the portability test moved to
  `references/spec-template.md`.
- Reviewer round 2 only after critical/high findings, scoped to those fixes. `tasks.md` gains `domains:`.
- **Write-time budget:** rules stay ≤ `rule_max_chars` (250) — `/learn` and the correction note enforce
  it, `digest.py --lint-rules` checks it, `/audit` flags longer rules `too-long`; `/learn` handles
  over-budget files (interactively merges; unattended, reports). `/lg-status` shows `--footprint`.
- `/audit`, `/bootstrap`, `/lg-status` are `disable-model-invocation`: user-only, so their descriptions
  no longer sit in every session's context. `/learn` stays visible (auto-learn runs it headless).
- **Fix: automated sessions no longer feed learning.** Prompts from `claude -p` and Agent SDK sessions
  (`CLAUDE_CODE_ENTRYPOINT=sdk-*`: another plugin's summarizer, an app backend, a script) were logged as
  the user's prompts — one, "You are a memory consolidation agent…", was logged as a *correction*. The
  prompt hook now skips them (no log, no nudge); `/learn` and `/bootstrap` ignore old ones at read time
  (transcript entrypoint, or no transcript + the system temp dir; `/tmp` is not treated as temp) without rewriting the logs. On a real KB:
  21 tool prompts and 1 false correction dropped, all 669 interactive prompts kept. Opt back in with
  `learn_from_automated: true`.
- **Budget guard:** `tests/test_budget.py` caps every tier (always-on text, hook notes, SKILL, template,
  fallback prompt, builder load on a 60-rule fixture). CI fails on growth past a budget.

## 1.10.0 — 2026-10-29
- **Behavioural evals** (adopting "measure first" from Anthropic's article on folding subagents into the
  main loop): `plugins/lifecycle-guard/evals/` holds 9 golden cases for `claude plugin eval`: seven
  planted-gap reviews, a clean control, and spec-before-code. Each runs with and without the plugin.
  See `evals/README.md`.
- **Review routing fix, found by those evals**: asking "is this feature actually done?" never reached the
  plugin's reviewer (0/3); Claude reviewed alone. The `/lifecycle-guard:review` description now describes
  when to use it in users' terms, and routing went to 3/3. The routed reviews found the planted gap 3/3
  and three real defects plain Claude missed. The command is now scoped to features with a `.lifecycle`
  spec (not general code or PR review). When the user only asks whether a feature is done, it reports
  findings and offers to fix them instead of editing.
- Eval finding: the default eval judge (haiku) misgrades long, multi-finding reviews; use
  `--judge-model sonnet`.

## 1.9.0 — 2026-10-07
- **Spec-slop check** (the portability test, adapted from petergyang/no-ai-slop): a requirement that
  could be pasted unchanged into any feature's spec ("handle errors gracefully", "notify the user",
  "all edge cases covered") is easy to tick while work is half done. New `digest.py --lint-spec`
  flags the common phrasings in a spec's requirement sections; the reviewer gains a **Spec
  specificity** hard gate (generic acceptance criteria or failure cases fail the review); the skill
  applies the test before showing a spec, and learned rules must name a concrete failure.
- One shipped seed item rewritten ("skip gracefully" → skip that recipient, log it, keep sending).
- CI: GitHub Actions pinned to commit SHAs; new manifest test validates plugin/marketplace manifests,
  command/agent/skill frontmatter, hook wiring, SHA pinning, and that CHANGELOG matches plugin.json.
- `PRIVACY.md`: what's stored, retention, what leaves the machine, how to delete.
- 72 tests.

## 1.8.1 — 2026-10-03
- The knowledge base's `bin/digest.py` is refreshed on every prompt, including slash commands. Before,
  running `/lifecycle-guard:audit` right after `/plugin update` used the previous version's script.

## 1.8.0 — 2026-10-03
- **Stop gate fixes** (found by the new gate test suite): a draft whose task text mentioned
  `status: active` was treated as active; an unedited `VERDICT: PASS | FAIL` template, or "verdict: pass"
  in prose, unlocked the gate. The gate now reads the `status:` header line and a filled-in verdict line.
- **Project identity**: a project is labelled by its git repo's folder name, so sessions started in a
  subfolder (`src/`, `apps/ui`) get the repo's name. `[scope: X]` now also covers repos nested under a
  folder named X, and `digest.py --rules` marks rules scoped elsewhere `N/A here`. New `--project`.
- **Log retention**: prompt/correction logs older than `log_retention_days` (180) are pruned at session
  end, never before they've been learned from. New `--prune-logs`.
- **Audit**: `possible-duplicate` flag for rules written twice, a knowledge-file size budget
  (`kb_budget_kb`, 12 KB), and a consolidate/merge step for conceptually overlapping rules.
- Tests: Stop gate (15) and maintenance (9) suites; 53 tests total, run in CI.

## 1.7.0 — 2026-10-03
- Rule usage tracking: reviews list the learned rules they applied (`caught` / `satisfied`), the Stop
  hook records them, and the audit shows `applied N× (caught M)`. Used rules stay fresh. `--usage`.

## 1.6.1 — 2026-10-03
- Learn only from the user's own words: task notifications, system reminders, pasted text and image
  placeholders no longer feed correction detection or style learning. Old log records filtered on read.

## 1.6.0 — 2026-10-03
- Rule provenance: every learned rule records when, where (origin project) and why; `[scope: project]`;
  `/lifecycle-guard:audit` for keep / scope / reword / drop with backups and changelog.

## 1.5.0
- Every new value, default or limit is reconciled with existing business rules.

## 1.4.0
- Orient before building: extend the existing page/route/tab instead of adding a parallel one.

## 1.3.0
- Call-to-action coverage on every page: entity references link to the entity's own page.

## 1.2.0
- `/lifecycle-guard:review` and a committed `review.md` the Stop gate requires before "done".

## 1.1.0
- Enforced independent reviewer (fresh-context critic on a different model) with CTA-coverage review.

## 1.0.0 — 2026-10-01
- First public release: spec-first workflow, Stop gate, self-learning checklists and style memory.
