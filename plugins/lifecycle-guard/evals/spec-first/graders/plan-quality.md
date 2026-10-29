---
type: llm
focus: last_message
weight: 2
---

Judge the plan for order cancellation that the agent presents in its final response, or points to there
(a spec or plan file it summarises counts). Pass only if the plan covers ALL of:
(1) the customer cancelling and seeing the result;
(2) the admin side (seeing cancelled orders and/or cancelling on a customer's behalf);
(3) for paid orders, a refund through the payment gateway, and reserved stock released or explicitly
    addressed;
(4) the race where the order ships while cancellation is in progress;
(5) concrete failure cases or acceptance criteria (states, amounts, outcomes), not generic phrases.
Judge the plan, not how much code was written. Fail if the response presents no plan, or covers only
part of the list.
