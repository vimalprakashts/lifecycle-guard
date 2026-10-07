# Spec — v1.9.0: spec-slop check, CI hardening, PRIVACY.md

## Goal
Stop "looks done but isn't" at the source: a spec line that could be pasted unchanged into any
feature's spec ("handle errors gracefully", "ensure security", "notify the user") is easy to tick
and specifies nothing. Adopted from no-ai-slop's portability test. Also pin CI actions to commit
SHAs, validate the plugin's manifests/frontmatter in CI, and document privacy in PRIVACY.md.

## Actors
Main agent (writes spec/tasks, runs the lint), reviewer (judges, reports `spec-slop` findings),
/learn + correction hook (write rules), CI (system), contributors/users (read PRIVACY.md).

## A. Spec-slop
- `digest.py --lint-spec <file>...` (deterministic, read-only): flags lines containing vague
  phrases (`gracefully, properly, correctly, appropriately, as needed, if necessary, robust,`
  `seamless, user-friendly, intuitive, best practices, all edge cases, edge cases handled, etc.,`
  `and so on, various, TBD/TODO/???`, "ensure security/secure", "handle errors", "notify the user"
  without a channel…). Output: `file:line — "<phrase>" — <what to name instead>` + count; exit 0
  always (advisory). Ignores fenced code blocks, headings, and checklist-coverage `N/A` lines.
- SKILL §2: after writing spec.md + tasks.md, apply the portability test and run the lint; rewrite
  each hit to name the concrete actor / state / trigger / channel / error / limit.
- Reviewer hard gate **Spec specificity**: acceptance criteria and failure/edge-case lines must be
  specific to THIS feature; generic lines = `spec-slop` finding quoting the line and what's missing.
  FAIL only when an acceptance criterion or failure case is generic (they're what gets ticked).
- Rubric (fallback reviewer) gets the same gate.
- Rules (/learn, correction hook, SKILL learning, CONTRIBUTING): portable across projects but
  specific about the failure — name the situation, the miss, and the check.

## B. CI hardening
- Pin `actions/checkout` and `actions/setup-python` to the commit SHAs of the majors already used
  (v4, v5), version in a trailing comment. Major upgrades are a separate decision.
- `tests/test_manifest.py` (runs in the existing CI loop): plugin.json has name/version(semver)/
  description/author; marketplace.json lists every plugin dir with a matching `source`; every
  command has frontmatter `description`; every agent has `name`/`description`/`tools`; hooks.json
  scripts exist; SKILL.md has name/description; CHANGELOG top version == plugin.json version.

## C. PRIVACY.md
What is stored (prompts, corrections, usage, changelog, backups), where (~/.claude/lifecycle-guard),
what's filtered (pasted text, system-injected messages), retention (180 days, never before learned),
what leaves the machine (nothing, except the background learner's normal Claude API call, which
sends the digest to Anthropic like any Claude Code session), how to delete. Linked from README.

## Failure / edge cases
Lint false positives (e.g. "correctly" in a quoted error message) → advisory only; reviewer judges.
Lint on missing file → message, exit 0. Unicode/CRLF → handled. Pinned SHA must equal the tag's
commit (verified via API at authoring time).

## Cross-cutting
Extends digest.py, reviewer agent, rubric, SKILL, learn/hook text, CI workflows, tests, docs.
No new hook; no gate behaviour change (the Stop gate stays deterministic on boxes + verdict).

## Acceptance
- Given a spec with "Handle errors gracefully" under Failure cases, `--lint-spec` reports that line
  with the phrase and a hint; a line naming "gateway timeout → order stays pending_payment, retry
  job after 5 min" is not reported.
- Lines inside ``` fences and headings are ignored.
- test_manifest fails if a command loses its description or CHANGELOG/plugin.json versions diverge.
- Workflows reference actions only by 40-hex SHA.
- README links PRIVACY.md; PRIVACY.md states retention and what leaves the machine.

## Out of scope
Blocking the Stop gate on lint hits; action major-version upgrades; cross-agent packaging.
