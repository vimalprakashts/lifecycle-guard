#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Refund amount presets ignore the 'refund ≤ amount paid − already refunded' rule.
python3 - <<'PY'
import pathlib
p = pathlib.Path("src/admin/RefundsPage.jsx"); s = p.read_text()
old_max = "const max = maxRefundable(r.order);                                   // never above amount paid"
old_presets = "const presets = [0.25, 0.5, 1].map((f) => Math.round(f * max));"
assert old_max in s and old_presets in s, "fixture drifted: planted change no longer applies"
s = s.replace(old_max, "const max = 10000;").replace(old_presets, "const presets = [1000, 5000, 10000];")
p.write_text(s)
PY
