# Spec — v1.11.0: token diet (issue #1)

## Goal
Issue #1: the plugin accounts for ~26% of the user's usage. A full feature loads ~55 KB (~14k tokens)
of instructions + checklists, re-sent on every later turn of a long session, and the reviewer loads it
again per round. About a third is duplication: `digest.py --rules` reprints the learned rules the agent
already read from core.md / domains/*.md. Cut the per-feature load without dropping any checklist item,
learned rule or hard gate.

## Actors
Main agent (loads context, writes spec, dispatches reviewer), lifecycle-reviewer subagent (loads the
same context, reviews), fallback general-purpose critic (references/review.md), the user (pays the
tokens; reads issue #1).

## A. `digest.py --context [--domains a,b] [--cwd DIR]` — one compact load
- Prints core.md, style.md and only the named domains/*.md, in that order, under `## <file>` headers.
- Learned rules print as `- [<id>] <full rule text>` (same id as `--rules`), without checkbox, scope
  tag, `_(learned …)_` or `_(reviewed …)_` stamps. Rule text is NOT truncated (`--rules` cuts at 160).
- Rules whose `[scope: X]` doesn't match DIR's project are omitted; the header says how many.
- Seed checklist items keep their text, lose the `- [ ]` box. Headings kept; blank lines dropped.
- Header line lists every available domain and which were loaded; an unknown `--domains` name prints
  `no domain file: <name>` so the agent knows to create one (SKILL §1).
- `--domains` omitted → core + style only.
- Read-only; never edits the KB. Exit 0. `--rules` stays (audit, tests, users) unchanged.
- Failure: a missing/unreadable KB file is skipped (KB is seeded by hooks; a fresh KB may lack style.md).

## B. SKILL.md split (progressive disclosure)
- SKILL.md keeps the workflow skeleton: load (one `--context` call), orient, spec sections as a short
  list, tasks/approval, implement, verify, learning, scale. Target ≤ 7.5 KB from 13.2 KB.
- Spec section detail + tasks template + portability test → `references/spec-template.md`, read in §2
  only when writing a full spec (trivial/small changes skip it).
- Nothing substantive dropped: every rule in today's SKILL.md lands in SKILL.md or the reference.

## C. Reviewer
- lifecycle-reviewer + references/review.md: load checklists via `--context --domains <given>`
  (one call) instead of reading the KB files and `--rules`; cite ids from it.
- Round 2 runs only when round 1 returned critical/high findings that were fixed, and is scoped: the
  dispatch passes round-1 findings + files changed since, the critic confirms those fixes and checks
  the touched files for regressions. PASS or only medium/low in round 1 → no round 2.
- SKILL §5 and commands/review.md say the same; the main agent passes the domains it loaded.

## Acceptance criteria
- Given the real KB in this repo's cwd, `--context --domains payments,notifications` output is ≤ 60% (measured 55%: 42 KB → 23 KB; the rest is learned-rule text itself, trimmed only by /audit)
  of the bytes of core.md + style.md + payments.md + notifications.md + `--rules` output.
- Given a rule scoped to another project, `--context` omits it and the header counts it; a rule scoped
  to an enclosing folder is shown.
- Given `--domains nope`, output contains `no domain file: nope`.
- Every learned rule id printed by `--context` (in scope) equals the id `--rules` prints for it.
- SKILL.md ≤ 7.5 KB (was 13.2 KB); references/spec-template.md exists and SKILL §2 points to it.
- Reviewer agent, references/review.md, commands/review.md and SKILL §5 all describe the conditional,
  scoped round 2 and the `--context` load; none still tell the reviewer to read core.md/style.md
  directly.
- 7 existing suites + new tests green on 3.9/3.13 CI.

## Out of scope
- Trimming the user's core.md (16 KB) — user data, `/lifecycle-guard:audit` (offered separately).
- Paid evals — run after the weekly limit resets (Nov 1); README notes it.
- Changing the reviewer model.
