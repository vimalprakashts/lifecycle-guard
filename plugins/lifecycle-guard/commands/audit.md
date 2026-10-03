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
   If nothing is flagged (and mode isn't `all`), say so and stop.

2. For **no-origin** rules, try to recover the origin before asking: search `corrections.jsonl` and `prompts.jsonl` (each record has `cwd`) and `bootstrap/part-*.md` (lines are `[project date]`) for the rule's cause or distinctive words around its learned date. Propose the project you find, or `?` if none.

3. Present the flagged rules grouped by flag, each with file:line, the rule, cause, origin and age, plus your recommendation:
   - **keep** — still true everywhere it applies.
   - **scope `<project>`** — true only in that project (names its tenants, hosts, paths, entities).
   - **reword** — the lesson is general but the wording is project-specific; offer the generalized wording.
   - **drop** — wrong, superseded, or about code that no longer exists.
   Ask the user to decide (use AskUserQuestion, at most 4 rules per question round; offer "accept all recommendations" for large batches, but "accept all" never covers **drop**: each drop is confirmed individually). Never decide alone. This command makes no edits without the user's answer.

4. Before editing any file, copy it to `backups/<filename>.<YYYYMMDD-HHMM>.bak`. Then apply:
   - keep → remove every existing `_(reviewed …)_` stamp and append one `_(reviewed <today>)_` at the end of the line.
   - scope → insert `[scope: <project>]` right after `- [ ] ` and stamp `_(reviewed <today>)_` (replacing older ones).
   - set origin → turn `_(learned DATE: cause)_` into `_(learned DATE @ <project>: cause)_`.
   - reword → replace the rule text and keep its learned stamp; stamp `_(reviewed <today>)_`.
   - drop → delete the line.

5. Append to `changelog.md`: `## <today> audit`, then one line per decision: `<keep|scope|reword|drop|origin> <file>: <rule, first 80 chars> — <reason>`. For **drop** and **reword**, log the full original line verbatim (indented under the entry) so it can be restored without digging through backups.

6. Re-run `digest.py --audit` and reply with a compact summary: N kept, N scoped, N reworded, N dropped, N origins set, N still flagged.
