// Shown on the customer's own order page: a request form, then every refund with its status and, if
// rejected, the reason.
export function OrderRefunds({ order, refunds, requestRefund }) {
  const [error, setError] = useState(null);
  return (
    <>
    <RefundRequestForm
      max={maxRefundable(order)}
      onSubmit={({ amount, reason }) => requestRefund(order.id, { amount, reason }).catch((e) => setError(e.message))}
    />
    {error && <p role="alert">{error}</p>}
    <ul>
      {refunds.map((r) => (
        <li key={r.id}>
          ₹{r.amount} — <StatusBadge status={r.status} />
          {r.status === "rejected" && <p>Reason: {r.rejectReason}</p>}
          {r.status === "failed" && <p>The refund didn't go through; our team has been alerted and will retry.</p>}
        </li>
      ))}
    </ul>
    </>
  );
}
