status: done
feature: v1.12.0 hardening (review + debate findings)
domains: (none — plugin internals)

## Backend (digest.py)
- [x] C0 --apply-proposal (validate, backup, add/reword/cause, was-stamp, verbatim log, id check + rollback, cursor mark)
- [x] #1/#11 maintain guards + malformed flag; #2 symlink/mode-safe atomic writes; #4 kb_budget guard
- [x] #5 --full loads all domains; #8/#10 domains parsing; #12 --rule was ids; #13 abspath cwd
- [x] #14/#15 TEMP_ROOTS without /tmp; #16 VERSION + unknown-flag exit; #20 digest cap + cursor
## Hooks
- [x] C0/C1 on_session_end: automated sessions upkeep-only, attempt backoff, proposal wrapper
- [x] #16 lg_common: bin/lg-digest.py, no downgrade; save_config symlink/mode-safe
- [x] #4/#7/#21 on_prompt: isolated reminder, ~ paths, was in note, stacked ≤ 700 B
- [x] #19 on_stop reason caps
## Prose
- [x] learn.md auto = proposal JSON; interactive backup/snapshot first; verbatim log (#3/#9)
- [x] #6 round-2 gate + verbatim verdict (SKILL, commands/review.md, references/review.md, template)
- [x] #5 reviewer prompts; #7 SKILL strengthen; #16 lg-digest path everywhere + stale-copy note
- [x] #0/#18 seed core.md rules + causes
- [x] #17 release-notes.sh from CHANGELOG
## Tests
- [x] one regression test per finding (19/20 fail on the old code); suite green on macOS + TMPDIR=/tmp — Linux container blocked: the Colima VM has no route to Docker Hub; GitHub CI runs Linux 3.9/3.13 on push
## Docs
- [x] CHANGELOG, README, PRIVACY, plugin CLAUDE.md, specs corrected (context-budget mitigation, kb-autofix)
## Review
- [x] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
