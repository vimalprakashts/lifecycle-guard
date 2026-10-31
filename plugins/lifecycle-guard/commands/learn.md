---
description: Distill recent prompts and corrections into checklist rules and style memory
argument-hint: "[auto]"
---

Update the lifecycle-guard knowledge base in `~/.claude/lifecycle-guard/` from new material. `D` below is `python3 ~/.claude/lifecycle-guard/bin/lg-digest.py`. Mode: `$ARGUMENTS`.

**`auto` mode** (the background run after a session): you can't write under `~/.claude`, and you mustn't. Never edit files and never ask questions. Do steps 1–5 by reading only, then end with ONE JSON object as your final message — nothing after it. `lg-digest.py --apply-proposal` applies it: it validates it, backs up, logs every original line verbatim, refuses anything that would lose a rule, then marks the digest as learned.

```json
{"add":    [{"file": "domains/payments.md", "rule": "<≤ 250 chars>", "project": "<[project] from the digest>", "cause": "<under 10 words>", "scope": "<project, only if it can't hold elsewhere>"}],
 "reword": [{"id": "<8-char id>", "rule": "<the same lesson, ≤ 250 chars>"}],
 "cause":  [{"id": "<8-char id>", "cause": "<under 10 words>"}]}
```

`file` is `core.md`, `style.md` or `domains/<name>.md` (a new domain file is created). There is no drop or merge: those need the user, in `/lifecycle-guard:audit`. Return `{}` when there's nothing to change.

1. Run `D` to get prompts and flagged corrections since the last learn. If it says newer records weren't shown, they stay pending for the next run. If both counts are zero, run `D --lint-rules`. If it flags no `too-long` rule and no `long-cause`: in `auto` mode return `{}`; otherwise run `D --mark` and stop. An `over-budget` file alone needs merges, which only `/lifecycle-guard:audit` makes with the user. Otherwise this is a compaction run: go straight to step 6.

2. Load the knowledge base: `D --context --full` (every rule, with its `[id]`).

3. From the **flagged corrections**, extract missed-scope lessons. Ignore false positives (questions, unrelated "missing" wording). For each real lesson:
   - Generalize it into a reusable rule that would have prevented the miss on a *different* project: portable across projects (no project, tenant or host names) but specific about the failure — the situation, the miss, and the check. "Handle payments properly" fails that test; "A payment QR for a partially paid order encodes the balance due, not the order total" passes.
   - Put it in the matching `domains/<domain>.md` under `## Learned`, or in `core.md` if it applies to any feature.
   - At most `rule_max_chars` (default 250) characters, leading with the situation and the check: the builder sees only the first ~100 characters as a headline until it fetches the rule.
   - Format: `- [ ] <rule> _(learned YYYY-MM-DD @ <project>: <cause in under 10 words>)_`. `<project>` is the `[project]` prefix of the correction in the digest.
   - If the rule only makes sense in that project (it names its tenants, hosts, paths, entities or data), scope it: `- [ ] [scope: <project>] <rule> …`. Prefer generalizing the wording; scope only what can't be generalized.

4. From **all prompts**, extract style and conventions for `style.md` (Stack / Code conventions / UI / Process). Only record explicit instructions ("always", "never", "use X not Y", "I prefer"), even if seen once, and implicit patterns seen in 2+ separate prompts. Same stamp and scoping as rules. Never record one-off task details, secrets, credentials, customer names, or personal information.

5. Deduplicate: if an equivalent rule exists, reword it sharper instead of adding a second one. If a new rule contradicts an old one, reword the old one to the new lesson. Either way it keeps its id history.

6. **Budget:** run `D --lint-rules`, then read the full text of every flagged rule with `D --rule <id>,<id>` (lint shows only a headline). Reword every rule flagged `too-long` (not only today's) to the limit, keeping the same lesson with the situation and the check first. Shorten every cause flagged `long-cause`. In `auto` mode, put all of steps 3–6 into the proposal and stop here.

7. **Interactive only, before any edit:** copy every file you'll touch to `backups/<filename>.<YYYYMMDD-HHMM>.bak` and snapshot the ids: `D --ids > ~/.claude/lifecycle-guard/.ids-before`.

8. Apply the edits. A reworded rule keeps its learned stamp and gets `_(was <old id>)_` appended (add to an existing `was` list) so its usage history follows it. If a file is `over-budget`, propose merges of overlapping rules and apply only the ones the user accepts (the merged rule's id goes into the kept rule's `was`). Then run `D --verify-ids ~/.claude/lifecycle-guard/.ids-before`: if it reports `missing`, fix the `was` stamp or restore that file from its backup until it prints `ok`.

9. Append to `changelog.md`: `## <date> learn`, then one line per rule added or changed with its file. For every rule reworded, add the full original line verbatim, indented as `    was: <line>`. Then run `D --mark`.

10. Reply with a compact summary: N rules added (by file), N style entries, N reworded, anything skipped as ambiguous. Add one line from `D --audit` (rules needing review) and suggest `/lifecycle-guard:audit` if any are flagged.
