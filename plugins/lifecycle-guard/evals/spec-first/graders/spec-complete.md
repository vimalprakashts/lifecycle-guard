---
type: llm
focus:
  source: file
  path: .lifecycle/order-cancellation/spec.md
weight: 2
---

Judge the spec file the agent wrote for order cancellation. Pass only if it covers ALL of:
(1) the customer cancelling and seeing the result;
(2) the admin side (seeing cancelled orders and/or cancelling on a customer's behalf);
(3) the system side for paid orders: a refund through the payment gateway, and reserved stock either
    released or explicitly addressed (e.g. deferred with a reason, since this repo has no inventory module);
(4) the race where the order ships while cancellation is in progress;
(5) acceptance criteria or failure cases that name concrete states, amounts or outcomes rather than
    generic phrases like "handle errors gracefully".
If no spec file exists, fail.
