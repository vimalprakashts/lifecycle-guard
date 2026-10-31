---
name: lifecycle-guard
description: Full-lifecycle definition-of-done for building any feature end to end — customer side, admin side, system/background jobs, webhooks, failure paths, notifications, reporting, security, tests. Use this whenever the user asks to build, implement, add, integrate or extend a feature, module, flow, screen, API, integration or workflow (payments, auth, onboarding, orders, uploads, notifications, dashboards, CRUD modules, etc.), even if they phrase it casually or only mention one side of it. Also use when the user complains that something is half done, missing pieces, or not handled.
---

# Lifecycle Guard

You tend to build the happy path for one actor and stop. This skill makes you design the whole lifecycle first, build against a checklist, and get blocked by a Stop hook until the checklist is done. The checklists grow from the user's own corrections; they live in `~/.claude/lifecycle-guard/` (`core.md`, `style.md`, `domains/<domain>.md`).

## Scale to the request

For a trivial tweak (rename a label, fix a typo, change a color), skip all of this. For a small change inside an existing feature, append a short section to that feature's `spec.md` and add a few tasks. The full workflow is for anything with new states, actors or integrations.

## Workflow

### 1. Load context + ORIENT (silently, FIRST)

`ls ~/.claude/lifecycle-guard/domains/`, pick the domains the request touches (a "subscription renewal" needs `payments` and `notifications`), then load everything in ONE call — don't read the KB files separately:

`python3 ~/.claude/lifecycle-guard/bin/digest.py --context --domains payments,notifications`

It prints core + style + those domains, each learned rule as `[id] text`, and omits rules scoped to other projects. Learned rules are mandatory: each exists because it was missed before. If one obviously doesn't fit this codebase, follow the safer reading and suggest `/lifecycle-guard:audit` in one line. If it prints `no domain file: <name>`, create `domains/<name>.md` from your domain knowledge in the shape of the existing ones, header `> seeded by Claude — unverified`. Also read the project's `CLAUDE.md`, and apply the style rules throughout.

**Then orient against what already exists, before the spec.** Your job is to put new things in the RIGHT existing home, not build a parallel one:

- **Routes / nav / menus / settings tabs** — grep the router and nav lists; know every existing page.
- **The natural home** — the existing page, tab, section, modal, list or report where this belongs (a new AI toggle goes on the existing AI settings page, not a new tab). Read that surface's code.
- **Existing endpoints / services / DTOs / settings** that already do part of this — extend, don't duplicate.
- **Existing business rules** the feature touches — min/max order value, qty limits, pricing/discount tiers, tax, stock thresholds, delivery eligibility, coupons, rounding. Every value you introduce (default, preset, limit, threshold) must be consistent with them; never pick a number in isolation.
- When placement isn't obvious, list the routes/tabs with one line each and pick the fit.

A NEW top-level surface (nav item, route, settings tab, page, endpoint) where an existing one is the natural home is a red flag. Decide here, and record placement + reuse in the spec.

### 2. Write the spec

Read `references/spec-template.md` (next to this file) and write `.lifecycle/<feature-slug>/spec.md` from it: goal, actors, state machine, per-actor capabilities + CTAs and entity links, failure cases, cross-cutting (incl. placement & reuse and business-rule reconciliation), checklist coverage, acceptance criteria, out of scope. Apply its portability test and run its `--lint-spec` command before showing the spec.

### 3. Write tasks and get approval

Write `.lifecycle/<feature-slug>/tasks.md` from the same template (it includes the mandatory **Review** task and a `domains:` line). Show the user a short summary (actor count, states, task count, notable N/A decisions) and ask for approval once; if they already said to proceed, don't wait. On approval set `status: active` — from then on the Stop hook won't let you finish while any `- [ ]` remains.

### 4. Implement

Work task by task. Tick a box only when the code exists and a test covers it. If an item truly can't be done now (credentials, a product decision, a later phase), mark it `- [~] <item> — <reason>`; never fake `- [x]`.

### 5. Verify — enforced independent review

Self-review is not enough; you miss the same things twice. A separate reviewer in a fresh context MUST run before anything is called done.

1. Run the tests and linters; fix failures.
2. **Round 1:** dispatch the `lifecycle-reviewer` agent (no plugin agents? spawn a fresh general-purpose subagent with `references/review.md`). Pass the spec/tasks paths, the changed files, and the `--domains` you loaded — paths, not file dumps, not the whole repo. It returns `VERDICT` + ranked findings + `RULES APPLIED`.
3. **Fix** every critical/high finding (and cheap mediums). A fix that reflects a reusable lesson also goes through "Learning in the moment".
4. **Round 2 only if round 1 had critical/high findings.** Dispatch it scoped: the round-1 findings, what you changed for each, and the files touched since. It confirms those fixes and checks the touched files for regressions. Never a third round; anything left is reported to the user as a known gap.
5. Write `.lifecycle/<feature>/review.md` (format in `/lifecycle-guard:review`) with the verdict, findings addressed, deferred gaps and the critic's `## Rules applied` list (merge rounds; `caught` wins). The Stop hook records rule usage and requires `VERDICT: PASS` (or `review: deferred — <reason>`) before `status: done`.
6. **Definition of done** — paste evidence, don't claim it: run the build, tests and linter and paste their literal output. A failing suite fixes the CODE, never the test. Only when all are green, the review is PASS (or deferred) and every box is ticked or `- [~]`, set `status: done` and summarise for the user, including deferred items and known gaps.

If browser/E2E tooling is available, click the feature's primary CTAs to confirm each lands on the correct pre-filtered actionable view — a CTA that opens a generic page is a FAIL.

## Learning in the moment

When the user points out something missing or wrong (a hook flags it too):

1. Fix it and add it to the active `tasks.md`.
2. Generalize it into a rule — portable across projects (no project names) but specific about the failure: the situation, the miss, the check. "You didn't add refund on admin panel" → "Admin can initiate full and partial refunds with reason; refund state reflected to customer." Append under `## Learned` in the right domain file, or `core.md` if it applies to any feature, as `- [ ] <rule> _(learned YYYY-MM-DD @ <project>: <cause>)_` (`<project>` from `digest.py --project`). If it only holds in this project (names its tenants, hosts, paths), prefix `[scope: <project>]`, or an enclosing folder's name if it holds for every repo under it.
3. Style or convention ("use zod not yup") → `style.md` instead.
4. If an equivalent rule exists, strengthen its wording instead of duplicating it.

Mention the learning in one short line.
