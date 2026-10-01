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
- [ ] Every metric, alert, list row and notification has a clear call-to-action
- [ ] Each CTA deep-links to the EXACT pre-filtered, actionable view (not a generic page); target page honours the filter param
- [ ] The action completes the task in place (verify/approve/pay/edit), not just a redirect that leaves the user to hunt
- [ ] Charts/graphs are interactive (hover value + tooltip), not static images

## Delivery
- [ ] Unit tests per state transition; integration test for the main flow
- [ ] Independent reviewer pass (fresh context) before "done"
- [ ] Feature flag or safe rollout path
- [ ] API docs / README updated
- [ ] Config and env vars documented

## Learned
