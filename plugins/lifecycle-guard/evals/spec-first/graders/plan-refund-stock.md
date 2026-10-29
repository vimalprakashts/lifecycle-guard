---
type: llm
focus: last_message
weight: 1
---

Judge only the plan for order cancellation that the agent presents in its final response (a summary of
its spec or plan file counts). Judge the plan, not how much code was written. Fail if the response
presents no plan (e.g. it was cut off mid-task).

Pass if the plan covers both money and stock for a paid order: a refund through the payment gateway (including what happens if the gateway fails), AND reserved stock or inventory either released or explicitly addressed (deferring it with a stated reason counts).
