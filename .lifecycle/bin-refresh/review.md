# Review — refresh bin/digest.py before slash commands (v1.8.1)

VERDICT: PASS
Reviewed: 2026-10-03 · rounds: 1

## Findings addressed
- [low] headless guarantee unpinned → test: LG_HEADLESS=1 leaves the KB untouched.

## Known gaps (deferred)
- [low] bin/digest.py is copied on every prompt even when unchanged (~30 KB) — accepted in the spec.

## Rules applied
- 3de05c35 satisfied — slash commands still not logged or nudged; normal prompts unchanged
- 1faadcdf satisfied — every ensure_data_dir caller (on_prompt, on_session_end) checked
- 9b09bd45 satisfied — refresh is automatic in the hook, not left to the agent

## Evidence
New test fails without the fix (verified by stashing it) and passes with it; 55 tests OK across 5 files.
