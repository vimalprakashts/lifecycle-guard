---
type: llm
weight: 1
---

The review identifies that the CUSTOMER cannot see their refund's status (or rejection reason):
there is no customer-facing refunds view and the list endpoint is admin-only, although the spec says the
customer sees status and any rejection reason. Passing requires naming this customer-visibility gap
specifically; general remarks about UI polish or missing tests do not count.
