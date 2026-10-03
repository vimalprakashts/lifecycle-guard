status: done
feature: filter system-injected text out of learning input

## Backend
- [x] digest.py: clean_prompt() + single CORRECTION regex; use in since_last, stats, bootstrap
- [x] on_prompt.py: import shared clean_prompt/CORRECTION; skip empty; log cleaned text
- [x] lg_common.count_since: ignore records whose cleaned prompt is empty
## Tests
- [x] tests for hook + digest read-time filtering + bootstrap
## Ops / docs
- [x] CLAUDE.md note, version 1.6.1
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
