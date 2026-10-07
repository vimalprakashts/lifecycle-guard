---
description: Distill recent prompts and corrections into checklist rules and style memory
argument-hint: "[auto]"
---

Update the lifecycle-guard knowledge base in `~/.claude/lifecycle-guard/` from new material. Mode: `$ARGUMENTS` (if `auto`, you are running unattended in the background: never ask questions, just apply).

1. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py` to get prompts and flagged corrections since the last learn. If both counts are zero, run `python3 ~/.claude/lifecycle-guard/bin/digest.py --mark` and stop.

2. Read `core.md`, `style.md` and every file in `domains/`.

3. From the **flagged corrections**, extract missed-scope lessons. Ignore false positives (questions, unrelated "missing" wording). For each real lesson:
   - Generalize it into a reusable rule that would have prevented the miss on a *different* project: portable across projects (no project, tenant or host names) but specific about the failure — the situation, the miss, and the check. "Handle payments properly" fails that test; "A payment QR for a partially paid order encodes the balance due, not the order total" passes.
   - Put it in the matching `domains/<domain>.md` under `## Learned` (create the domain file if needed, copying the section structure of `payments.md`), or in `core.md` under `## Learned` if it applies to any feature.
   - Format: `- [ ] <rule> _(learned YYYY-MM-DD @ <project>: <cause in under 10 words>)_`. `<project>` is the `[project]` prefix of the correction in the digest; it records where the rule was born so it can be questioned later.
   - If the rule only makes sense in that project (it names its tenants, hosts, paths, entities or data), prefix it: `- [ ] [scope: <project>] <rule> …`. Prefer generalizing the wording so it holds anywhere; scope only what can't be generalized.

4. From **all prompts**, extract style and conventions into `style.md` under the right heading (Stack / Code conventions / UI / Process). Only record:
   - Explicit instructions ("always", "never", "use X not Y", "I prefer"), even if seen once.
   - Implicit patterns seen in 2+ separate prompts (same library choice, same folder layout, same way of describing a module).
   Style entries carry the same provenance stamp `_(learned YYYY-MM-DD @ <project>: <why>)_` and `[scope: <project>]` when project-specific (one project's stack is not every project's stack).
   Never record one-off task details, secrets, credentials, customer names, or personal information.

5. Deduplicate: if an equivalent rule exists, sharpen its wording instead of adding a second one. If a new rule contradicts an old one, keep the newer and note `(supersedes: <old>)`.

6. Before editing any file, copy it to `backups/<filename>.<YYYYMMDD-HHMM>.bak`.

7. Append to `changelog.md`: date, mode, and one line per rule added, changed or removed, with the file it went into.

8. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --mark`.

9. Reply with a compact summary: N rules added (by file), N style entries, anything skipped as ambiguous. Add one line from `digest.py --audit` (rules needing review) and suggest `/lifecycle-guard:audit` if any are flagged.
