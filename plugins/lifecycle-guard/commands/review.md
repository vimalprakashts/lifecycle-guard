---
description: Run the independent lifecycle reviewer (critic) loop on a feature and write its verdict
argument-hint: "[feature-slug]"
---

Run the mandatory independent review for a feature and record the result. Target: `$ARGUMENTS` (a `.lifecycle/<slug>` feature; if omitted, use the most recently modified `.lifecycle/*/tasks.md` with `status: active` or `done`).

1. Identify the feature dir `.lifecycle/<slug>/` and read its `spec.md` + `tasks.md`. Determine the changed files (git diff for the feature, or the feature's code area).

2. **Dispatch the critic in a fresh context** — the `lifecycle-reviewer` agent if available, else a fresh general-purpose subagent using `references/review.md`. Pass it the spec/tasks paths and the changed files (paths/diff, NOT the whole repo — token discipline). It returns `VERDICT: PASS|FAIL` + ranked findings across actor coverage, **CTA/deep-link coverage**, action closure, **interactivity**, state visibility, failure/edge cases, security/tenancy, CRUD parity, `## Learned` rules, and tests.

3. **Fix** every critical/high finding (and cheap mediums). Where a fix is a reusable lesson, also apply "Learning in the moment" (append the rule to the right checklist).

4. **Re-dispatch once** to confirm. Stop at PASS or after this 2nd round — never loop more (token cap).

5. **Write the committed artifact** `.lifecycle/<slug>/review.md`:
   ```
   # Review — <slug>
   VERDICT: PASS | FAIL
   Reviewed: <YYYY-MM-DD> · rounds: <n>
   ## Findings addressed
   - [severity] <file> — <what> → <fix applied>
   ## Known gaps (deferred)
   - <item> — <reason>
   ## Rules applied
   - <id> caught — <gap it exposed>
   - <id> satisfied
   ```
   Copy the critic's RULES APPLIED list (merge both rounds: a rule that caught something in round 1 stays `caught`). The Stop hook records it in `~/.claude/lifecycle-guard/usage.jsonl`, which is how `/lifecycle-guard:audit` knows which rules earn their place.
   If the user intentionally defers the whole review, write `review: deferred — <reason>` instead. The Stop hook requires this artifact (PASS or deferred) before a feature can be `status: done`.

6. Run the test suite + lint and **paste the literal output**; a failing suite means the review is not PASS. Reply with a one-line summary (verdict, rounds, # findings fixed, any deferred).
