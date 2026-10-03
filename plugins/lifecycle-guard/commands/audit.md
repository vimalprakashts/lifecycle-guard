---
description: Review learned rules — keep, scope to a project, or drop stale / project-specific ones
argument-hint: "[all]"
---

Review the lifecycle-guard knowledge base in `~/.claude/lifecycle-guard/`. Learned rules are injected into every project, so a rule that was right where it was born can be wrong elsewhere or go stale as code changes. This pass makes each one questionable. Mode: `$ARGUMENTS` (`all` = review every rule, not only flagged ones).

This command is interactive. If you are running headless (`LG_HEADLESS=1`, or `claude -p` with nobody to answer), print the step-1 report and stop: never edit rules unattended.

1. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --audit` (if that copy doesn't know `--audit` yet, the plugin was just updated: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/digest.py" --audit` instead). The rule format is
   `- [ ] [scope: <project>] <rule> _(learned YYYY-MM-DD @ <project>: <cause>)_ _(reviewed YYYY-MM-DD)_`
   (`[scope: …]` and `_(reviewed …)_` are optional). Flags:
   - **no-origin** — learned before provenance existed (or added by hand without a stamp); the project it came from is unknown.
   - **malformed** — has a `_(learned …)_` stamp the parser can't read; fix the stamp.
   - **stale** — not learned or reviewed within `review_after_days` (config, default 90).
   - **looks-project-specific** — unscoped but names a known project or a hostname.
   - **possible-duplicate** — shares most of its words with another rule (`similar to: <id>`): the same lesson written twice.
   The header also warns when a knowledge file is over `kb_budget_kb` (default 12 KB). Every file is loaded for every feature, so size costs tokens and dilutes attention.
   Each rule also shows its usage from past reviews: `applied N× (caught M)` or `never applied`. A rule that keeps being applied stays fresh (age counts from its last use); `caught` means it exposed a real miss — strong evidence to keep it. A stale rule that was never applied is the prime candidate for scope or drop.
   If no rule is flagged, no file is over the size budget, and mode isn't `all`, say so and stop. An over-budget file alone is reason enough to continue to step 2.

2. **Consolidate** (when a file is over budget, any rule is `possible-duplicate`, or mode is `all`): read the file's `## Learned` rules and propose merges for rules that overlap *conceptually*, such as one rule being a special case of another or two rules guarding the same failure from different angles. The duplicate flag only catches near-identical wording, so this is your judgement. For each merge, name the rule to keep. Prefer the one with more catches, kept word for word, because rewording resets its usage history. Fold the other rule's specifics into it only if they add something.

3. For **no-origin** rules, try to recover the origin before asking: search `corrections.jsonl` and `prompts.jsonl` (each record has `cwd`) and `bootstrap/part-*.md` (lines are `[project date]`) for the rule's cause or distinctive words around its learned date. Propose the project you find, or `?` if none.

4. Present the flagged rules grouped by flag, each with file:line, the rule, cause, origin and age, plus your recommendation:
   - **keep** — still true everywhere it applies.
   - **scope `<project>`** — true only in that project (names its tenants, hosts, paths, entities).
   - **reword** — the lesson is general but the wording is project-specific; offer the generalized wording.
   - **drop** — wrong, superseded, or about code that no longer exists.
   - **merge into `<id>`** — covered by another rule (from step 2).
   Ask the user to decide (use AskUserQuestion, at most 4 rules per question round; offer "accept all recommendations" for large batches, but "accept all" never covers **drop** or **merge**: each drop is confirmed individually). Never decide alone. This command makes no edits without the user's answer.

5. Before editing any file, copy it to `backups/<filename>.<YYYYMMDD-HHMM>.bak`. Then apply:
   - keep → remove every existing `_(reviewed …)_` stamp and append one `_(reviewed <today>)_` at the end of the line.
   - scope → insert `[scope: <project>]` right after `- [ ] ` and stamp `_(reviewed <today>)_` (replacing older ones).
   - set origin → turn `_(learned DATE: cause)_` into `_(learned DATE @ <project>: cause)_`.
   - reword → replace the rule text and keep its learned stamp; stamp `_(reviewed <today>)_`. Rewording changes the rule's id, so its usage history starts over — mention that when recommending a reword of a rule with catches.
   - drop → delete the line.
   - merge → edit the kept rule only if it must absorb a specific; give it the earlier of the two learned dates (keep its own origin and cause) and add `_(reviewed <today>)_`; then delete the merged rule. Treat the merge like a drop: confirm it individually.

6. Append to `changelog.md`: `## <today> audit`, then one line per decision: `<keep|scope|reword|merge|drop|origin> <file>: <rule, first 80 chars> — <reason>`. For **drop**, **merge** and **reword**, log the full original line verbatim (for a merge, both lines — the merged one and the kept one if it was edited) (indented under the entry) so it can be restored without digging through backups.

7. Re-run `digest.py --audit` and reply with a compact summary: N kept, N scoped, N reworded, N merged, N dropped, N origins set, the new file sizes, and N still flagged.
