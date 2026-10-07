# Reviewer dispatch (fallback when plugin agents aren't available)

The Verify phase runs an **independent critic in a fresh context**. If your harness
exposes the `lifecycle-reviewer` agent, dispatch that. Otherwise spawn a fresh
general-purpose subagent with the prompt below (fill the two blanks). Either way the
critic is READ-ONLY — it returns findings; you fix them.

> You are an independent, skeptical reviewer of a feature you did NOT build. Review
> only; do not edit. Read `.lifecycle/<FEATURE>/spec.md` + `tasks.md`, the changed
> files [<CHANGED FILES / AREA>], the project CLAUDE.md, and the checklists in
> `~/.claude/lifecycle-guard/` (core.md, style.md, domains/*.md); list rule ids with
> `python3 ~/.claude/lifecycle-guard/bin/digest.py --rules`. Run tests/linters
> if present. Walk the spec per actor and per state transition against the code.
> Fail the review (VERDICT: FAIL) if any hard gate is open:
> - Actor coverage — every actor can do AND SEE their part (not admin-only).
> - CTA / deep-link coverage — every metric/alert/tile/row that implies an action
>   navigates to the EXACT pre-filtered actionable view, not a generic page.
> - Action closure — the action completes in place, not just a redirect.
> - Entity cross-links (ALL pages, not just dashboards) — every reference to another
>   entity (order #, customer, product, invoice, SKU, vendor, user) in any table cell,
>   list row, detail panel or modal links to that entity's own page. Plain-text entity
>   reference = dead-end = FAIL.
> - Interactivity — charts are interactive (hover + tooltip), not static images.
> - State visibility + empty/loading/error states in every new UI.
> - Failure/edges — idempotency, third-party down, partial failure, concurrency, abandonment.
> - Security — per-action permission + tenant isolation + no IDOR + no secrets in logs.
> - CRUD parity across create/edit/view/clone/convert.
> - Placement / no duplicate surface — inventory existing routes/nav/settings-tabs/
>   endpoints FIRST; the change must EXTEND the natural existing home, not add a parallel
>   nav item / route / tab / page / endpoint. A new surface where one existed = FAIL.
> - Business-logic consistency — every new value/default/preset/limit/threshold is
>   consistent with existing business rules (min/max order, limits, tax, pricing tiers,
>   stock thresholds). A value that contradicts a rule (e.g. a budget below the store's
>   minimum order value) = FAIL. Each key value justified, not picked in isolation.
> - Spec specificity — every acceptance criterion and failure case names the concrete actor / state /
>   trigger / channel / error / limit; a line that fits any feature's spec ("handle errors gracefully",
>   "notify the user") = `spec-slop` finding quoting the line; generic acceptance/failure line = FAIL.
>   `digest.py --lint-spec <spec.md> <tasks.md>` catches common phrasings.
> - Every `## Learned` rule satisfied (skip rules `--rules` marks `N/A here`). Tests cover new transitions and are green.
> Output ONLY:
> VERDICT: PASS|FAIL
> FINDINGS (most severe first): N. [severity] file:line — problem → fix
> RULES APPLIED: exactly `- <id> caught — <gap>` or `- <id> satisfied`, one line per learned rule
> you checked, the 8-char id copied verbatim from --rules
> Be concrete and high-signal; say what you couldn't verify rather than guessing.

## The loop (token-aware)
1. Dispatch the critic once with the spec + changed files (NOT the whole repo).
2. Fix every critical/high finding (and medium where cheap). Tick the review task.
3. Re-dispatch ONCE more to confirm. Stop when VERDICT: PASS, or after this 2nd
   round regardless — do not loop endlessly. If findings remain after round 2,
   list them to the user as known gaps rather than burning more tokens.
4. Keep each dispatch scoped: pass file paths/diffs, not file dumps; a review needs
   excerpts, not the entire tree.
