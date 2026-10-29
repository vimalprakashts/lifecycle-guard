---
type: llm
focus: last_message
weight: 1
---

Judge only the plan for order cancellation that the agent presents in its final response (a summary of
its spec or plan file counts). Judge the plan, not how much code was written. Fail if the response
presents no plan (e.g. it was cut off mid-task).

Pass if the plan covers the customer cancelling an order and seeing the outcome (status, refund, or a clear refusal once shipped).
