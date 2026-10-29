#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Order number in the refunds table is plain text, not a link to the order.
python3 - <<'PY'
import pathlib
p = pathlib.Path('src/admin/RefundsPage.jsx'); s = p.read_text()
assert '<td><Link to={`/admin/orders/${r.orderId}`}>{r.orderNumber}</Link></td>' in s, "fixture drifted: planted change no longer applies"
p.write_text(s.replace('<td><Link to={`/admin/orders/${r.orderId}`}>{r.orderNumber}</Link></td>', '<td>{r.orderNumber}</td>', 1))
PY
