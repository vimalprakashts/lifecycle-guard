status: done
feature: v1.12.0 automatic KB budget upkeep
domains: (none — plugin internals)

## Backend
- [x] digest.maintain() + --maintain; config keys; count_since skips automated records
- [x] on_session_end: maintain, throttled compaction spawn
- [x] on_prompt: weekly over-budget reminder
## Commands
- [x] learn.md: compaction run; reword every too-long rule with was-stamp in auto mode
## Tests
- [x] tests/test_autofix.py; seed caps in test_budget.py
## Docs
- [x] CHANGELOG, plugin CLAUDE.md, README, PRIVACY
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
