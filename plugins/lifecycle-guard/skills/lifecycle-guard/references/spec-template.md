# Spec + tasks template (read when writing a full spec)

## `.lifecycle/<feature-slug>/spec.md`

1. **Goal** — one paragraph.
2. **Actors** — every role that touches it: end customer, admin/ops, super-admin/tenant owner, finance, support, system (cron, queues), external systems (gateway webhooks, third-party APIs).
3. **Entity state machine** — every state and every transition, including who or what triggers each one and what happens on timeout. Use a mermaid `stateDiagram-v2`.
4. **Per-actor capabilities + CTAs** — for each actor: screens, APIs, actions, and what they see in each state. For every metric, alert, list and notification, name the **call-to-action and its exact destination** — a deep-link to the pre-filtered, actionable view (not a generic page), and the action that closes the task in place. If a target page lacks the needed filter param, adding it is part of this feature. Any chart/graph is interactive (hover value + tooltip), not a static image. **"Call to action" is not dashboard-only — it applies to every page.** For each screen (list, table, detail, modal — not just dashboards), enumerate every reference it renders to another entity (order #, customer, product, invoice, affiliate, SKU, vendor, user) and make each a link to that entity's own page. A plain-text entity reference is a lifecycle dead-end.
5. **Failure and edge cases** — walk every item in the loaded checklists' failure sections against this feature.
6. **Cross-cutting** — permissions, tenant isolation, audit log, notifications, reporting/export, observability, config, migrations, data retention.
   **Placement & reuse** (from the orientation): name the existing page/route/tab/section/endpoint this feature EXTENDS, and the existing services/DTOs it reuses. If you are adding any NEW top-level surface (nav item, route, settings tab, page, endpoint), justify why no existing home fit — this is the anti-duplication record the reviewer checks.
   **Business rules & dependencies**: for each KEY value, default, preset, limit or threshold the feature introduces, write one line — *why this value, what existing business rule it must respect, what it depends on, what depends on it, is it grouped correctly*. Reconcile every one against the constraints found while orienting (min/max order, limits, tax, pricing tiers, stock thresholds, delivery eligibility). A value that contradicts an existing rule is a bug, not a detail.
7. **Checklist coverage** — every item from the loaded checklists (`--context` output), each marked `✓ covered in §N`, or `N/A — <reason>`. Nothing silently skipped. Learned rules are cited by `[id]`.
8. **Acceptance criteria** — Given/When/Then, at least one per state transition and per actor.
9. **Out of scope** — explicit.

**Portability test** (before showing the spec): a requirement line that could be pasted unchanged into
any other feature's spec specifies nothing — "handle errors gracefully", "notify the user", "ensure
security", "all edge cases covered". It reads as covered and is easy to tick while the work is half
done. Rewrite each one to name the concrete actor, state, trigger, channel, error or limit ("gateway
timeout → order stays `pending_payment`; retry job after 5 min; customer sees 'payment pending'").
Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --lint-spec .lifecycle/<slug>/spec.md
.lifecycle/<slug>/tasks.md` to catch the common phrasings; the reviewer checks the rest.

## `.lifecycle/<feature-slug>/tasks.md`

```markdown
status: draft
feature: <name>
domains: <the --domains you loaded, e.g. payments,notifications>

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

Every spec item maps to at least one task. The **Review** section is mandatory — the Stop hook
enforces that the review actually happened before "done". The `domains:` line tells the reviewer
which checklists to load.
