const { makeApp, seed } = require("./helpers"); // in-memory stores + fake gateway/notify/alerts

test("request ₹2000 on a paid ₹5000 order → requested, customer emailed", async () => {
  const { app, order, customer, notify } = await seed({ paid: 5000 });
  const res = await app.as(customer).post(`/orders/${order.id}/refunds`, { amount: 2000, reason: "damaged" });
  expect(res.status).toBe(201);
  expect(res.body.status).toBe("requested");
  expect(notify.sent).toContainEqual(expect.objectContaining({ template: "refund-requested" }));
});

test("approve ₹2000 → gateway called once with key refund-<id>; double approve → 409", async () => {
  const { app, admin, refund, gateway } = await seed({ paid: 5000, refund: 2000 });
  expect((await app.as(admin).post(`/refunds/${refund.id}/approve`, { amount: 2000 })).status).toBe(200);
  expect((await app.as(admin).post(`/refunds/${refund.id}/approve`, { amount: 2000 })).status).toBe(409);
  expect(gateway.calls).toEqual([expect.objectContaining({ amount: 2000, idempotencyKey: `refund-${refund.id}` })]);
});

test("₹5000 paid, ₹4000 refunded → approving ₹2000 is 422", async () => {
  const { app, admin, refund } = await seed({ paid: 5000, refunded: 4000, refund: 2000 });
  expect((await app.as(admin).post(`/refunds/${refund.id}/approve`, { amount: 2000 })).status).toBe(422);
});

test("webhook success → refunded, order total +2000; replay → no second credit or email", async () => {
  const { app, refund, order, notify, webhook } = await seed({ paid: 5000, refund: 2000, processing: true });
  await webhook({ eventId: "e1", refundRef: refund.gatewayRef, succeeded: true });
  await webhook({ eventId: "e1", refundRef: refund.gatewayRef, succeeded: true });
  expect((await order.reload()).amountRefunded).toBe(2000);
  expect(notify.sent.filter((m) => m.template === "refund-refunded")).toHaveLength(1);
});

test("gateway error on approve → failed, 502, ops alert + customer email", async () => {
  const { app, admin, refund, gateway, alerts, notify } = await seed({ paid: 5000, refund: 2000 });
  gateway.failNext("card closed");
  expect((await app.as(admin).post(`/refunds/${refund.id}/approve`, { amount: 2000 })).status).toBe(502);
  expect(alerts.sent).toContainEqual(expect.objectContaining({ type: "refund-failed" }));
  expect(notify.sent).toContainEqual(expect.objectContaining({ template: "refund-failed" }));
});

test("reject needs a reason; customer sees rejected + reason", async () => {
  const { app, admin, customer, refund, order } = await seed({ paid: 5000, refund: 2000 });
  expect((await app.as(admin).post(`/refunds/${refund.id}/reject`, {})).status).toBe(422);
  await app.as(admin).post(`/refunds/${refund.id}/reject`, { reason: "outside return window" });
  const list = await app.as(customer).get(`/orders/${order.id}/refunds`);
  expect(list.body[0]).toMatchObject({ status: "rejected", rejectReason: "outside return window" });
});

test("another customer's order → 404; request after the refund window → 422", async () => {
  const { app, order, stranger, customer, settings } = await seed({ paid: 5000, deliveredDaysAgo: 40 });
  expect((await app.as(stranger).get(`/orders/${order.id}/refunds`)).status).toBe(404);
  settings.refundWindowDays = 30;
  expect((await app.as(customer).post(`/orders/${order.id}/refunds`, { amount: 100 })).status).toBe(422);
});
