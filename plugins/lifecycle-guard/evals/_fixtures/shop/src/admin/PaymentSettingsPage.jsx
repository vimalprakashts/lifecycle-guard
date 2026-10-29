// Payments settings: gateway keys and the refund window (days) enforced by POST /orders/:id/refunds.
export function PaymentSettingsPage({ settings, save }) {
  return (
    <form onSubmit={save}>
      <GatewayKeys value={settings.gateway} />
      <NumberField label="Refund window (days)" name="refundWindowDays" value={settings.refundWindowDays} />
    </form>
  );
}
