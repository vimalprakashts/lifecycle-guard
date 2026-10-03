# Spec — rule usage tracking (lifecycle-guard v1.7.0)

## Goal
Know which learned rules actually earn their place. Every review records which rules it applied and
whether each one caught a miss; the audit uses that so proven rules aren't nagged and rules that are
never applied surface for keep/scope/drop.

## Actors
Reviewer agent (read-only; reports rules applied), main agent (writes review.md), Stop hook (system;
ingests usage deterministically), user (runs /audit, /lg-status), background learner (rewords rules).

## Data
- Rule id = first 8 hex of sha1(normalized rule text: scope/stamps stripped, whitespace collapsed,
  lowercased). `digest.py --rules` lists `id · file:line · [scope] · rule` for the reviewer.
- review.md gains:
  ```
  ## Rules applied
  - <id> caught — <what it caught>
  - <id> satisfied
  ```
  (only rules relevant to the feature; N/A rules omitted)
- `~/.claude/lifecycle-guard/usage.jsonl`: `{ts, rule, outcome: caught|satisfied, project, feature, review}`
  where `review` = sha1(project path + feature + sorted parsed rules) for idempotency (prose edits
  don't recount; a re-review that changes the rules list is new evidence). `ts` = review.md mtime.

## State
Rule usage: never-applied → applied (satisfied) → proven (caught ≥1). Freshness age = days since
max(learned, reviewed, last applied); stale only when that exceeds review_after_days.

## Behaviour
- Stop hook: on every run, scans `.lifecycle/*/review.md` (any status), parses `## Rules applied`,
  appends unseen records. Never blocks because of this; any error is swallowed (fail-safe).
- Audit JSON/markdown: `id`, `applied`, `caught`, `last_applied`; line shows `applied N× (caught M)`.
- /lg-status: top rules by catches, count never applied.
- Reviewer agent + fallback rubric + /review + SKILL §5: run `digest.py --rules`, report the section.
- /audit: shows usage evidence; reword note that history resets (new id).

## Failure / edge cases
- Decorated ids (`**id**`, `[id]`, `id (core.md:55) — caught`) parsed leniently.
- Unknown id in review.md (rule since reworded/dropped) → stored anyway; ignored by audit join.
- Malformed lines → skipped. Reviews with no Rules applied section → skipped (cheap re-check each Stop).
- Repeated Stop runs → deduped by review hash. No `.lifecycle` → no-op.
- Two rules with identical text → same id (they're duplicates; audit already exposes them).
- usage.jsonl missing → zero usage, no crash.

## Cross-cutting
Placement: extends existing digest.py (ids, --rules, join), on_stop.py (ingest), reviewer/rubric/commands
docs. One new data file in the KB (local only). Privacy: stores project basename + feature slug only.

## Checklist coverage
Same rule across entry points ✓ (one id function, used by --rules, --audit, ingest join). Migration ✓
(no format change; old rules simply have zero usage). Verify end-to-end ✓ (hook → usage → audit test).
UI/tenant/payments N/A.

## Acceptance
- Given review.md with `## Rules applied` listing an id caught, when Stop runs twice, then usage.jsonl
  has exactly one record for it with outcome caught.
- Given a rule learned 200d ago, applied 10d ago, then not stale and shows `applied 1× (caught 1)`.
- Given a rule learned 200d ago, never applied/reviewed → stale.
- `--rules` ids equal `--audit --json` ids.

## Out of scope
Automatic dropping; usage weighting/decay; tracking rules applied during build (only reviews count).
