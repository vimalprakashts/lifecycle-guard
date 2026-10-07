# Notifications (email, SMS, WhatsApp, push, in-app)

## Customer / recipient
- [ ] Every state change a human cares about has a notification, with the channel chosen deliberately
- [ ] Per-channel content: subject/body, deep link back into the app, brand/sender identity
- [ ] Preferences: opt in/out per category and channel; honoured on every send
- [ ] Unsubscribe link (email) / STOP keyword (SMS/WhatsApp) respected
- [ ] In-app notification centre: unread count, mark read, clear call-to-action

## Admin / ops
- [ ] Template management per event + channel (edit without a deploy); preview with sample data
- [ ] Notification / message log: who, when, channel, template, status (sent/delivered/failed), payload
- [ ] Resend / test-send a notification; see failures and why
- [ ] Per-tenant sender config (from-address, numbers, provider keys)

## System
- [ ] Sending is async (queue/job) — a failed notification NEVER fails the main transaction
- [ ] Retry with backoff on transient provider errors; dead-letter after N attempts
- [ ] Idempotency: one logical event → one message, even on retries/duplicate triggers
- [ ] Delivery/read webhooks from providers ingested and reflected in the log
- [ ] Rate limiting / batching to stay within provider limits; quiet hours if relevant
- [ ] Scheduled / reminder sends (cron) are gated so they can't double-fire

## Edge cases
- [ ] Missing/invalid recipient (no email/phone) — skip that recipient, log it with the reason, keep sending to the rest; never fail the whole batch
- [ ] Provider down → queued, not lost; surfaces in the log
- [ ] Template variable missing → safe fallback, never ships "{{name}}" to a customer
- [ ] Duplicate event (e.g. webhook + redirect both fire) → deduped
- [ ] Wrong locale / timezone in dates and times
- [ ] Opted-out user still gets transactional (vs marketing) — the distinction is enforced

## Compliance / deliverability
- [ ] Transactional vs marketing separated; consent recorded for marketing
- [ ] SPF/DKIM (email) and approved templates/sender IDs (SMS/WhatsApp) where required
- [ ] No secrets or full PII in notification bodies or logs
- [ ] Audit trail for every send

## Learned
