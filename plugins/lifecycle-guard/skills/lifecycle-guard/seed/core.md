# Core lifecycle checklist

Applies to every feature. Mark each item covered or N/A with a reason in the spec.

## Actors
- [ ] End user / customer flows identified
- [ ] Admin / ops flows identified (view, search, filter, act, override)
- [ ] Tenant owner / super-admin flows (multi-tenant products)
- [ ] System actors: cron jobs, queues, retries, scheduled cleanup
- [ ] External systems: inbound webhooks, outbound API calls

## State
- [ ] Core entity has an explicit state machine; every transition has a trigger
- [ ] Timeouts / expiry defined for every waiting state
- [ ] Invalid transitions rejected server-side
- [ ] State visible to every actor who needs it, in their own UI

## Data
- [ ] Schema + migration (forward and safe to rerun)
- [ ] Validation on server, not just client
- [ ] Soft delete / archival rules
- [ ] Seed / fixture data for dev and tests

## Failure and edge cases
- [ ] Network failure / third-party down mid-operation
- [ ] Duplicate submission and double-click (idempotency keys)
- [ ] Concurrent edits (locking or versioning)
- [ ] Partial failure across steps (compensation or retry)
- [ ] User abandons mid-flow; flow resumable
- [ ] Empty, loading and error states in every UI

## Security
- [ ] Permission checks per action, per role (RBAC)
- [ ] Tenant isolation on every query
- [ ] Input sanitization; no IDOR on IDs in URLs
- [ ] Secrets in config, never in code; PII masked in logs

## Communication
- [ ] Notifications for each state change that a human cares about (channel decided)
- [ ] Notification failures don't fail the main transaction

## Visibility
- [ ] Audit log: who did what, when, old → new value
- [ ] Admin list view with filters, search, pagination, export
- [ ] Metrics / dashboard numbers updated
- [ ] Structured logs + alert on failure spikes

## Actionability
"Call to action" is not a dashboard-only concept — it applies to EVERY page.
- [ ] Every metric, alert, list row and notification has a clear call-to-action
- [ ] Each CTA deep-links to the EXACT pre-filtered, actionable view (not a generic page); target page honours the filter param
- [ ] The action completes the task in place (verify/approve/pay/edit), not just a redirect that leaves the user to hunt
- [ ] **Entity cross-links everywhere**: any reference to another entity shown on ANY page — order #, customer, product, invoice, affiliate, SKU, vendor, user — rendered in a table cell, list row, detail panel or modal is a link to that entity's own page. A plain-text entity reference is a lifecycle dead-end. Enumerate every entity reference each screen renders and confirm each is navigable.
- [ ] Charts/graphs are interactive (hover value + tooltip), not static images

## Reuse & placement (orient before building)
- [ ] Before adding ANY new surface (nav/menu item, route/path, settings tab, page, modal, endpoint, service), inventory what already exists (grep the router, nav/tab lists, endpoints/services) and EXTEND the natural existing home
- [ ] A new top-level surface where an existing page/section/endpoint is the obvious home is a red flag — justify it or place it in the existing home
- [ ] Spec records the chosen placement + what existing code was reused

## Business rules & dependencies
- [ ] Every new value / default / preset / limit / threshold is reconciled with the EXISTING business rules it touches (min/max order value, order/qty limits, pricing & discount tiers, tax, stock thresholds, delivery eligibility, coupons) — never picked in isolation
- [ ] Each key value is justified: why this value, why here, what it depends on, what depends on it, is it grouped correctly
- [ ] No value contradicts an existing rule (e.g. a budget/price option below the store's minimum order value)

## Delivery
- [ ] Unit tests per state transition; integration test for the main flow
- [ ] Independent reviewer pass (fresh context) before "done"
- [ ] Feature flag or safe rollout path
- [ ] API docs / README updated
- [ ] Config and env vars documented

## Learned
- [ ] ORIENT BEFORE BUILDING: read the existing routes/nav/settings-tabs/endpoints for the area FIRST and extend the natural home; adding a parallel nav item / route / tab / page / endpoint when one exists is a red flag the reviewer must also catch (a diff-only read misses it — look at the surrounding structure) _(learned 2026-10-02: a feature added its own settings tab + route instead of joining the existing AI settings page)_
- [ ] RECONCILE VALUES WITH BUSINESS RULES: every new value/default/preset/limit/threshold must respect existing constraints (min/max order, limits, tax, pricing tiers, stock thresholds); justify each (why this value, why here, dependencies) — a value picked in isolation that contradicts a rule is a bug _(learned 2026-10-02: budget presets started at ₹500 while the store minimum order is ₹3000)_
