---
name: lifecycle-guard
description: Full-lifecycle definition-of-done for building any feature end to end — customer side, admin side, system/background jobs, webhooks, failure paths, notifications, reporting, security, tests. Use this whenever the user asks to build, implement, add, integrate or extend a feature, module, flow, screen, API, integration or workflow (payments, auth, onboarding, orders, uploads, notifications, dashboards, CRUD modules, etc.), even if they phrase it casually or only mention one side of it. Also use when the user complains that something is half done, missing pieces, or not handled.
---

# Lifecycle Guard

You tend to build the happy path for one actor and stop. Design the whole lifecycle first, build against a checklist, and a Stop hook blocks you until it's done. The checklists grow from the user's corrections and live in `~/.claude/lifecycle-guard/`.

## Scale to the request

For a trivial tweak (rename a label, fix a typo, change a color), skip all of this. For a small change inside an existing feature, append a short section to that feature's `spec.md` and add a few tasks. The full workflow is for anything with new states, actors or integrations.

## Workflow

### 1. Load context + ORIENT (silently, FIRST)

`ls ~/.claude/lifecycle-guard/domains/`, pick the domains the request touches (a subscription renewal needs `payments`, `notifications`), then load everything in ONE call, never the KB files separately:

`python3 ~/.claude/lifecycle-guard/bin/lg-digest.py --context --domains payments,notifications`

It prints core + style + those domains, minus rules scoped to other projects. Learned rules (`[id] …`) are mandatory: each was missed before. Domain rules print in full, core/style ones as headlines: read every one that touches this feature in full with `lg-digest.py --rule <id>,<id>` before writing the spec. No `[id]` rules, `# Digest since`, or an unknown-flag error means a stale copy: use the plugin's `scripts/digest.py` — never go on without the rules. If a rule obviously doesn't fit this codebase, follow the safer reading and suggest `/lifecycle-guard:audit`. On `no domain file: <name>`, create `domains/<name>.md` like the others, header `> seeded by Claude — unverified`. Read the project's `CLAUDE.md`; apply the style rules throughout.

**Then orient against what already exists, before the spec.** Your job is to put new things in the RIGHT existing home, not build a parallel one:

- **Routes / nav / menus / settings tabs** — grep the router and nav lists; know every existing page.
- **The natural home** — the existing page, tab, section, modal, list or report where this belongs (an AI toggle goes on the AI settings page, not a new tab). Read its code.
- **Existing endpoints / services / DTOs / settings** that already do part of this — extend, don't duplicate.
- **Existing business rules** the feature touches — min/max order value, qty limits, pricing/discount tiers, tax, stock thresholds, delivery eligibility, coupons, rounding. Every value you introduce (default, preset, limit, threshold) must be consistent with them; never pick a number in isolation.
- Placement unclear? List the routes/tabs, one line each, and pick the fit.

A NEW top-level surface (nav item, route, settings tab, page, endpoint) where an existing one is the natural home is a red flag. Decide here, and record placement + reuse in the spec.

### 2. Write the spec

Read `references/spec-template.md` (next to this file) and write `.lifecycle/<feature-slug>/spec.md` from it: goal, actors, state machine, per-actor capabilities + CTAs and entity links, failure cases, cross-cutting (incl. placement & reuse and business-rule reconciliation), checklist coverage, acceptance criteria, out of scope. Apply its portability test and run its `--lint-spec` command before showing the spec.

### 3. Write tasks and get approval

Write `.lifecycle/<feature-slug>/tasks.md` from the same template (it includes the mandatory **Review** task and a `domains:` line). Show a short summary (actors, states, tasks, notable N/A decisions) and ask for approval once, unless they already said to proceed. On approval set `status: active` — from then on the Stop hook won't let you finish while any `- [ ]` remains.

### 4. Implement

Tick a box only when the code exists and a test covers it. An item that truly can't be done now (credentials, a product decision, a later phase) becomes `- [~] <item> — <reason>`; never fake `- [x]`.

### 5. Verify — enforced independent review

Self-review misses the same things twice: a fresh-context reviewer MUST run before "done".

1. Run the tests and linters; fix failures.
2. **Round 1:** dispatch the `lifecycle-reviewer` agent (no plugin agents? spawn a fresh general-purpose subagent with `references/review.md`). Pass the spec/tasks paths, the changed files, and the `--domains` you loaded (a hint: it loads every rule of every domain, in full; its context is discarded afterwards) — paths, not file dumps, not the whole repo. It returns `VERDICT` + ranked findings + `RULES APPLIED`.
3. **Fix** every critical/high finding and every finding that opens a hard gate (whatever its severity), plus cheap mediums. A fix that reflects a reusable lesson also goes through "Learning in the moment".
4. **Round 2 if round 1 returned FAIL or you changed code for any finding.** Dispatch it scoped: the round-1 findings, what you changed for each, and the files touched since. It confirms those fixes and checks the touched files for regressions. Skip it only when round 1 was PASS and you changed nothing. Never a third round.
5. Write `.lifecycle/<feature>/review.md` (format in `references/spec-template.md`): the critic's LAST verdict verbatim (never your own), findings addressed, deferred gaps and the critic's `## Rules applied` list (merge rounds; `caught` wins). If the last round is still FAIL, write `review: deferred — <reason>` and list the open gaps for the user. The Stop hook records rule usage and requires `VERDICT: PASS` (or `review: deferred — <reason>`) before `status: done`.
6. **Definition of done** — paste the literal output of the build, tests and linter; don't claim it. A failing suite fixes the CODE, never the test. Only when all are green, the review is PASS (or deferred) and every box is ticked or `- [~]`, set `status: done` and summarise, incl. deferred items and known gaps.

If browser/E2E tooling is available, click the feature's primary CTAs to confirm each lands on the correct pre-filtered actionable view — a CTA that opens a generic page is a FAIL.

## Learning in the moment

When the user points out something missing or wrong, fix it, add it to the active `tasks.md`, and record one rule (portable, ≤ 250 chars, situation + check first) under `## Learned` in the right domain file (`core.md` if universal, `style.md` if a convention) as `- [ ] <rule> _(learned YYYY-MM-DD @ <lg-digest.py --project>: <cause>)_`, prefixed `[scope: <project>]` if it only holds here. Strengthen an equivalent rule instead of duplicating; if you reword it, keep its stamp and append `_(was <its old id>)_` so its history carries over.
