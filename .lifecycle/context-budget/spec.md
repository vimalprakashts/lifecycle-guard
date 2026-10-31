# Spec — v1.12.0: context diet + budget guard (issue #1, round 2)

## Goal
v1.11 cut the duplicate load; the user asked for the minimum context without losing quality, and for a
guard so the plugin never drifts back. Applies: index + fetch on demand (Code Mode / search_tools detail
levels), filtering in code, progressive disclosure, just-in-time instructions, disposable-context
subagents for heavy loads, and write-time budgets on the knowledge base (the real growth source: 28 of
61 rules > 250 chars; core.md 15.6 KB vs a 12 KB budget that only warned).

## Actors
Builder agent (loads the index, fetches rules), reviewer subagent (loads `--full`), the user (pays;
runs /audit, /lg-status), /learn (auto + interactive), the correction hook, CI (budget test).

## Behaviour
- `--context`: domain-file rules in full; core/style learned rules as `[id] headline …` when the rule is
  > 120 chars (first ≤100 chars cut at a word). Header tells the builder to fetch the full text of every
  headline that touches the feature with `--rule`. `--full` prints all in full (reviewer).
- `--rule id[,id]`: full text + file + scope; unknown id → `no rule with id X (…rerun --context)`.
- `--lint-rules`: `too-long <id> file:line N/250` and `over-budget <file>`; `ok: …` when clean; exit 0.
- `--audit`: new `too-long` flag + header count. `rule_max_chars` config (default 250).
- `--footprint`: builder load (core+style), with all domains, reviewer load, rule count/KB, top 3 longest.
- Commands audit/bootstrap/lg-status: `disable-model-invocation: true`. learn stays model-visible
  (auto-learn runs `claude -p /lifecycle-guard:learn auto`; hiding it risks silently breaking that).
- Correction note ≤ 700 B incl. the ≤250-char rule instruction; SKILL "Learning" is self-contained.
- /learn step 8: lint; shorten own too-long rules; over-budget → interactive merge proposals, auto mode
  never merges existing rules unattended (reports + suggests /audit).
- review.md format moved into references/spec-template.md (SKILL pointed at a command file before).

## Failure / edge cases
- Builder skips fetching a relevant headline → the reviewer has every rule in full (`--full`) and FAILs
  the learned-rule gate; the miss is caught at review, not lost.
- A rule ≤ 120 chars prints whole (no "…"), so short rules never need a fetch.
- A reworded rule changes id → `--rule` says so and points to rerunning `--context`.
- `disable-model-invocation` unknown to an older Claude Code → ignored (field silently ignored), the
  command stays visible: no breakage, just no saving.

## Acceptance criteria
- Given the real KB, `--context --domains payments,notifications` ≤ 16 KB (measured 15.8; v1.10 42 KB).
- Given the 60-rule fixture, builder load (1 domain) ≤ 9,000 B, reviewer `--full` > 1.5× builder,
  an unloaded domain absent, and `--rule <id>` returns the untruncated text.
- Always-on model-visible descriptions ≤ 1,450 B; audit/bootstrap/lg-status hidden.
- Each hook note ≤ 700 B at the real KB path; SKILL ≤ 7,200 B; spec-template ≤ 4,800 B.
- A > 250-char rule → `--lint-rules` prints `too-long`; `--audit` header `too-long: 1`.
- All suites green; CHANGELOG 1.12.0 = plugin.json.

## Added during build: automated sessions never feed learning (user request)
- Write time: on_prompt returns before logging or nudging when `CLAUDE_CODE_ENTRYPOINT` starts with
  `sdk-` (`claude -p` → sdk-cli, Agent SDK → sdk-ts/sdk-py; verified in the Claude Code 2.1.316 binary).
  Interactive surfaces (`cli`, `claude-vscode`, `claude-desktop`, unset) unchanged. New records store
  `entrypoint`. Config `learn_from_automated` (default false) opts back in.
- Read time (`user_records`, used by /learn and --stats): skip a record whose `entrypoint` is sdk-*;
  for older records, look up the session transcript's entrypoint; with no transcript, skip only if the
  cwd is under the system temp dir. Bootstrap skips transcript lines with an sdk-* entrypoint.
- Known limits (accepted): a person typing into a third-party app built on the Agent SDK reports
  `sdk-ts`/`sdk-py` and isn't learned from — documented in README + /lg-status, opt in with the config. A
  legacy record (no `entrypoint`) whose transcript was cleaned up and whose cwd is under the system temp
  dir is dropped; `/tmp` is not treated as temp (people work there). New records carry `entrypoint`.
- Acceptance: sdk-cli/ts/py prompt → nothing logged, no output; cli/vscode/desktop/unset correction →
  logged with entrypoint; opt-in logs; legacy records: sdk transcript dropped, cli kept, temp-dir
  no-transcript dropped, non-temp no-transcript kept. Real KB: 21 prompts + 1 correction dropped.

## Out of scope
- Rewording the user's 28 long rules (user data → /lifecycle-guard:audit; offered).
- Spec drafting in a subagent (quality risk; eval experiment later).
- Shortening the skill / review descriptions (routing tuned by evals).
- Paid evals: after the weekly limit resets; release should wait for them or ship and measure.
