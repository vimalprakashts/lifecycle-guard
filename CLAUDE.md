# vimal-tools — Claude Code plugin marketplace

A personal Claude Code plugin marketplace by Vimal Prakash. The catalog is
`.claude-plugin/marketplace.json`; each plugin lives under `plugins/<name>/`.

## Plugins

- **lifecycle-guard** (`plugins/lifecycle-guard/`) — full-lifecycle definition-of-done for
  every feature: forces a spec-first workflow, **blocks "done"** via a deterministic Stop gate
  until a checklist + an independent review pass, runs a **fresh-context critic on a different
  model**, and **learns** new checklist/style rules from your corrections over time.
  → Full design, file map, hooks, data model, and dev notes: **`plugins/lifecycle-guard/CLAUDE.md`**.

## Working here

- Each plugin is self-contained under `plugins/<name>/` with its own `.claude-plugin/plugin.json`
  (name/version). Add a new plugin by creating that dir and registering it in
  `.claude-plugin/marketplace.json`.
- Plugins ship only code + seed data. User/runtime data lives outside the repo under
  `~/.claude/` so it survives plugin updates (e.g. lifecycle-guard's knowledge base is at
  `~/.claude/lifecycle-guard/`).
- Changes take effect on `/reload-plugins` or a new session. No build step — Markdown + stdlib
  Python only.
- See `README.md` (overview) and `CONTRIBUTING.md` before structural changes.
