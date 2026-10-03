# Review — CI tests + automatic releases

VERDICT: PASS

Reviewer: lifecycle-reviewer (fresh context), 2 rounds.

## Round 1 — FAIL (findings addressed)
- [medium] "v1.6.1 tag missing" → false positive (tag exists on remote; reviewer's clone hadn't fetched). Spec acceptance clarified.
- [medium] Manual dispatch could publish from any branch → publish requires `refs/heads/main`.
- [medium] Concurrency group could drop a queued bump run → group removed; duplicate run fails on existing tag; manual-dispatch recovery documented.
- [low] Values interpolated into `run:` → passed via `env`.
- [low] Case-sensitive trailer filter → `grep -viE`, guarded for empty body under pipefail.
- [low] Wrong bump commit if plugin.json edited later → pickaxe on the exact version string, with fallback.
- [low] Release tested on one Python only → reusable `test.yml` matrix gates the release (`needs: tests`).
- [low] Tests ran twice for PR branches → `push` limited to main.

## Round 2 — PASS
- [nit] accepted: notes "since" range uses `git describe HEAD^` — correct behaviour.

## Evidence
- tests run on push afbb3c0: 3.9 success, 3.13 success.
- release dispatch dry_run run 37120009850: tests 3.9/3.13 success → "Tag v1.6.1 already exists, nothing to release." → Publish step skipped.
- release-notes.sh verified in a scratch repo: empty body, description-only later edit, trailers.
