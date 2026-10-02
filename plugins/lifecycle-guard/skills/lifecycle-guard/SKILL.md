---
name: lifecycle-guard
description: Full-lifecycle definition-of-done for building any feature end to end — customer side, admin side, system/background jobs, webhooks, failure paths, notifications, reporting, security, tests. Use this whenever the user asks to build, implement, add, integrate or extend a feature, module, flow, screen, API, integration or workflow (payments, auth, onboarding, orders, uploads, notifications, dashboards, CRUD modules, etc.), even if they phrase it casually or only mention one side of it. Also use when the user complains that something is half done, missing pieces, or not handled.
---

# Lifecycle Guard

You tend to build the happy path for one actor and stop. This skill makes you design the whole lifecycle first, build against a checklist, and get blocked by a Stop hook until the checklist is done. The checklists are not static: they grow from the user's own corrections and prompts.

All learned knowledge lives in `~/.claude/lifecycle-guard/`:

- `core.md` — universal lifecycle checklist, applies to every feature
- `style.md` — the user's stack, conventions and preferences, learned from their prompts
- `domains/<domain>.md` — domain checklists (payments, auth, …), each with a `## Learned` section of rules that came from real misses

Treat `## Learned` items as mandatory: each one exists because it was missed before.

## Workflow

### 1. Load context + ORIENT (silently) — critical, do this FIRST

Read `core.md` and `style.md`. List `domains/` and read every file relevant to the request (a "subscription renewal" feature needs `payments.md` and `notifications.md`, for example). If no domain file fits, create `domains/<domain>.md` from your own domain knowledge using the structure of the existing ones, mark its header `> seeded by Claude — unverified`, and continue. Also read the project's `CLAUDE.md`.

**Then ORIENT against what already exists — before writing the spec, never mind code.** You will add new things (a setting, a page, an endpoint); your job is to put them in the RIGHT existing home, not to build a parallel one. So inventory the current structure for the area you're touching:

- **Routes / navigation / menus** — grep the router and any nav/tab/menu list. Know every existing page and section name.
- **The natural home for your feature** — is there already a page, tab, settings section, modal, list, or report where this belongs? (e.g. a new AI toggle belongs on the existing AI settings page, not a brand-new tab.) Read that surface's code.
- **Existing endpoints / services / DTOs / settings slices** — grep for ones that already do part of this, so you extend rather than duplicate.
- **Existing BUSINESS RULES & constraints the feature touches** — min/max order value, order/qty limits, pricing & discount tiers, tax, stock thresholds, delivery eligibility, coupon rules, currency/rounding. Any value you will introduce (a default, preset, limit, threshold, budget band) MUST be consistent with these — never pick a number in isolation. (E.g. a "budget" selector must not offer amounts below the store's minimum order value.)
- When placement isn't obvious, **build a quick sitemap**: list the routes/tabs and one line on what each already holds, and pick the fit from that.

**Adding a NEW top-level surface (nav item, route/path, settings tab, page, endpoint) when an existing one is the natural home is a red flag** — prefer extending the existing surface. This decision is made HERE, from reading, not after the fact. Record the chosen placement + what you reused in the spec (§6/§7), so the reviewer can check it.

### 2. Write the spec

Create `.lifecycle/<feature-slug>/spec.md` in the project root:

1. **Goal** — one paragraph.
2. **Actors** — every role that touches it: end customer, admin/ops, super-admin/tenant owner, finance, support, system (cron, queues), external systems (gateway webhooks, third-party APIs).
3. **Entity state machine** — every state and every transition, including who or what triggers each one and what happens on timeout. Use a mermaid `stateDiagram-v2`.
4. **Per-actor capabilities + CTAs** — for each actor: screens, APIs, actions, and what they see in each state. For every metric, alert, list and notification, name the **call-to-action and its exact destination** — a deep-link to the pre-filtered, actionable view (not a generic page), and the action that closes the task in place. If a target page lacks the needed filter param, adding it is part of this feature. Any chart/graph is interactive (hover value + tooltip), not a static image. **"Call to action" is not dashboard-only — it applies to every page.** For each screen (list, table, detail, modal — not just dashboards), enumerate every reference it renders to another entity (order #, customer, product, invoice, affiliate, SKU, vendor, user) and make each a link to that entity's own page. A plain-text entity reference is a lifecycle dead-end.
5. **Failure and edge cases** — walk every item in the loaded checklists' failure sections against this feature.
6. **Cross-cutting** — permissions, tenant isolation, audit log, notifications, reporting/export, observability, config, migrations, data retention.
   **Placement & reuse** (from the §1 orientation): name the existing page/route/tab/section/endpoint this feature EXTENDS, and the existing services/DTOs it reuses. If you are adding any NEW top-level surface (nav item, route, settings tab, page, endpoint), justify why no existing home fit — this is the anti-duplication record the reviewer checks.
   **Business rules & dependencies**: for each KEY value, default, preset, limit or threshold the feature introduces, write one line — *why this value, what existing business rule it must respect, what it depends on, what depends on it, is it grouped correctly*. Reconcile every one against the constraints found in §1 (min/max order, limits, tax, pricing tiers, stock thresholds, delivery eligibility). A value that contradicts an existing rule is a bug, not a detail. This is the "think through the whole lifecycle, not just the happy path" record the reviewer checks.
7. **Checklist coverage** — every item from `core.md` and the loaded domain files, each marked `✓ covered in §N`, or `N/A — <reason>`. Nothing silently skipped.
8. **Acceptance criteria** — Given/When/Then, at least one per state transition and per actor.
9. **Out of scope** — explicit.

Apply `style.md` throughout (stack, naming, folder layout, UI conventions).

### 3. Write tasks and get approval

Create `.lifecycle/<feature-slug>/tasks.md`:

```markdown
status: draft
feature: <name>

## Backend
- [ ] ...
## Customer UI
- [ ] ...
## Admin UI
- [ ] ...
## System / jobs / webhooks
- [ ] ...
## Notifications
- [ ] ...
## Tests
- [ ] ...
## Ops (migrations, config, logging, alerts, docs)
- [ ] ...
## Review
- [ ] Independent reviewer pass (lifecycle-reviewer, fresh context) — findings fixed or deferred
```

Every spec item maps to at least one task. The **Review** section is mandatory —
always include the reviewer-pass task; the Stop hook enforces that the §5 review
actually happened before "done". Show the user a short summary (actor count, states, task count, notable N/A decisions) and ask for approval once. If the user already said to just proceed, skip the wait.

On approval, change the header to `status: active`. From then on, a Stop hook will not let you finish while any `- [ ]` remains.

### 4. Implement

Work task by task. Tick a box only when the code exists and a test covers it. If an item truly can't be done now (needs credentials, a product decision, a later phase), mark it `- [~] <item> — <reason>` rather than leaving it open or pretending it's done.

### 5. Verify — enforced independent review loop

Self-review is not enough; you miss the same things twice. A **separate reviewer in
a fresh context MUST run** before anything is called done — this is mandatory, not
"if available", and it is why §3 always adds a `Reviewer agent pass` task that the
Stop hook won't let you leave open.

1. Run the test suite and any linters first; fix failures.
2. **Dispatch the critic.** Prefer the `lifecycle-reviewer` agent; if your harness
   has no plugin agents, spawn a fresh general-purpose subagent using
   `references/review.md`. Give it the `spec.md`/`tasks.md` paths and the changed
   files — NOT the whole repo. It reviews read-only and returns `VERDICT` + ranked
   findings covering actor coverage, **CTA/deep-link coverage**, action closure,
   **interactivity**, failure/edge cases, security/tenancy, CRUD parity, and the
   `## Learned` rules.
3. **Fix** every critical/high finding (and cheap mediums). Each fix that reflects a
   reusable lesson also follows "Learning in the moment".
4. **Re-dispatch once** to confirm. Stop at `VERDICT: PASS` or after this 2nd round —
   never loop endlessly. Remaining findings after round 2 are reported to the user as
   known gaps, not silently dropped.
5. **Token discipline**: at most 2 review rounds; scope each dispatch to the diff +
   spec; pass paths/excerpts, not file dumps; the critic runs on a mid-tier model.
6. **Write the committed review artifact** `.lifecycle/<feature>/review.md` with the
   verdict, findings addressed, and any deferred gaps (format in `/lifecycle-guard:review`).
   The Stop hook requires this file to show `VERDICT: PASS` (or `review: deferred — <reason>`)
   before a feature may be `status: done` — so the review cannot be silently skipped.
7. **Definition of done** (paste the evidence, don't just claim it): run the build, the
   test suite and the linter and paste their literal output. A failing suite fixes the
   CODE, never the test. Only when build+tests+lint are green, the review is PASS (or
   deferred), and every box is ticked or `- [~]`, set `status: done` and give the user a
   short summary including deferred items and known gaps.

If browser/E2E tooling is available, the critic (or you) should also click the
feature's primary CTAs to confirm each lands on the correct, pre-filtered actionable
view — a CTA that opens a generic page is a FAIL.

## Learning in the moment

When the user points out something missing or wrong (a hook will flag it too):

1. Fix it and add it to the active `tasks.md`.
2. Generalize it into a reusable rule. "You didn't add refund on admin panel" becomes "Admin can initiate full and partial refunds with reason; refund state reflected to customer." Append it under `## Learned` in the right domain file, or `core.md` if it applies to any feature, as `- [ ] <rule> _(learned YYYY-MM-DD: <cause>)_`.
3. If it's about style or conventions ("use zod not yup", "always paginate admin lists server-side"), append to `style.md` instead.
4. Check for an existing equivalent rule first. Strengthen its wording rather than duplicating it.

Mention the learning in one short line; don't make a show of it.

## Scale to the request

For a trivial tweak (rename a label, fix a typo, change a color), skip the spec. For a small change inside an existing feature, a short spec section appended to that feature's existing `spec.md` and a few tasks is enough. The full workflow is for anything with new states, actors or integrations.
