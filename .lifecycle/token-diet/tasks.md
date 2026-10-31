status: done
feature: v1.11.0 token diet (issue #1)
domains: (none — plugin internals)

## Backend
- [x] digest.py --context (+ docstring)
## Skill / agent / commands
- [x] SKILL.md slimmed; references/spec-template.md
- [x] lifecycle-reviewer.md + references/review.md use --context; conditional scoped round 2
- [x] commands/review.md round-2 rule
## Tests
- [x] tests/test_context.py (sizes, scope omit, unknown domain, id parity, SKILL size + pointers)
## Docs / ops
- [x] CHANGELOG, plugin CLAUDE.md, README if it mentions loading, version 1.11.0, byte measurement
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
