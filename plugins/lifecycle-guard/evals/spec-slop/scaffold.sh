#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# planted: Failure cases and acceptance criteria are generic phrases that specify nothing.
python3 - <<'PY'
import pathlib, re
p = pathlib.Path(".lifecycle/refunds/spec.md"); s = p.read_text()
def replace_section(text, heading, body):
    pattern = re.compile(r"(^## " + re.escape(heading) + r"\n)(.*?)(?=^## )", re.S | re.M)
    assert pattern.search(text), f"fixture drifted: no '## {heading}' section"
    return pattern.sub(lambda m: m.group(1) + body + "\n", text, count=1)
s = replace_section(s, "Failure and edge cases", "- Handle errors gracefully.\n- All edge cases covered.\n")
s = replace_section(s, "Acceptance criteria",
    "- Refunds work correctly for customers and admins.\n- The customer is notified as needed.\n- Security is ensured.\n")
p.write_text(s)
PY
