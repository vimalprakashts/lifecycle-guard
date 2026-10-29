# Spec — behavioural eval suite (lifecycle-guard v1.10.0)

## Goal
Adopt step 1 of "Building agents: when to fold subagents into your main agent loop": measure before
changing. The 72 unit tests cover the plumbing; nothing measures whether the reviewer catches a real
gap or whether the skill produces a complete spec. Add a golden set run by `claude plugin eval`, with
the default no-plugin baseline arm, so every later prompt change (e.g. trimming SKILL.md) is judged
against numbers.

## Actors
Maintainer (runs the suite locally; decides on prompt changes), `claude plugin eval` (runs each case
3× with and without the plugin, grades), the reviewer agent and skill (under test).

## Cases (fixture: a tiny shop app with a refunds feature, spec + tasks + code)
Reviewer, one planted gap each — graded on whether the review names that gap:
1. customer-visibility — refund status visible to admin only
2. generic-cta — "pending refunds" tile links to the unfiltered orders list
3. plain-entity — order number rendered as plain text in the refunds table
4. spec-slop — acceptance criteria / failure cases are generic phrases
5. unwired-endpoint — reject endpoint exists, no reject action in the admin UI
6. business-rule — refund presets exceed the amount paid (spec says refund ≤ paid)
7. parallel-surface — new top-level "Refund settings" tab while the existing Payments settings page holds refund config
Control:
8. complete-feature — the same feature with no planted gap; graded on NOT claiming a blocking gap
Skill:
9. spec-first — "add order cancellation" → a spec with actors, states, concrete failure cases and
   acceptance criteria is written before any code

## Behaviour
- Fixtures live in `evals/_fixtures/shop/`; each case's `scaffold.sh` copies it and applies its one
  planted change. Requires `--scaffold` (documented in evals/README.md).
- Prompts are generic ("is this feature done?"), so the baseline arm is a fair comparison.
- Graders: `llm` rubric naming the specific gap (both arms); `regex` on verdict where useful.
- `evals/results/` git-ignored. Suite is NOT run in CI (each run is a paid model session).

## Failure / edge cases
Scaffold failure → run scores 0 with "scaffold failed" (visible). A case where both arms pass → the
plugin adds nothing for that gap (useful finding, not a bug). Flaky case (passes 1 of 3) → reported
as a fractional score, which is the point of runs=3.

## Cross-cutting
Cost: 9 cases × 3 runs × 2 arms = 54 sessions; README documents `--case`, `--runs 1`,
`--ablation none` and `--max-cost-usd` for cheaper runs. No plugin runtime behaviour changes.

## Acceptance
- `claude plugin eval plugins/lifecycle-guard --scaffold --case customer-visibility --runs 1
  --ablation none` completes and grades (validation run).
- Every case's scaffold produces the fixture with exactly its planted change (checked locally).
- README explains how to run, cost, and how to read the with/without delta.

## Out of scope
Prompt trimming (the article's step 2 — done later, measured against this suite); hook-level cases
(the eval harness doesn't document hook events).
