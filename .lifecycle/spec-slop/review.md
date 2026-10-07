# Review — v1.9.0 spec-slop check, CI hardening, PRIVACY.md

VERDICT: PASS
Reviewed: 2026-10-07 · rounds: 2

## Findings addressed
- [medium] digest.py QUOTED — two apostrophes on a line ("user's … admin's") were read as a quoted span and hid real slop → single-quote span needs non-word chars around it (tested).
- [medium] digest.py REQUIREMENT_SECTIONS — substring match let "Stateless design" / "Statement" headings enable linting → word-bounded (tested).
- [low] `/etc/hosts` flagged as "etc" → path-aware pattern (tested).
- [low] PRIVACY.md — states prompt logs keep the full working-directory path and usage records a project-path hash.
- [low] test_manifest frontmatter parsing normalises CRLF (verified by hand).
- [self-found while dogfooding] the plugin's own seed checklist had "skip gracefully" → rewritten; a test keeps all seeds lint-clean.
- [self-found] narrative sections (Goal, Root cause) produced a false positive on a real CrackersCity spec → lint only requirement sections when a spec has them.

## Known gaps (deferred)
- Advisory, line-based lint: "notify the user via" + "email" on the next line is still flagged; "a TODO app" is flagged. Documented in plugins/lifecycle-guard/CLAUDE.md.
- Actions pinned to the majors in use (checkout v4, setup-python v5); upgrading to v7 is a separate change.

## Rules applied
- 1faadcdf satisfied — --lint-spec, gate wording and docs consistent across every file that defines them
- 9b09bd45 satisfied — manifest/SHA checks automatic in CI; lint deliberately advisory, gate is the reviewer's
- 3de05c35 satisfied — existing suites green; Stop gate behaviour unchanged

## Evidence
`for t in plugins/lifecycle-guard/tests/test_*.py; do python3 $t; done` → 72 tests OK (7 suites).
--lint-spec on 12 real CrackersCity specs + 6 plugin specs + all seed checklists → 0 hits.
Manifest test mutation-checked: broken version and missing command description both fail.
