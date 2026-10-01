# Reviewer dispatch (fallback when plugin agents aren't available)

The Verify phase runs an **independent critic in a fresh context**. If your harness
exposes the `lifecycle-reviewer` agent, dispatch that. Otherwise spawn a fresh
general-purpose subagent with the prompt below (fill the two blanks). Either way the
critic is READ-ONLY — it returns findings; you fix them.

> You are an independent, skeptical reviewer of a feature you did NOT build. Review
> only; do not edit. Read `.lifecycle/<FEATURE>/spec.md` + `tasks.md`, the changed
> files [<CHANGED FILES / AREA>], the project CLAUDE.md, and the checklists in
> `~/.claude/lifecycle-guard/` (core.md, style.md, domains/*.md). Run tests/linters
> if present. Walk the spec per actor and per state transition against the code.
> Fail the review (VERDICT: FAIL) if any hard gate is open:
> - Actor coverage — every actor can do AND SEE their part (not admin-only).
> - CTA / deep-link coverage — every metric/alert/tile/row that implies an action
>   navigates to the EXACT pre-filtered actionable view, not a generic page.
> - Action closure — the action completes in place, not just a redirect.
> - Interactivity — charts are interactive (hover + tooltip), not static images.
> - State visibility + empty/loading/error states in every new UI.
> - Failure/edges — idempotency, third-party down, partial failure, concurrency, abandonment.
> - Security — per-action permission + tenant isolation + no IDOR + no secrets in logs.
> - CRUD parity across create/edit/view/clone/convert.
> - Every `## Learned` rule satisfied. Tests cover new transitions and are green.
> Output ONLY:
> VERDICT: PASS|FAIL
> FINDINGS (most severe first): N. [severity] file:line — problem → fix
> Be concrete and high-signal; say what you couldn't verify rather than guessing.

## The loop (token-aware)
1. Dispatch the critic once with the spec + changed files (NOT the whole repo).
2. Fix every critical/high finding (and medium where cheap). Tick the review task.
3. Re-dispatch ONCE more to confirm. Stop when VERDICT: PASS, or after this 2nd
   round regardless — do not loop endlessly. If findings remain after round 2,
   list them to the user as known gaps rather than burning more tokens.
4. Keep each dispatch scoped: pass file paths/diffs, not file dumps; a review needs
   excerpts, not the entire tree.
