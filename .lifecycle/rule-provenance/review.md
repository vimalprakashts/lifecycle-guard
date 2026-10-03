# Review — rule provenance, scoping & review (v1.6.0)

VERDICT: PASS

Reviewer: lifecycle-reviewer (fresh context), 2 rounds.

## Round 1 — FAIL (findings addressed)
- [high] Origin containing `)`/`:` silently dropped from audit → lenient origin regex + `malformed` flag; never drop.
- [high] Unstamped rules skipped → unstamped bullets under `## Learned` audited as `no-origin`; seed checklist items declared out of scope (spec §5).
- [medium] Generic basenames (test/config/rule) flagged project-specific → stoplist + project must appear in 2+ prompts.
- [medium] HOSTNAME matched `1.5.com`, `example.com` → alphabetic last label + placeholder-host skip.
- [medium] audit.md edit ambiguity → single reviewed stamp, full-text logging of drop/reword, drops confirmed individually, headless = report only.
- [low] Double spaces in rule text → whitespace collapsed.
- [low] Stale `bin/digest.py` after update → audit.md falls back to `${CLAUDE_PLUGIN_ROOT}/scripts/digest.py`.

## Round 2 — PASS
- [low] fixed: unknown age printed as `age unknown`.
- [low] deferred: a rule body containing a literal `)_` before its stamp could truncate the cause. Not observed in the real KB; the stamp is always the trailing element by format.

## Evidence
`python3 plugins/lifecycle-guard/tests/test_provenance.py` → 8 tests OK. Live KB audit: 42 rules parsed, 1 flagged project-specific (a rule naming one project's test tenant), 0 false positives.
