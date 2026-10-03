status: done
feature: v1.8.0 hardening (gate tests, project identity, log retention, duplicates/size, changelog)

## Tests
- [x] A: tests/test_stop_gate.py — all gate cases; fix any bug found
## Backend
- [x] B: digest project_name (git root) + project_scopes; --project; --rules N/A marking; wire hook/usage/bootstrap
- [x] C: log retention (SessionEnd + --prune-logs), never prune unlearned records, atomic
- [x] D: possible-duplicate flag + kb size budget in audit; config keys
## Commands / skill
- [x] skill + reviewer + rubric: use --rules N/A marking / --project for scope
- [x] audit.md merge action; lg-status mentions size/duplicates
## Tests
- [x] tests for B, C, D
## Ops / docs
- [x] CHANGELOG.md, CONTRIBUTING, README config table, plugin CLAUDE.md, version 1.8.0
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
