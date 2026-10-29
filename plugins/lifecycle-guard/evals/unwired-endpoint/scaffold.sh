#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Reject endpoint exists but the admin UI has no reject action.
python3 - <<'PY'
import pathlib
p = pathlib.Path('src/admin/RefundsPage.jsx'); s = p.read_text()
assert '              <button onClick={() => reject(r.id, prompt("Reason shown to the customer"))}>Reject</button>\n' in s, "fixture drifted: planted change no longer applies"
p.write_text(s.replace('              <button onClick={() => reject(r.id, prompt("Reason shown to the customer"))}>Reject</button>\n', '', 1))
PY
