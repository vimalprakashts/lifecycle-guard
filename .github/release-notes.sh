#!/usr/bin/env bash
# Build release notes for tag $1 (e.g. v1.6.2): the version-bump commit's body, then every commit
# subject since the previous tag, then the upgrade block. Used by .github/workflows/release.yml.
set -euo pipefail
tag="$1"
plugin_json="plugins/lifecycle-guard/.claude-plugin/plugin.json"
prev=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || true)
bump=$(git log -1 --format=%H -- "$plugin_json")
range=${prev:+$prev..}HEAD

body=$(git log -1 --format=%b "$bump" | sed '/^Co-Authored-By:/d' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')
if [ -n "$body" ]; then
  printf '%s\n\n' "$body"
fi
printf '### Commits%s\n' "${prev:+ since $prev}"
git log --format='- %s (%h)' --no-merges "$range"
cat <<'UPGRADE'

### Upgrade
```
/plugin update lifecycle-guard@vimal-tools
/reload-plugins
```
UPGRADE
