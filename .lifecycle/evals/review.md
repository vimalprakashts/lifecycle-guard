# Review — behavioural eval suite (v1.10.0)

VERDICT: PASS
Reviewed: 2026-10-29 · rounds: 2

## Findings addressed
- [high] spec-first `file_exists` always passed because the fixture's own spec was copied in. Fix: the scaffold drops `.lifecycle/`.
- [high] The control fixture wasn't clean: stub tests, unused settings, "team alerted" not implemented, one order's cap used for every row.
  - Fix: the fixture now has a refund window enforced, alerts and emails on both failure paths, per-row caps, real assertion tests, an admin list endpoint with `?status=`, and a customer request form.
  - The control was redefined as false alarms on the 7 planted dimensions, because a rigorous review always finds other gaps in a toy fixture.
- [medium] The README didn't say routing graders count under `--ablation none`. Now documented.
- [medium] The review command over-routed, and it edited code on "is it done?" questions. It is now scoped to `.lifecycle` features, not general or PR review, and reports and offers fixes when the user only asked a question. Verified in a run.
- [medium] 8 of 9 cases had never run. All 9 now validated end to end (plugin arm, sonnet judge).
- [low] The spec-first rubric now uses refund-only gateway wording and accepts stock that's addressed or deferred. The grader reads the spec file.
- [low] Test support files added. The harness omission is stated in the fixture's CLAUDE.md.
- [low] customer-visibility now removes only the refund list, not the request form.
- [self-found] An earlier routing regex matched the session-init tool listing, a false PASS. Replaced with `tool_used`.
- [self-found] The default haiku judge misgraded long reviews, failing all 3 on runs a sonnet judge passed 3 of 3. The README requires `--judge-model sonnet`.
- [self-found] The `llm` grader key `target` was invalid (`focus`); the file focus doesn't take globs.

## Known gaps (deferred)
- The with/without baseline (≈54 sessions, ≈$15–25) has not been run. It needs the user's go-ahead. Until then the suite shows the plugin catches these gaps, not how much more than plain Claude.
- A small fixture means reviews legitimately report other gaps. The control tolerates them by design.

## Rules applied
- 20cd2a90 caught — validating end to end exposed the false-PASS regex, the haiku judge, the always-passing file_exists and the untouched spec-first case
- 09ddc2c3 satisfied — the reject action is wired in the control; unwired-endpoint encodes the rule
- 3de05c35 satisfied — the review command change is description and step-3 text only; unit tests green
- 9b09bd45 satisfied — the eval suite is the automatic quality gate for future prompt changes

## Evidence
- Unit tests: 7 suites OK.
- Eval validation (plugin arm, sonnet judge): 7/7 planted gaps found and routed; control 2/2 after fixes; spec-first 1.00; customer-visibility (narrowed) 1.00.
- Total eval spend while building: $15.56.
