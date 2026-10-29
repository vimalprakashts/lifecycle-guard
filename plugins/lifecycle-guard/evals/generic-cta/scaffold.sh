#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Dashboard tile 'Refunds waiting for review' links to the unfiltered orders list.
python3 - <<'PY'
import pathlib
p = pathlib.Path('src/admin/DashboardTiles.jsx'); s = p.read_text()
assert 'to="/admin/refunds?status=requested"' in s, "fixture drifted: planted change no longer applies"
p.write_text(s.replace('to="/admin/refunds?status=requested"', 'to="/admin/orders"', 1))
PY
