---
type: llm
focus: last_message
weight: 1
---

Judge only the plan for order cancellation that the agent presents in its final response (a summary of
its spec or plan file counts). Judge the plan, not how much code was written. Fail if the response
presents no plan (e.g. it was cut off mid-task).

Pass if the plan covers the admin side: admins can see cancelled orders and/or cancel on a customer's behalf. Saying no admin change is needed, without giving admins any way to see cancellations, does not count.
