# Payments (collection, refunds, settlement)

## Customer
- [ ] Initiate payment with amount computed server-side (never trust client amount)
- [ ] Pending / processing screen that survives refresh
- [ ] Success and failure pages with clear next step; retry on failure
- [ ] Receipt (on screen + email/SMS/WhatsApp), downloadable invoice
- [ ] Payment history with status
- [ ] Refund status visible

## Admin / finance
- [ ] Payment list: filter by status, date, method, customer; search by order/txn id; export
- [ ] Payment detail: full timeline of state changes and gateway events
- [ ] Full and partial refund with reason; permission-gated
- [ ] Record offline / manual payment (cash, cheque, bank transfer) with proof
- [ ] Daily collection summary / dashboard totals

## System
- [ ] Gateway webhook endpoint with signature verification
- [ ] Idempotent webhook processing (duplicate and out-of-order events)
- [ ] Webhook may arrive before or after browser redirect — both paths converge to same state
- [ ] Status poll / reconcile job for payments stuck in pending
- [ ] Expire unpaid orders after timeout
- [ ] Settlement reconciliation against gateway report; mismatch report

## Edge cases
- [ ] User closes browser mid-payment
- [ ] Double click / double charge prevention
- [ ] Amount tampering on client
- [ ] Partial refunds summing above original amount rejected
- [ ] Currency, rounding, paise vs rupees consistency
- [ ] Gateway downtime: clear message, no orphaned orders

## Compliance
- [ ] No card data stored; tokenization only
- [ ] GST invoice fields where applicable
- [ ] Audit trail for every money movement

## Learned
