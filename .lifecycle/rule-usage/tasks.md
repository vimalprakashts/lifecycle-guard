status: done
feature: rule usage tracking

## Backend
- [x] digest.py: rule_id(), --rules, usage join in audit (applied/caught/last_applied, freshness)
- [x] on_stop.py: ingest `## Rules applied` from .lifecycle/*/review.md into usage.jsonl (idempotent, fail-safe)
## Agent / commands
- [x] reviewer agent + references/review.md: run --rules, output Rules applied section
- [x] commands/review.md + SKILL.md §5: review.md template includes Rules applied
- [x] commands/audit.md + lg-status.md: show usage evidence
## Tests
- [x] tests/test_rule_usage.py: ids, ingest idempotency, audit join + freshness
## Ops / docs
- [x] README, plugin CLAUDE.md, version 1.7.0 (commit body = release notes)
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
