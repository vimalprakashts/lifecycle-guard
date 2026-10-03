# Review — filter system-injected text out of learning input (v1.6.1)

VERDICT: PASS

Reviewer: lifecycle-reviewer (fresh context), 2 rounds.

## Round 1 — FAIL (findings addressed)
- [medium] Nested/multiple pasted blocks leaked text → innermost-first loop, stray closing tags, unclosed-to-end.
- [medium] Compaction summary + IDE/hook tags not filtered → MACHINE_TAGS / MACHINE_TEXT lists.
- [medium] Bootstrap path + import fallback untested; since_last only negative asserts → bootstrap e2e (temp HOME), broken-digest fallback test (on_prompt + on_stop), positive digest asserts.
- [low] `missing.` / end-of-text recall lost → bare `missing`.
- [low] Leading system-reminder dropped trailing user text → leading machine blocks peeled, user text kept.
- [low] Fallback silent → writes `hook-errors.log`; `sys.path.append` instead of insert.
- [low] Double spaces after paste removal → whitespace collapsed.

## Round 2 — PASS
- [low] accepted: bare `missing` favours recall over precision; corrections are re-checked after cleaning.
- [low] accepted: only LEADING machine blocks are peeled (the harness injects at the front).

## Evidence
`for t in plugins/lifecycle-guard/tests/test_*.py; do python3 $t; done` → 14 + 8 tests OK.
Live KB (read-only): corrections 11 → 5, prompts 87 → 61 after read-time filtering.
