# lifecycle-guard evals

Behavioural evals for the plugin, run by Claude Code's `claude plugin eval`. The unit tests in `../tests/`
cover the plumbing (hooks, gate, digest). These cases measure the plugin's actual behaviour: does a review
catch a real gap, and does a feature request get a complete spec before code. Each case runs with the
plugin and again without it, so the report shows what the plugin adds.

## Cases

All reviewer cases share one fixture: a small shop with a fully specified refunds feature
(`_fixtures/shop/`). Each case's `scaffold.sh` copies it and plants **one** gap.

| Case | Planted gap | Graded on |
|---|---|---|
| `customer-visibility` | refund status visible to the admin only | review names the customer-visibility gap |
| `generic-cta` | "refunds waiting" tile → unfiltered orders list | names the wrong destination |
| `plain-entity` | order number is plain text in the refunds table | names the missing order link |
| `spec-slop` | spec's failure cases + acceptance criteria are generic | calls out the vague spec lines |
| `unwired-endpoint` | reject endpoint exists, no reject button | names the missing reject action |
| `business-rule` | refund presets ignore "refund ≤ amount paid" | names the conflict with the cap |
| `parallel-surface` | new "Refund settings" tab duplicates Payments settings | names the duplicate surface |
| `complete-feature` | none (control) | does **not** claim any of the seven planted gaps (other findings on this small fixture are allowed) |
| `spec-first` | — (new feature: order cancellation) | the plan covers customer, admin, refund + stock, the ship race and concrete criteria (one grader each) |

Reviewer cases also carry two **routing indicators** (`routed-skill`, `routed-agent`): did the request
reach `/lifecycle-guard:review` and the `lifecycle-reviewer` agent? In a with/without run they're shown
as indicators and don't count toward the score. In a plugin-only run (`--ablation none`) they **do**
count, so a case that finds the gap but isn't routed scores 0.33 there.

The control can't be "the review says PASS": any rigorous review finds real gaps in a fixture this small
(missing test helpers, webhook races, validation). So it measures false alarms on the seven planted
dimensions only. When a review finds a real gap on one of those dimensions, fix the fixture, not the rubric.

## Running

```sh
# whole suite, with + without the plugin (9 cases × 3 runs × 2 arms ≈ 54 sessions)
claude plugin eval plugins/lifecycle-guard --scaffold --trust-plugin --judge-model sonnet \
  --allow-tools Write Edit --no-publish --max-cost-usd 30

# one case, one run, plugin arm only (≈ $0.30)
claude plugin eval plugins/lifecycle-guard --scaffold --trust-plugin --judge-model sonnet \
  --case generic-cta --runs 1 --ablation none --no-publish
```

- `--scaffold` is required: it builds each case's workspace from the fixture.
- `--judge-model sonnet` matters. The default judge (haiku) failed long, multi-finding reviews
  that plainly named the gap: 0/3 vs 3/3 with sonnet on identical runs. Without it, the suite wrongly
  says the reviewer makes reviews worse.
- `--allow-tools Write Edit` is needed only for `spec-first` (it writes the spec). Without it the case
  silently measures nothing.
- `--case` takes one glob, and a second `--case` replaces the first. Use a glob such as `--case '*-cta'`.
- LLM graders that read a file need an exact path (`focus: {source: file, path: …}` doesn't expand
  globs; `file_exists` does).
- Every run is a real model session on your account, so the suite is **not** run in CI. Results go to
  `evals/results/` (git-ignored).

## Reading the results

- **Score per arm**: share of runs whose graders passed. Runs are repeated (3 by default) because a
  behaviour that holds in one run can fail in the next.
- **Delta (with − without)**: what the plugin adds. A case where both arms pass means plain Claude
  already catches that gap, so the plugin adds nothing there. Report that rather than hiding it.
- **Routing indicators**: if `routed-agent` is low, prompts like "is this done?" aren't reaching the
  plugin's reviewer; fix the command/agent descriptions, not the rubric.
- Before changing a prompt (SKILL.md, the reviewer, a command), run the affected cases, make **one**
  change, and run them again. Keep the change only if the numbers hold.

## History

- 2026-10-29 (v1.10.0): first runs on `customer-visibility`.
  - Routing to the reviewer was 0/3; plain Claude reviewed the code on its own and found the gap 3/3.
  - Rewriting the `/lifecycle-guard:review` description around how users ask ("is it done / ready, review /
    verify it") changed routing to 3/3.
  - The routed reviews found the planted gap in 3/3 (sonnet judge). They also found three real defects
    in the fixture that plain Claude missed (gateway reference never stored, replayed webhook
    double-counting, "tests" ticked with none written). The fixture was then fixed so the control case is
    genuinely clean.
  - Cost per review: about $0.28 routed vs $0.16 unrouted.
  - A smoke run of every case (1 run, plugin arm only, sonnet judge): all seven planted gaps found and
    routed 7/7. The control first failed: the "complete" fixture had real gaps (no admin list endpoint
    behind the filtered queue, no customer request form). The fixture was fixed and the control redefined
    as above. A second failure came from an ambiguous rubric (a suggested *extra* tile was read as the
    planted tile gap), so the rubric was sharpened. Now 2/2.
  - `spec-first`:
    - The first run had no Write tool (missing `--allow-tools Write Edit`), so it measured nothing.
    - With write access, the plugin wrote a strong spec covering every rubric point: concrete
      Given/When/Then lines and 0 lint hits. It also ran the reviewer on its own work, which honestly
      recorded FAIL with status kept `active`.
    - The judge first graded the trace and missed the spec, because it only sees the first and last 12
      messages. It then graded the file, but `focus` file paths don't accept globs. The prompt now names the
      feature (`order-cancellation`) so the grader can read `.lifecycle/order-cancellation/spec.md`.
      Score 1.00 (3/3 votes).
  - All 9 cases validated in a plugin-only run. Building and validating the suite cost $15.56 in eval
    sessions.
- 2026-10-29: first with/without baseline (9 cases × 3 runs × 2 arms, sonnet judge, $21.18, 22 min).
  - **The seven planted-gap reviews: delta 0.** Plain Claude found every planted gap 3/3, just as the
    plugin did. For an explicit "is it done?" on someone else's code with one clear gap, the plugin adds
    no detection. The plugin's reviews were more thorough on everything else (extra real defects), at
    about 1.8× the cost. Its distinctive job, an independent check of work the agent built itself, isn't
    measured by these cases.
  - **Control: −0.33 was a fixture gap.** One plugin review flagged that the customer refunds component was
    never mounted, and that was true; plain Claude didn't notice. The fixture now mounts it
    (`src/customer/OrderPage.jsx`).
  - **spec-first: +1.00 was rigged.** Both graders only checked `.lifecycle/…`, a path only the plugin
    knows about, so the no-plugin arm scored 0 by construction. Those graders are now plugin-only
    indicators, and a new `plan-quality` grader judges the plan in the final response for both arms
    (later split into five `plan-*` graders, see below).
- 2026-10-29: re-run of the two corrected cases (3 runs × 2 arms, sonnet judge, $6.75).
  - **Control: 1.00 in both arms** once the customer component was mounted. No false alarms on the 7 dimensions.
  - **spec-first: 0.00 in both arms, again a grader artifact.** The single `plan-quality` grader needed
    all 5 points at once, so every run failed on one or two misses. That hid a real difference: the plugin
    covered the admin side and its own reviewer caught a double-refund path (refund endpoints still
    accepting cancelled orders); plain Claude had no admin side but did address the shipping race. 2 of 3
    plugin runs also hit the 900 s timeout mid-review, leaving a fragment as the last message. Fixed by
    splitting the rubric into five `plan-*` graders (partial credit) and raising the timeout to 1500 s.
  - Cost/time: the plugin arm ran ~2.5× the cost (about $1.20 vs $0.40 per run) and much longer, because
    it writes a spec and runs two review rounds.
