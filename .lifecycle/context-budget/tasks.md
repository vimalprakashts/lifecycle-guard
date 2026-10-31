status: done
feature: v1.12.0 context diet + budget guard
domains: (none — plugin internals)

## Backend
- [x] digest.py headline index, --full, --rule, --lint-rules, --footprint, audit too-long, rule_max_chars
## Skill / agent / commands / hooks
- [x] SKILL index+fetch, self-contained learning; review.md format → spec-template
- [x] reviewer + fallback use --context --full
- [x] learn.md write-time budget; audit.md too-long; lg-status footprint; hide audit/bootstrap/lg-status
- [x] correction note shortened (≤250-char rule instruction)
## Tests
- [x] tests/test_budget.py; test_context updated
## Docs / ops
- [x] CHANGELOG 1.12.0 (absorbs unreleased 1.11.0), plugin.json, CLAUDE.md budget table, README, CONTRIBUTING
## Automated sessions (added)
- [x] on_prompt skip + entrypoint field; digest is_automated / automated_record / bootstrap filter; config
- [x] tests (AutomatedSessions); docs: CHANGELOG, README, PRIVACY, CLAUDE.md
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
