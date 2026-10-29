// Admin refunds queue. ?status= filters the list (e.g. /admin/refunds?status=requested).
// Each refund row carries its own order (r.order), so caps are per order.
// The ?status= filter (used by the dashboard tile) is read from the URL and sent to GET /admin/refunds.
export function RefundsPage({ approve, reject }) {
  const [params] = useSearchParams();
  const refunds = useApi(`/admin/refunds?status=${params.get("status") ?? ""}`);
  return (
    <table>
      <tbody>
        {refunds.map((r) => {
          const max = maxRefundable(r.order);                                   // never above amount paid
          const presets = [0.25, 0.5, 1].map((f) => Math.round(f * max));
          return (
          <tr key={r.id}>
            <td><Link to={`/admin/orders/${r.orderId}`}>{r.orderNumber}</Link></td>
            <td><Link to={`/admin/customers/${r.customerId}`}>{r.customerName}</Link></td>
            <td>₹{r.amount}</td>
            <td><StatusBadge status={r.status} /></td>
            <td>
              <AmountPicker presets={presets} max={max} onPick={(amt) => approve(r.id, amt)} />
              <button onClick={() => reject(r.id, prompt("Reason shown to the customer"))}>Reject</button>
            </td>
          </tr>
          );
        })}
      </tbody>
    </table>
  );
}
