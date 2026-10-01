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

### 1. Load context (silently)

Read `core.md` and `style.md`. List `domains/` and read every file relevant to the request (a "subscription renewal" feature needs `payments.md` and `notifications.md`, for example). If no domain file fits, create `domains/<domain>.md` from your own domain knowledge using the structure of the existing ones, mark its header `> seeded by Claude — unverified`, and continue. Also read the project's `CLAUDE.md` and skim the codebase for existing patterns.

### 2. Write the spec

Create `.lifecycle/<feature-slug>/spec.md` in the project root:

1. **Goal** — one paragraph.
2. **Actors** — every role that touches it: end customer, admin/ops, super-admin/tenant owner, finance, support, system (cron, queues), external systems (gateway webhooks, third-party APIs).
3. **Entity state machine** — every state and every transition, including who or what triggers each one and what happens on timeout. Use a mermaid `stateDiagram-v2`.
4. **Per-actor capabilities** — for each actor: screens, APIs, actions, and what they see in each state.
5. **Failure and edge cases** — walk every item in the loaded checklists' failure sections against this feature.
6. **Cross-cutting** — permissions, tenant isolation, audit log, notifications, reporting/export, observability, config, migrations, data retention.
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
```

Every spec item maps to at least one task. Show the user a short summary (actor count, states, task count, notable N/A decisions) and ask for approval once. If the user already said to just proceed, skip the wait.

On approval, change the header to `status: active`. From then on, a Stop hook will not let you finish while any `- [ ]` remains.

### 4. Implement

Work task by task. Tick a box only when the code exists and a test covers it. If an item truly can't be done now (needs credentials, a product decision, a later phase), mark it `- [~] <item> — <reason>` rather than leaving it open or pretending it's done.

### 5. Verify

Run the test suite and any linters. Re-read `spec.md` section by section against the code and list any gaps; fix them. If subagents are available, have a fresh one do this comparison instead, since a reviewer without your context is stricter. When everything is ticked or deferred, set `status: done` and give the user a short summary including any deferred items.

## Learning in the moment

When the user points out something missing or wrong (a hook will flag it too):

1. Fix it and add it to the active `tasks.md`.
2. Generalize it into a reusable rule. "You didn't add refund on admin panel" becomes "Admin can initiate full and partial refunds with reason; refund state reflected to customer." Append it under `## Learned` in the right domain file, or `core.md` if it applies to any feature, as `- [ ] <rule> _(learned YYYY-MM-DD: <cause>)_`.
3. If it's about style or conventions ("use zod not yup", "always paginate admin lists server-side"), append to `style.md` instead.
4. Check for an existing equivalent rule first. Strengthen its wording rather than duplicating it.

Mention the learning in one short line; don't make a show of it.

## Scale to the request

For a trivial tweak (rename a label, fix a typo, change a color), skip the spec. For a small change inside an existing feature, a short spec section appended to that feature's existing `spec.md` and a few tasks is enough. The full workflow is for anything with new states, actors or integrations.
