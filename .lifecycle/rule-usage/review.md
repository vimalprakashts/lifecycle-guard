# Review — rule usage tracking (v1.7.0)

VERDICT: PASS
Reviewed: 2026-10-03 · rounds: 2

## Findings addressed
- [high] commands/lg-status.md — `--audit | head -3` cut off the usage line → new `digest.py --usage` summary, used by /lg-status (tested).
- [medium] digest.py ingest_usage — whole-file hash recounted on any prose edit → key = project|feature|sorted parsed rules; rule-less reviews skipped (tested).
- [medium] digest.py USAGE_LINE — decorated ids silently dropped → lenient parser + strict output template in agent and rubric (tested).
- [medium] digest.py ingest_usage — ingest time used as review time → review.md mtime (tested).
- [nit] lg-status.md separator; CLAUDE.md documents re-review semantics.

## Known gaps (deferred)
- Stop-hook re-reads usage.jsonl + review.md files each run — a global mtime marker would skip other projects' reviews; cost stays small (~10 lines per review). Revisit if usage.jsonl grows large.
- A line like `- <id> not satisfied` would parse as satisfied — unlikely given the strict template.

## Rules applied
- 20cd2a90 caught — end-to-end run of /lg-status showed the usage line was never reached
- 87bbc6b3 satisfied — one id function shared by --rules, --audit, --usage and ingest
- 423381e6 satisfied — no format change; existing rules start at zero usage
- 3de05c35 satisfied — Stop gate behaviour untouched; gate tests green
- a9bcdcc5 satisfied — ticked tasks match the implementation
- 09ddc2c3 satisfied — --rules / --ingest-usage reachable from agent, commands and hook
- 7e416fdf satisfied — usage flows review.md → usage.jsonl → audit

## Evidence
`for t in plugins/lifecycle-guard/tests/test_*.py; do python3 $t; done` → 14 + 8 + 7 tests OK.
