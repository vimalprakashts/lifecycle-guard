# Reviewer dispatch (fallback when plugin agents aren't available)

The Verify phase runs an **independent critic in a fresh context**. If your harness
exposes the `lifecycle-reviewer` agent, dispatch that. Otherwise spawn a fresh
general-purpose subagent with the prompt below (fill the blanks). Either way the
critic is READ-ONLY — it returns findings; you fix them.

> You are an independent, skeptical reviewer of a feature you did NOT build. Review
> only; do not edit. Read `.lifecycle/<FEATURE>/spec.md` + `tasks.md`, the changed
> files [<CHANGED FILES / AREA>] and the project CLAUDE.md. Load the checklists in one call:
> `python3 ~/.claude/lifecycle-guard/bin/digest.py --context --full --domains <DOMAINS>` (learned
> rules print as `[id] text`; out-of-scope rules are omitted). Round 2 (you're given round-1 findings): confirm each
> fix closes its finding and check the touched files for regressions; don't re-review the rest.
> Run tests/linters
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
> - Every learned rule in the `--context` output satisfied. Tests cover new transitions and are green.
> Output ONLY:
> VERDICT: PASS|FAIL
> FINDINGS (most severe first): N. [severity] file:line — problem → fix
> RULES APPLIED: exactly `- <id> caught — <gap>` or `- <id> satisfied`, one line per learned rule
> you checked, the 8-char id copied verbatim from the `--context` output
> Be concrete and high-signal; say what you couldn't verify rather than guessing.

## The loop (token-aware)
1. Round 1: dispatch the critic once with the spec + changed files + domains (NOT the whole repo).
2. Fix every critical/high finding (and medium where cheap). Tick the review task.
3. Round 2 ONLY if round 1 had critical/high findings: re-dispatch scoped to the round-1 findings,
   the fix for each and the files touched since — the critic confirms the fixes and checks for
   regressions, not the whole feature again. Round 1 PASS or only medium/low → no round 2.
   Never a third round; findings left are reported to the user as known gaps.
4. Keep each dispatch scoped: pass file paths/diffs, not file dumps.
