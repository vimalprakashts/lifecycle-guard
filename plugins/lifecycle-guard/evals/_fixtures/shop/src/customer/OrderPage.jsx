// The customer's own order page (/orders/:id): order summary, then refunds (request form + statuses).
export function OrderPage({ orderId }) {
  const order = useApi(`/orders/${orderId}`);                 // 404 for another customer's order
  const refunds = useApi(`/orders/${orderId}/refunds`);
  const requestRefund = (id, body) => api.post(`/orders/${id}/refunds`, body);
  return (
    <>
      <OrderSummary order={order} />
      <OrderRefunds order={order} refunds={refunds} requestRefund={requestRefund} />
    </>
  );
}
