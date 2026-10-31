#!/usr/bin/env bash
# Build release notes for tag $1 (e.g. v1.6.2): its CHANGELOG.md section (else the bump commit's body), then every commit
# subject since the previous tag, then the upgrade block. Used by .github/workflows/release.yml.
set -euo pipefail
tag="$1"
plugin_json="plugins/lifecycle-guard/.claude-plugin/plugin.json"
prev=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || true)
# the commit that introduced this exact version string (not just any later edit to plugin.json)
bump=$(git log -1 --format=%H -S"\"${tag#v}\"" -- "$plugin_json")
bump=${bump:-$(git log -1 --format=%H -- "$plugin_json")}
range=${prev:+$prev..}HEAD

# the CHANGELOG section for this version is the release body (it covers every commit since the last
# release); the bump commit's body is the fallback for a version with no section
body=$(awk -v v="${tag#v}" '$0 ~ "^## "v" " {on=1; next} on && /^## / {exit} on' CHANGELOG.md | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')
if [ -z "$body" ]; then
  body=$(git log -1 --format=%b "$bump" | { grep -viE '^(co-authored-by|signed-off-by):' || true; } | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')
fi
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
