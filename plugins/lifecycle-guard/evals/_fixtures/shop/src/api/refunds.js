const { maxRefundable } = require("../config/business-rules");

// Customer asks for a refund on their own order.
router.post("/orders/:id/refunds", requireCustomer, async (req, res) => {
  const order = await Orders.findOwned(req.params.id, req.user.id);          // 404 if not the customer's order
  if (!order) return res.status(404).end();
  const { refundWindowDays } = await Settings.payments();
  if (daysSince(order.deliveredAt ?? order.paidAt) > refundWindowDays) return res.status(422).json({ error: `refunds close ${refundWindowDays} days after delivery` });
  const amount = Number(req.body.amount);
  if (!(amount > 0) || amount > maxRefundable(order)) return res.status(422).json({ error: "amount must be between 1 and the amount paid" });
  if (await Refunds.openFor(order.id)) return res.status(409).json({ error: "a refund is already in progress for this order" });
  const refund = await Refunds.create({ orderId: order.id, amount, reason: req.body.reason, status: "requested" });
  await notify.email(order.customerEmail, "refund-requested", { orderNumber: order.number, amount: refund.amount });
  res.status(201).json(refund);
});

// Customer sees refunds on their own order; admin sees any order's refunds.
router.get("/orders/:id/refunds", requireCustomerOrAdmin, async (req, res) => {
  const order = req.user.isAdmin ? await Orders.find(req.params.id) : await Orders.findOwned(req.params.id, req.user.id);
  if (!order) return res.status(404).end();
  res.json(await Refunds.forOrder(order.id));
});

// Admin refunds queue: rows carry their order + customer so the UI can link them and cap per order.
router.get("/admin/refunds", requireAdmin, async (req, res) => {
  const status = ["requested", "processing", "refunded", "rejected", "failed"].includes(req.query.status) ? req.query.status : undefined;
  res.json(await Refunds.list({ status, include: ["order", "customer"] }));   // [{ id, status, amount, orderId, orderNumber, order, customerId, customerName }]
});

// Admin approves: amount is capped at what was actually paid and not yet refunded.
router.post("/refunds/:id/approve", requireAdmin, async (req, res) => {
  const refund = await Refunds.find(req.params.id);
  if (!refund) return res.status(404).end();
  if (refund.status !== "requested") return res.status(409).json({ error: `refund is ${refund.status}` });
  const order = await Orders.find(refund.orderId);
  const amount = Number(req.body.amount);
  if (!(amount > 0) || amount > maxRefundable(order)) return res.status(422).json({ error: "exceeds amount paid" });
  // claim the refund first so a double click can't call the gateway twice; the key makes retries safe too
  if (!(await Refunds.transition(refund.id, "requested", "processing", { amount }))) return res.status(409).end();
  try {
    const { refundRef } = await gateway.refund(order.paymentId, amount, { idempotencyKey: `refund-${refund.id}` });
    await Refunds.update(refund.id, { gatewayRef: refundRef });
  } catch (err) {
    await Refunds.update(refund.id, { status: "failed", failureReason: err.message });
    await alerts.ops("refund-failed", { refundId: refund.id, orderNumber: order.number, reason: err.message });
    await notify.email(order.customerEmail, "refund-failed", { orderNumber: order.number, amount });
    return res.status(502).json({ error: "gateway refused the refund; marked failed" });
  }
  res.json({ ok: true });
});

// Admin rejects with a reason the customer can read.
router.post("/refunds/:id/reject", requireAdmin, async (req, res) => {
  if (!req.body.reason) return res.status(422).json({ error: "a reason is required" });
  const refund = await Refunds.transition(req.params.id, "requested", "rejected", { rejectReason: req.body.reason });
  if (!refund) return res.status(409).end();
  const order = await Orders.find(refund.orderId);
  await notify.email(order.customerEmail, "refund-rejected", { orderNumber: order.number, reason: req.body.reason });
  res.json({ ok: true });
});

// Gateway webhook: processing → refunded | failed. Idempotent on the gateway event id.
router.post("/webhooks/gateway/refunds", verifyGatewaySignature, async (req, res) => {
  if (!(await Events.recordOnce(req.body.eventId))) return res.status(200).end();   // atomic insert; replays are no-ops
  const refund = await Refunds.byGatewayRef(req.body.refundRef);
  if (!refund) return res.status(404).end();
  const status = req.body.succeeded ? "refunded" : "failed";
  if (!(await Refunds.transition(refund.id, "processing", status))) return res.status(200).end();
  await Orders.addRefunded(refund.orderId, req.body.succeeded ? refund.amount : 0);
  const order = await Orders.find(refund.orderId);
  await notify.email(order.customerEmail, `refund-${status}`, { orderNumber: order.number, amount: refund.amount });
  if (status === "failed") await alerts.ops("refund-failed", { refundId: refund.id, orderNumber: order.number, reason: req.body.failureReason });
  res.status(200).end();
});
