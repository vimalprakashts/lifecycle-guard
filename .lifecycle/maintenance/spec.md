# Spec — v1.8.0: gate tests, project identity, log retention, duplicate/size audit, changelog

## Goal
Finish the hardening list: prove the Stop gate with tests; label projects by git root and make
scopes cover nested repos; stop the prompt log growing forever; surface near-duplicate rules and a
knowledge-base size budget in the audit; keep a CHANGELOG.md.

## Actors
User, prompt hook, Stop hook, SessionEnd hook, reviewer/skill (read rules + scope), /audit, CI.

## A. Stop gate tests (no behaviour change unless a test exposes a bug)
Cases: no .lifecycle; active + open boxes → block listing items (>12 truncated); `[~]` deferral and
`[x]` pass; all ticked + no review → review block; review PASS / `review: deferred` → pass; draft/done
→ no block; stop_hook_active → no block; stop_gate false → no block; multiple features.

## B. Project identity (single source: digest.project_name / project_scopes)
- Primary label = basename of the enclosing git root (walk up for `.git` dir or file, stop at $HOME);
  no git root → cwd basename. No subprocess (hooks stay fast). Remote names NOT used: they differ
  from folder names (vimal-tools → remote lifecycle-guard) and would relabel existing rules.
- Scope set = primary + basenames of cwd and every ancestor below $HOME. `[scope: X]` applies when X
  is in the set (case-insensitive) → an umbrella folder scope covers its nested repos.
- `digest.py --rules [--cwd DIR]` marks scoped rules outside the set as `N/A here (scope: X)`;
  `digest.py --project [DIR]` prints primary + scope set. Skill/reviewer use these instead of prose.
- Used by: on_prompt origin stamp, prompts/usage labels, bootstrap labels, known_projects.
- Migration: existing labels were cwd basenames; for repo roots and non-git folders they are
  unchanged; only sessions started in subfolders get their (better) repo name from now on.

## C. Log retention
- SessionEnd prunes `prompts.jsonl` and `corrections.jsonl` records older than `log_retention_days`
  (default 180; 0 = keep forever) — but never records newer than `last_learn_ts` (not yet learned).
  Atomic rewrite (temp + replace). usage.jsonl and changelog kept (small, evidence/audit trail).
- `--prune-logs` for manual runs; prints removed counts.

## D. Duplicates + size budget in the audit
- `possible-duplicate` flag: token-set similarity of two rules' normalized words (stopwords removed)
  ≥ `duplicate_threshold` (default 0.5, calibrated on the real KB); report names the partner id.
- Size line: each KB file's size; files over `kb_budget_kb` (default 12) flagged in the report header.
- /audit gains **merge**: fold one rule into the other (prefer keeping the text of the rule with more
  catches unchanged), keep the earliest learned date, drop the other; logged verbatim.

## E. CHANGELOG.md
History 1.0.0 → 1.8.0 at repo root; CONTRIBUTING: add an entry in the version-bump commit.

## Failure / edge cases
Unreadable .git file / worktree → still the folder containing `.git` is the root. cwd missing on disk
(old transcripts) → pure-path walk finds no .git → basename. Prune with corrupt lines → kept as-is
(never destroy what can't be parsed). Prune racing a prompt append → atomic replace; a concurrent
append may be lost only in a sub-millisecond window (documented, acceptable for a local log).
Duplicate check O(n²) on ~50–200 rules → trivial.

## Cross-cutting
All in existing files (digest.py, hooks, commands, skill, agent); config keys added to DEFAULT_CONFIG
and README. Privacy improves (retention). Tests for every part; CI runs them.

## Acceptance
- Gate: each case in A behaves as listed.
- cwd …/storefront/apps/ui with .git at storefront → label `crackerscity-storefront`; `[scope:
  CrackersCity]` applies there when CrackersCity is an ancestor; `--rules` marks other scopes N/A.
- Records 200 days old and before last learn → pruned; unlearned old records kept; 0 → nothing pruned.
- Two near-identical rules → both flagged possible-duplicate with each other's id; unrelated → not.
- KB file over budget → header warns.

## Out of scope
Automatic merging; remote-based identity; compressing archives.
