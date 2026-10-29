#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# control: no planted gap
