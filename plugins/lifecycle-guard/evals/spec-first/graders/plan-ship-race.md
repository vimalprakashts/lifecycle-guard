---
type: llm
focus: last_message
weight: 1
---

Judge only the plan for order cancellation that the agent presents in its final response (a summary of
its spec or plan file counts). Judge the plan, not how much code was written. Fail if the response
presents no plan (e.g. it was cut off mid-task).

Pass if the plan addresses the race where the order is marked shipped while a cancellation is in progress (e.g. an atomic status transition, or a named open risk with its consequence).
