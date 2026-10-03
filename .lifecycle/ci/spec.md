# Spec — CI tests + automatic releases

## Goal
Every push/PR runs the plugin's stdlib test suites; merging a `plugin.json` version bump to `main`
publishes the matching GitHub release automatically, so releases can't fall behind `main` again
(v1.1–1.6 were never released until done by hand).

## Actors
Maintainer (pushes, bumps version), contributor (opens PRs), GitHub Actions (system), plugin users
(see "Latest" release).

## States (release)
version bumped on main → tests pass → tag `v<version>` absent → release created (Latest).
Tag already exists → skip (idempotent). Tests fail → no release. Manual `workflow_dispatch` with
`dry_run` → print notes only.

## Behaviour
- `test.yml`: on push + pull_request; matrix Python 3.9 / 3.13; runs `tests/test_*.py`; fails on any
  failure (no `|| true`). No secrets, read-only permissions.
- `release.yml`: on push to main touching `plugins/lifecycle-guard/.claude-plugin/plugin.json`, plus
  `workflow_dispatch` (dry_run default true). Runs tests first. Reads version from plugin.json;
  if tag exists → skip. Notes = bump commit's message body + commit subjects since the previous tag +
  upgrade block. `permissions: contents: write` only on this job.

## Failure / edge cases
Version unchanged but file touched → tag exists → skip. Malformed plugin.json → job fails loudly.
Several commits in one push → tag on the pushed head (`github.sha`). First tag missing → notes list
all commits. No concurrency group (it would drop queued runs); two racing runs for one version →
the second `gh release create` fails on the existing tag (no duplicate). A missed run → manual
dispatch on main. Publishing only from `refs/heads/main`. Release gated on the full test matrix
(reusable `test.yml`).

## Cross-cutting
Placement: new `.github/workflows/` (none existed). Docs: CONTRIBUTING "Releasing", plugin CLAUDE.md.
Security: GITHUB_TOKEN only, least privilege; third-party actions limited to official `actions/*`.

## Acceptance
- Push → test workflow green on both Pythons.
- dispatch dry_run → notes printed, no release created.
- Existing tag (v1.6.1) → release job skips (verified via dry-run dispatch, which also prints notes).

## Out of scope
Linting, multi-plugin releases (only lifecycle-guard exists), changelog file.
