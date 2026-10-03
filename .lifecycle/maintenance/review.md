# Review — v1.8.0 hardening

VERDICT: PASS
Reviewed: 2026-10-03 · rounds: 2

## Findings addressed
- [high, self-found via new tests] on_stop.py — draft with a task mentioning "status: active" was treated as active → header-line STATUS regex.
- [high, self-found] on_stop.py — unedited `VERDICT: PASS | FAIL` template / prose "verdict: pass" unlocked the gate → VERDICT_OK line regex.
- [medium] audit.md — over-budget file alone never reached consolidation → step 1 continues when a file is over budget.
- [medium] on_stop.py — `> status:` / `- status:` / `**Status:**` headers stopped counting → decorated headers accepted, tasks still rejected (tested).
- [low] prune_logs — records without a numeric ts were pruned; invalid UTF-8 aborted pruning → kept; errors="replace" (tested).
- [low] audit.md merge — earliest learned date + both original lines logged verbatim.
- [low] exact duplicates showed a self-reference → "exact duplicate" line.
- [low, self-found] exact duplicates were never flagged (same id excluded) → fixed (tested).
- [low, self-found] audit header had a blank line after the title, so /lg-status would only read the title → header is one block (tested).

## Known gaps (deferred)
- A bullet `- status: active` in a file with no real header would count as the header — very unlikely shape.
- Symlinked cwd and the real path get different labels; lru_cache per short-lived hook process — harmless.

## Rules applied
- 763dcc8a caught — over-budget consolidation missing was another occurrence of the same concern
- 9b09bd45 satisfied — gate enforced by hook and pinned by tests
- a9bcdcc5 satisfied — no unbuilt items ticked
- 3de05c35 satisfied — existing suites still green
- 6f3c32cd satisfied — extends existing files, no new surface
- 7d994649 satisfied — duplicate threshold and size budget calibrated on the real KB
- f260dfa2 satisfied — no raw-basename labels left
- 20cd2a90 satisfied — real --audit / --rules output exercised

## Evidence
`for t in plugins/lifecycle-guard/tests/test_*.py; do python3 $t; done` → 9 + 14 + 8 + 7 + 15 = 53 tests OK.
