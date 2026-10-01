# Contributing to lifecycle-guard

Thanks for helping make Claude Code finish what it starts. The most valuable
contribution is usually a **new domain checklist** — a reusable set of
lifecycle items for a common feature area — but fixes and improvements to the
hooks, skill and docs are just as welcome.

## Ways to contribute

- **Add a domain checklist** (`auth`, `notifications`, `payments` exist — add `search`, `billing`, `onboarding`, `uploads`, `chat`, `scheduling`, …).
- **Sharpen the core checklist** (`core.md`) with lifecycle items that apply to *any* feature.
- **Improve the skill or hooks** (clearer spec workflow, better correction/feature detection, fewer false positives).
- **Docs** — clarify the README, fix examples.

## Adding a domain checklist

1. Copy an existing file in `plugins/lifecycle-guard/skills/lifecycle-guard/seed/domains/` (e.g. `payments.md`) as the template.
2. Keep the section shape: actor groups (**Customer**, **Admin / ops**, **System**), then **Edge cases**, then a domain-specific section (**Compliance**, **Security**, …), and end with an empty `## Learned` heading.
3. Write items as checkboxes (`- [ ] …`), one concern each, imperative and **general enough to prevent a miss on a _different_ codebase** — no project-, company- or stack-specific details.
4. Leave `## Learned` empty; it fills from real corrections on the user's machine.

> These are **seed** files. They're copied into `~/.claude/lifecycle-guard/` on first run and only if a file of that name doesn't already exist, so they never clobber a user's learned knowledge.

## Rule style

- One idea per checkbox; prefer the failure it prevents ("Webhook may arrive before the browser redirect — both paths converge") over a vague noun ("webhooks").
- No secrets, credentials, customer names, or PII anywhere.
- Learned-rule format (when documenting one that came from a real miss): `- [ ] <rule> _(learned YYYY-MM-DD: <cause in under 10 words>)_`.

## Dev / testing

- Hooks are plain Python 3, no third-party packages — keep it that way so it runs anywhere `python3` does.
- Test locally: `/plugin marketplace add ~/path/to/your/clone` → `/plugin install lifecycle-guard@vimal-tools` → `/reload-plugins`, then try a feature prompt and a correction and watch `~/.claude/lifecycle-guard/`.
- A hook must **never** break the session — keep the top-level `try/except … pass` in each hook intact.

## Pull requests

Keep PRs focused (one domain file, or one behaviour change). Describe what miss or
behaviour it addresses. By contributing you agree your work is licensed under the
repository's [MIT License](./LICENSE).
