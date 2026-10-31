# Spec — v1.12.0: the knowledge base stays in budget automatically

## Goal
The plugin ships to other users, so budget upkeep can't depend on anyone running /audit. Every rule a
model writes (in-the-moment learning, /learn) can be too long; old KBs from earlier versions are too long
already. Fix it automatically, cheapest and safest layer first, never destroying a lesson unattended.

## Actors
SessionEnd hook (deterministic upkeep + spawns background run), the background `claude -p /learn auto`
(rewords), the prompt hook (weekly reminder), the user (merges via /audit), CI (seed + budget tests).

## Behaviour
1. `digest.maintain()` at every SessionEnd, no model: causes > 80 chars trimmed at a word boundary + " …"
   (backup `*.maintain.bak`, original logged in changelog.md); rule ids/text untouched. Records
   `kb_too_long` (ids) and `kb_over_budget` (files) in config.json.
2. (Corrected by the v1.12 hardening: the background run is read-only and returns a JSON proposal that
   `lg-digest.py --apply-proposal` applies — Claude Code blocks unattended writes under ~/.claude.)
   If `auto_learn` and `kb_too_long` non-empty and `last_compact_ts` older than 24 h → spawn
   `/lifecycle-guard:learn auto` even with nothing new (same lock); set `last_compact_ts` first, so a rule
   the model can't shorten doesn't loop. learn.md: zero new material + lint not ok → compaction run;
   the budget step rewords EVERY too-long rule with `_(was id)_`; never merges or drops unattended.
3. `kb_over_budget` non-empty → prompt hook adds one line suggesting /lifecycle-guard:audit, at most
   once per 7 days (`last_budget_nudge_ts`), ≤ 700 B like every hook note.
4. Seed core.md ≤ 6 KB and every seed file ≤ 6 KB (CI), so new users start inside the budget.
5. count_since ignores automated (sdk-*) records, so tool prompts can't trigger background runs.

## Failure / edge cases
- `claude` not on PATH / lock held → no run; maintain still ran; next session retries (throttle allows).
- Background run fails or can't shorten a rule → retried at most daily (no loop, bounded cost).
- auto_learn off → only the deterministic layer + reminder; documented (README/PRIVACY).
- Cause trimming loses detail → original line in changelog.md + backup; provenance only.
- maintain raises → caught; session end continues (hooks never break a session).

## Acceptance criteria
- A long cause → trimmed at SessionEnd with auto_learn off; rule id unchanged; original in changelog;
  backup exists; no model run.
- A clean KB → files unchanged, no maintain changelog entry, `kb_too_long` = [].
- A too-long rule with nothing new to learn → exactly one background `/learn auto` run; a second
  SessionEnd the same day → none.
- Over budget → reminder on the first prompt, not on the second, again after 8 days; ≤ 700 B.
- Seed files within caps. All suites green.

## Out of scope
Unattended merges/drops (destructive; stay user-confirmed in /audit).
