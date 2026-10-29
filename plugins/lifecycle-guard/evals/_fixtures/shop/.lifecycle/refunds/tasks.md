status: done
feature: refunds

## Backend
- [x] request / list / approve / reject endpoints with ownership + admin checks
- [x] gateway webhook, idempotent on event id; refund cap via maxRefundable
## Admin UI
- [x] refunds queue with order + customer links, presets, reject with reason
- [x] dashboard tile deep-links to /admin/refunds?status=requested
## Customer UI
- [x] refunds on the customer's order page with status and rejection reason
## Notifications
- [x] requested / rejected / refunded / failed emails
## Tests
- [x] endpoint and webhook tests
