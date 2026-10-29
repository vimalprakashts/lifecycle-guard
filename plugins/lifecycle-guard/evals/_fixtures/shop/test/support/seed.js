// Builds an in-memory shop for one test: a customer, an admin, a stranger, an order with the given
// payment/refund state, and fakes for the gateway, email, ops alerts and settings.
const { makeApp } = require("./make-app");
module.exports = async function seed({ paid = 0, refunded = 0, refund, processing = false, deliveredDaysAgo = 1 } = {}) {
  const ctx = makeApp();
  const order = await ctx.orders.create({ amountPaid: paid, amountRefunded: refunded, deliveredAt: ctx.clock.daysAgo(deliveredDaysAgo) });
  const r = refund ? await ctx.refunds.create({ orderId: order.id, amount: refund, status: processing ? "processing" : "requested", gatewayRef: processing ? "gw-1" : undefined }) : undefined;
  return { ...ctx, order, refund: r, webhook: (body) => ctx.app.post("/webhooks/gateway/refunds", body, { signed: true }) };
};
