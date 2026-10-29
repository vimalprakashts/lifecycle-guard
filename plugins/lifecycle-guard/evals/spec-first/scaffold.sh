#!/usr/bin/env bash
# Copy the shared fixture into the run's workspace, then plant exactly one gap (if any).
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/../_fixtures/shop/." .
# a shop with refunds already built; the task is a new feature. Drop the refunds planning files so the
# only spec that can exist at the end is the one the agent writes.
rm -r .lifecycle
