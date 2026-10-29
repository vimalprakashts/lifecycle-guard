// Business rules shared by API and UI.
module.exports = {
  MIN_ORDER_VALUE: 3000,
  // A refund can never exceed what the customer actually paid on the order.
  maxRefundable: (order) => order.amountPaid - order.amountRefunded,
};
