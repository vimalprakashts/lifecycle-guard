# Review — context-budget
VERDICT: PASS
Reviewed: 2026-10-31 · rounds: 1 + 1 scoped round for the automated-session fix added mid-build (both PASS, medium/low only → no round 2)
## Findings addressed
- [medium] SKILL.md — headline fetch is unverifiable → spec coverage ends with `Rules fetched: <ids>`; reviewer --full remains the net
- [medium] CLAUDE.md vs learn.md — "never read KB files" now excepts /learn and /audit (they edit them)
- [low] test_budget — 30-char project fixture; bytes not chars; multi-line descriptions fail
- [low] lg-status separator; review.md format points to the template; --rule usage line + exact-id match; rule_max() tolerates bad config; /learn lints before the changelog so shortened rules are logged
- [medium] automated sessions: SDK-app users get no learning silently → README + /lg-status say so, opt-in documented
- [medium] lg_common fallback ignored the opt-in → reads config.json; tested via a forced broken import
- [medium] /tmp false positives → TEMP_ROOTS is the system temp dir only; limitation recorded in the spec
- [low] garbled config comment; string "false" no longer opts in; unreadable transcript treated as missing; tests for opt-in at read time, odd session ids, bootstrap skipping sdk lines
## Known gaps (deferred)
- Behavioural evals of the index+fetch builder vs v1.10 baseline — paid; after the weekly limit resets (Nov 1).
- The user's 28 too-long rules and core.md over budget — user data; /lifecycle-guard:audit.
- Spec drafting in a disposable subagent — experiment, eval-gated.
## Rules applied
- 9b09bd45 satisfied
- 3de05c35 satisfied
- 87bbc6b3 satisfied
