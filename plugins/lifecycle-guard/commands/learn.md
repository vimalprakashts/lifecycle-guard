---
description: Distill recent prompts and corrections into checklist rules and style memory
argument-hint: "[auto]"
---

Update the lifecycle-guard knowledge base in `~/.claude/lifecycle-guard/` from new material. Mode: `$ARGUMENTS` (if `auto`, you are running unattended in the background: never ask questions, just apply).

1. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py` to get prompts and flagged corrections since the last learn. If both counts are zero, run `python3 ~/.claude/lifecycle-guard/bin/digest.py --lint-rules`: if it flags no `too-long` rule and no `long-cause`, run `--mark` and stop (an `over-budget` file alone needs merges, which only `/lifecycle-guard:audit` makes with the user). Otherwise this is a compaction run: skip to step 6 and do steps 6–10 for the flagged rules only.

2. Read `core.md`, `style.md` and every file in `domains/`.

3. From the **flagged corrections**, extract missed-scope lessons. Ignore false positives (questions, unrelated "missing" wording). For each real lesson:
   - Generalize it into a reusable rule that would have prevented the miss on a *different* project: portable across projects (no project, tenant or host names) but specific about the failure — the situation, the miss, and the check. "Handle payments properly" fails that test; "A payment QR for a partially paid order encodes the balance due, not the order total" passes.
   - Put it in the matching `domains/<domain>.md` under `## Learned` (create the domain file if needed, copying the section structure of `payments.md`), or in `core.md` under `## Learned` if it applies to any feature.
   - Keep it short: at most `rule_max_chars` (config, default 250) characters, leading with the situation and the check. The builder sees only a rule's first ~100 characters as a headline until it fetches the rule, so the headline must say when the rule applies.
   - Format: `- [ ] <rule> _(learned YYYY-MM-DD @ <project>: <cause in under 10 words>)_`. `<project>` is the `[project]` prefix of the correction in the digest; it records where the rule was born so it can be questioned later.
   - If the rule only makes sense in that project (it names its tenants, hosts, paths, entities or data), prefix it: `- [ ] [scope: <project>] <rule> …`. Prefer generalizing the wording so it holds anywhere; scope only what can't be generalized.

4. From **all prompts**, extract style and conventions into `style.md` under the right heading (Stack / Code conventions / UI / Process). Only record:
   - Explicit instructions ("always", "never", "use X not Y", "I prefer"), even if seen once.
   - Implicit patterns seen in 2+ separate prompts (same library choice, same folder layout, same way of describing a module).
   Style entries carry the same provenance stamp `_(learned YYYY-MM-DD @ <project>: <why>)_` and `[scope: <project>]` when project-specific (one project's stack is not every project's stack).
   Never record one-off task details, secrets, credentials, customer names, or personal information.

5. Deduplicate: if an equivalent rule exists, sharpen its wording instead of adding a second one (append `_(was <its old id>)_` when you reword it). If a new rule contradicts an old one, keep the newer and give it `_(was <old id>)_` (the old rule's id from `--context`/`--rules`), so the lesson's history carries over.

6. Before editing any file, copy it to `backups/<filename>.<YYYYMMDD-HHMM>.bak`, and snapshot every rule id: `python3 ~/.claude/lifecycle-guard/bin/digest.py --ids > ~/.claude/lifecycle-guard/.ids-before`.

7. **Budget check (write-time):** run `python3 ~/.claude/lifecycle-guard/bin/digest.py --lint-rules`. Reword EVERY rule flagged `too-long` (not only today's) to at most the limit: the same lesson, leading with the situation and the check, keeping its learned stamp and appending `_(was <old id>)_` (add to an existing `was` list) so its usage history follows it. Shorten any cause flagged `long-cause`. Rewording is non-destructive, so do it in `auto` mode too — but reword only flagged rules, and never drop or merge one unattended. Then run `python3 ~/.claude/lifecycle-guard/bin/digest.py --verify-ids ~/.claude/lifecycle-guard/.ids-before`: if it reports `missing`, an id was lost (a rule dropped, or reworded without its `was` stamp) — fix the stamp, or restore that file from its step-6 backup, until it prints `ok`. If a file is `over-budget`: interactively, propose merges of overlapping rules in it and apply the ones the user accepts (the merged rule's id goes into the kept rule's `was` stamp); in `auto` mode, never merge or drop rules unattended — list the file in your summary (the prompt hook reminds the user to run `/lifecycle-guard:audit`).

8. Append to `changelog.md`: date, mode, and one line per rule added, changed or removed (after any shortening in step 7), with the file it went into.

9. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --mark`.

10. Reply with a compact summary: N rules added (by file), N style entries, anything skipped as ambiguous. Add one line from `digest.py --audit` (rules needing review) and suggest `/lifecycle-guard:audit` if any are flagged.
