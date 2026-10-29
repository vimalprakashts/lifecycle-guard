# Spec — refunds

## Goal
Customers can request a refund on a paid order; admins approve (full or partial) or reject; the payment
gateway confirms; everyone sees the current status.

## Actors
- Customer — requests a refund on their own order, sees its status and any rejection reason.
- Admin — reviews the queue, approves an amount (≤ amount paid − already refunded) or rejects with a reason.
- System — gateway webhook moves processing → refunded | failed.

## Entity state machine
requested → processing (admin approves) → refunded | failed (gateway webhook); requested → rejected (admin).

## Per-actor capabilities + CTAs
- Customer: order page lists refunds with status; rejection reason shown.
- Admin: dashboard tile "Refunds waiting for review" → /admin/refunds?status=requested; each row links
  the order and the customer; approve via amount presets (25/50/100% of refundable); reject with reason.

## Failure and edge cases
- Approve amount above refundable → API 422 "exceeds amount paid"; presets never exceed refundable.
- Gateway call retried → idempotency key refund-<id> prevents a double refund.
- Duplicate webhook → ignored by event id.
- Gateway rejects the approve call or reports failure → status failed; ops alert "refund-failed"; customer
  email + sees "didn't go through, team alerted"; admin queue shows failed.
- Request after the refund window (Payments settings, days after delivery) → 422 with the window in the message.

## Cross-cutting
- Customer can only read/request on their own order (404 otherwise); approve/reject admin-only.
- Placement: extends the existing /admin/refunds page and the Payments settings page (refund window,
  enforced when the customer requests); no new top-level page.
- Business rules: refund ≤ amountPaid − amountRefunded (config/business-rules.js maxRefundable).

## Acceptance criteria
- Given a paid order of ₹5000, when the customer requests ₹2000, then a refund in `requested` appears
  in the admin queue and the customer gets the "refund-requested" email.
- Given a requested refund, when the admin approves ₹2000, then the gateway is called once with key
  refund-<id> and the status is `processing`.
- Given the gateway webhook succeeds, then the status is `refunded`, the order's refunded total grows by
  ₹2000, and the customer sees `refunded`.
- Given the admin rejects with "outside return window", then the customer sees `rejected` and that reason.
- Given ₹5000 paid and ₹4000 already refunded, when the admin tries ₹2000, then the API returns 422.

## Out of scope
Store credit; refunds on unpaid orders.
