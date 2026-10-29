#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Refund status is visible to the admin only; the customer can't see it.
python3 - <<'PY'
import pathlib, re
p = pathlib.Path("src/customer/OrderRefunds.jsx"); s = p.read_text()
start = s.index("    <ul>"); end = s.index("    </ul>") + len("    </ul>\n")
assert start < end, "fixture drifted: refund list not found"
p.write_text(s[:start] + s[end:])   # keep the request form; drop the list of refunds + statuses
PY
python3 - <<'PY'
import pathlib
p = pathlib.Path('src/api/refunds.js'); s = p.read_text()
assert 'router.get("/orders/:id/refunds", requireCustomerOrAdmin, async (req, res) => {\n  const order = req.user.isAdmin ? await Orders.find(req.params.id) : await Orders.findOwned(req.params.id, req.user.id);' in s, "fixture drifted: planted change no longer applies"
p.write_text(s.replace('router.get("/orders/:id/refunds", requireCustomerOrAdmin, async (req, res) => {\n  const order = req.user.isAdmin ? await Orders.find(req.params.id) : await Orders.findOwned(req.params.id, req.user.id);', 'router.get("/orders/:id/refunds", requireAdmin, async (req, res) => {\n  const order = await Orders.find(req.params.id);', 1))
PY
