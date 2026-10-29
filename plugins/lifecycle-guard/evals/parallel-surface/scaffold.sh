#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: A new top-level 'Refund settings' tab duplicates the existing Payments settings page.
python3 - <<'PY'
import pathlib
p = pathlib.Path('src/admin/routes.js'); s = p.read_text()
assert '  { path: "/admin/settings/payments", page: "PaymentSettingsPage", nav: "Settings" }, // gateway keys, refund window\n' in s, "fixture drifted: planted change no longer applies"
p.write_text(s.replace('  { path: "/admin/settings/payments", page: "PaymentSettingsPage", nav: "Settings" }, // gateway keys, refund window\n', '  { path: "/admin/settings/payments", page: "PaymentSettingsPage", nav: "Settings" }, // gateway keys, refund window\n  { path: "/admin/refund-settings", page: "RefundSettingsPage", nav: "Refund settings" },\n', 1))
PY
cat > src/admin/RefundSettingsPage.jsx <<'JSX'
// Refund settings.
export function RefundSettingsPage({ settings, save }) {
  return (
    <form onSubmit={save}>
      <NumberField label="Refund window (days)" name="refundWindowDays" value={settings.refundWindowDays} />
    </form>
  );
}
JSX
