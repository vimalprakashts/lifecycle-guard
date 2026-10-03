# Changelog

All notable changes to lifecycle-guard. Releases: https://github.com/vimalprakashts/lifecycle-guard/releases

## 1.8.1 — 2026-10-03
- The knowledge base's `bin/digest.py` is refreshed on every prompt, including slash commands. Before,
  running `/lifecycle-guard:audit` right after `/plugin update` used the previous version's script.

## 1.8.0 — 2026-10-03
- **Stop gate fixes** (found by the new gate test suite): a draft whose task text mentioned
  `status: active` was treated as active; an unedited `VERDICT: PASS | FAIL` template, or "verdict: pass"
  in prose, unlocked the gate. The gate now reads the `status:` header line and a filled-in verdict line.
- **Project identity**: a project is labelled by its git repo's folder name, so sessions started in a
  subfolder (`src/`, `apps/ui`) get the repo's name. `[scope: X]` now also covers repos nested under a
  folder named X, and `digest.py --rules` marks rules scoped elsewhere `N/A here`. New `--project`.
- **Log retention**: prompt/correction logs older than `log_retention_days` (180) are pruned at session
  end, never before they've been learned from. New `--prune-logs`.
- **Audit**: `possible-duplicate` flag for rules written twice, a knowledge-file size budget
  (`kb_budget_kb`, 12 KB), and a consolidate/merge step for conceptually overlapping rules.
- Tests: Stop gate (15) and maintenance (9) suites; 53 tests total, run in CI.

## 1.7.0 — 2026-10-03
- Rule usage tracking: reviews list the learned rules they applied (`caught` / `satisfied`), the Stop
  hook records them, and the audit shows `applied N× (caught M)`. Used rules stay fresh. `--usage`.

## 1.6.1 — 2026-10-03
- Learn only from the user's own words: task notifications, system reminders, pasted text and image
  placeholders no longer feed correction detection or style learning. Old log records filtered on read.

## 1.6.0 — 2026-10-03
- Rule provenance: every learned rule records when, where (origin project) and why; `[scope: project]`;
  `/lifecycle-guard:audit` for keep / scope / reword / drop with backups and changelog.

## 1.5.0
- Every new value, default or limit is reconciled with existing business rules.

## 1.4.0
- Orient before building: extend the existing page/route/tab instead of adding a parallel one.

## 1.3.0
- Call-to-action coverage on every page: entity references link to the entity's own page.

## 1.2.0
- `/lifecycle-guard:review` and a committed `review.md` the Stop gate requires before "done".

## 1.1.0
- Enforced independent reviewer (fresh-context critic on a different model) with CTA-coverage review.

## 1.0.0 — 2026-10-01
- First public release: spec-first workflow, Stop gate, self-learning checklists and style memory.
