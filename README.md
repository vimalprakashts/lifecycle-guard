# lifecycle-guard

**A full-lifecycle "definition of done" for Claude Code.** It makes Claude design the *whole* feature before writing code — every actor, state, failure path and cross-cutting concern — blocks it from stopping while work is half-done, and learns your style and its own misses automatically so it stops repeating them.

Distributed as a [Claude Code](https://claude.com/claude-code) plugin.

---

## The problem it solves

Left alone, an AI coding agent builds the **happy path for one actor and stops**. You ask for "add refunds" and you get the customer-facing button — but not the admin action, the partial-refund case, the webhook that reconciles the gateway, the notification to the customer, the audit log, or the test. You find the gaps days later, one by one.

`lifecycle-guard` turns that around:

- It **forces a spec first** — a real state machine and a per-actor checklist, so nothing is silently skipped.
- It **won't let Claude call the work "done"** while the task list still has open items.
- Every time you say *"you missed X"*, it **writes that lesson into a checklist** so the same miss can't happen on the next project.

The checklists are not static — they grow from your own corrections and prompts.

---

## What it does

| Piece | When | What it does |
|---|---|---|
| **`UserPromptSubmit` hook** | every prompt | Logs it (raw material for learning). A feature request → injects *"spec the full lifecycle first."* A correction (*"you missed the admin side"*) → tells Claude to fix it **and** record a reusable rule immediately. Never blocks your prompt. |
| **`lifecycle-guard` skill** | feature work | Loads your checklists + style → writes `.lifecycle/<feature>/spec.md` (actors, state machine, failure & edge cases, cross-cutting) → `tasks.md` → asks for your approval → builds task by task. |
| **`Stop` hook** | Claude tries to end its turn | **Blocks** while an active `tasks.md` still has open `- [ ]` items. Deferral has to be explicit: `- [~] item — reason`. |
| **`lifecycle-reviewer` agent** | Verify phase | An independent critic in a fresh context reviews every build against the spec — actor coverage, **CTA/deep-link coverage**, interactivity, failure paths, security — and the main agent fixes its findings in a bounded (token-aware) loop before anything is called done. |
| **`SessionEnd` hook** | session closes | If enough new corrections/prompts piled up, runs `/lifecycle-guard:learn` headless in the background to distill them into rules. |

---

## Requirements

- [Claude Code](https://claude.com/claude-code)
- `python3` on your `PATH` (the hooks and the digest script are Python; no third-party packages)

---

## Install

### From GitHub (recommended)

In Claude Code:

```
/plugin marketplace add vimalprakashts/lifecycle-guard
/plugin install lifecycle-guard@vimal-tools
/reload-plugins
```

> The repo is `lifecycle-guard`; the **marketplace** inside it is named `vimal-tools`, so the install target is `lifecycle-guard@vimal-tools`.

### From a local clone

```bash
git clone https://github.com/vimalprakashts/lifecycle-guard.git ~/claude-plugins/lifecycle-guard
```

```
/plugin marketplace add ~/claude-plugins/lifecycle-guard
/plugin install lifecycle-guard@vimal-tools
/reload-plugins
```

### First run (optional but recommended)

```
/lifecycle-guard:bootstrap
```

This mines **all your past Claude Code sessions** to seed your style and domain checklists, so your very first feature already benefits from everything your history can teach. One-time; requires `python3`.

---

## How to use

You mostly **don't** invoke it — it activates itself.

1. **Ask for a feature the way you normally would** — *"add a subscription renewal flow"*, *"build invoice uploads"*, *"integrate Stripe refunds"*. The prompt hook recognises it and the skill takes over.
2. **Claude writes the spec and task list first.** You'll get `.lifecycle/<feature>/spec.md` and `.lifecycle/<feature>/tasks.md` in your project, plus a short summary (how many actors, states, tasks; any `N/A` decisions). Review and approve once. *(Say "just proceed" and it skips the wait.)*
3. **Claude implements against the checklist**, ticking a box only when the code exists and a test covers it. It physically cannot end the turn while boxes are open.
4. **When you catch a gap**, just say so — *"you forgot the admin can't see rejected uploads"*. Claude fixes it, adds the task, and appends a generalised rule under `## Learned` in the right checklist. One short line tells you it learned; next project, that case is already on the list.

> **Scales to the request.** A one-line tweak (rename a label, change a colour) skips the spec entirely. The full workflow is for anything with new states, actors or integrations.

### Example

```
You:  add gift cards to checkout
Claude (spec):  Actors: customer, admin, finance, system(expiry cron), gateway(webhook).
                States: issued → active → partially_redeemed → redeemed → expired → voided.
                12 tasks across Backend / Customer UI / Admin UI / Jobs / Notifications / Tests / Ops.
                2 items marked N/A (no multi-currency yet). Approve?
You:  go
Claude:  …implements task by task… (Stop hook holds the turn until every box is ticked or deferred)
```

---

## Commands

| Command | What it does |
|---|---|
| `/lifecycle-guard:review` | Run the independent critic loop on a feature on-demand + write its `review.md` verdict |
| `/lifecycle-guard:lg-status` | What's been learned, what's pending, any active feature's open-task count |
| `/lifecycle-guard:audit` | Review learned rules: keep, scope to a project, reword or drop the stale / origin-unknown / project-specific ones |
| `/lifecycle-guard:learn` | Distill new prompts/corrections into rules now (also runs automatically) |
| `/lifecycle-guard:bootstrap` | One-time scan of your whole Claude Code history to seed everything |

---

## Where your knowledge lives

Everything learned lives **outside the plugin**, in `~/.claude/lifecycle-guard/`, so it survives plugin updates and is shared across every project:

- `core.md` — universal lifecycle checklist (applies to every feature)
- `style.md` — your stack, conventions and preferences, learned from your prompts
- `domains/*.md` — per-domain checklists (`payments.md`, `auth.md`, …), auto-created as you work; each has a `## Learned` section of rules that came from real misses
- `changelog.md` — every automatic change (audit trail); `backups/` — a snapshot before each change, to revert
- `config.json` — the settings below

These are plain Markdown — **edit them freely**. Treat `## Learned` items as mandatory: each exists because something was missed before.

Every learned rule carries its provenance, so it can be questioned later:

```
- [ ] [scope: shop-api] <rule> _(learned 2026-10-03 @ shop-api: <why>)_ _(reviewed 2027-01-05)_
```

`@ shop-api` is the project it was learned in (the git repo's folder name); `[scope: …]` (optional) limits it to that project — or to every repo under a folder of that name — so a lesson born in one codebase isn't applied everywhere; `_(reviewed …)_` records the last time you confirmed it. `/lifecycle-guard:audit` lists rules that are stale, have no recorded origin, or look project-specific but are global, and walks you through keep / scope / reword / drop — every decision is backed up and logged to `changelog.md`.

Rules also earn their place with evidence. Every independent review lists the learned rules it applied in `review.md` (`- <rule-id> caught — <gap>` or `- <rule-id> satisfied`), and the Stop hook records them in `usage.jsonl`. The audit then shows each rule as `applied N× (caught M)` or `never applied`: rules that keep getting applied stay fresh, and rules nobody has used in `review_after_days` come up for review.

> **Tip:** put `~/.claude/lifecycle-guard` in a private git repo to version your knowledge base and share domain checklists with your team.

---

## Configuration

Edit `~/.claude/lifecycle-guard/config.json`:

| Key | Default | Meaning |
|---|---|---|
| `auto_learn` | `true` | Run `/lifecycle-guard:learn` in the background at session end |
| `auto_learn_min_corrections` | `2` | Min new corrections to trigger auto-learn |
| `auto_learn_min_prompts` | `40` | …or min new prompts to trigger it |
| `stop_gate` | `true` | Block "done" while an active `tasks.md` has open boxes |
| `feature_nudge` | `true` | Inject the lifecycle reminder on feature-like prompts |
| `review_after_days` | `90` | `/lifecycle-guard:audit` flags rules not learned, reviewed or applied within this many days |
| `log_retention_days` | `180` | Prune logged prompts/corrections older than this at session end (never ones not yet learned); `0` keeps them forever |
| `duplicate_threshold` | `0.5` | Word overlap at which `/audit` flags two rules as possible duplicates |
| `kb_budget_kb` | `12` | `/audit` warns when a knowledge file grows past this size (every file is loaded for every feature) |

---

## Privacy & cost

- **Local only.** Your prompts are logged to `~/.claude/lifecycle-guard/prompts.jsonl` on your machine and never leave it. Only what you typed is kept (pasted text and system-injected messages are stripped), and records older than `log_retention_days` (180) are pruned once they've been learned from. The learn step is instructed to never record secrets, credentials, customer names or personal data into the checklists.
- **Auto-learn uses tokens.** With `auto_learn: true`, a background `claude -p` run fires at session end once the thresholds are met — that's a real (small) model call. Set `"auto_learn": false` to turn it off and run `/lifecycle-guard:learn` by hand instead.

---

## Uninstall

```
/plugin uninstall lifecycle-guard@vimal-tools
```

Your learned knowledge in `~/.claude/lifecycle-guard/` is left in place — delete that folder too if you want a clean slate.

---

## Contributing

Issues and PRs welcome — especially new seed `domains/*.md` checklists for common feature areas (`payments`, `auth` and `notifications` ship already; `search`, `billing`, `onboarding`… wanted). Keep rules general enough to prevent a miss on a *different* codebase. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE) © Vimal Prakash

## Auto-registered on install

Installing the plugin registers everything automatically — the hooks (prompt nudge, Stop gate, session-end learner), the `lifecycle-guard` skill, the `lifecycle-reviewer` agent and all commands. No wiring. (After *updating* an installed copy, run `/reload-plugins`.) The review is enforced per feature: the Stop hook won't let a feature be `status: done` until a committed `.lifecycle/<feature>/review.md` shows `VERDICT: PASS` (or an explicit deferral).

## AI-native SDLC alignment

Each feature leaves committed artifacts — `spec.md` → `tasks.md` → `review.md` — an audit trail a reviewer (or the next session) can read. Definition of done = build + tests + lint green with the output pasted, and an independent reviewer PASS; failing tests fix the code, never the test.
