status: done
feature: rule provenance, scoping & review

## Backend
- [x] lg_common: project_of(cwd) + review_after_days default
- [x] on_prompt.py: inject concrete origin project into rule format
- [x] digest.py: --audit (markdown + --json), lenient parser, flags no-origin/stale/looks-project-specific
- [x] digest.py --bootstrap: origin from transcript cwd
## Commands / skill
- [x] learn.md + bootstrap.md: new format, origin, scoping guidance
- [x] new commands/audit.md (keep/scope/drop, backup, changelog, reviewed stamp)
- [x] lg-status.md: audit counts
- [x] SKILL.md + reviewer agent + references/review.md: honour [scope: …], new format
## Tests
- [x] scripted test of parser/flags on a temp KB (LG_DATA_DIR) + hook output
## Ops / docs
- [x] README, plugin CLAUDE.md, version 1.6.0
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
