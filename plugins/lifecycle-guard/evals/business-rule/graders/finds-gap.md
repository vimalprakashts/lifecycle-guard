---
type: llm
weight: 1
---

The review identifies that the admin refund amount presets/max are fixed amounts (1000/5000/
10000) that ignore the business rule refund ≤ amount paid − already refunded (maxRefundable), so the UI
offers refunds larger than what was paid (the API would then reject them with 422). Passing requires
naming this conflict with the refund cap specifically.
