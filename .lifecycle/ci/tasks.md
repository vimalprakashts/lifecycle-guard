status: done
feature: CI tests + automatic releases

## System / jobs
- [x] .github/workflows/test.yml (push + PR, py 3.9/3.13)
- [x] .github/workflows/release.yml (version bump → tests → release; idempotent; dry-run dispatch)
- [x] release notes script tested locally against real history
## Ops / docs
- [x] CONTRIBUTING "Releasing" + plugin CLAUDE.md note
- [x] push; verify test run green on GitHub; verify dry-run dispatch
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
