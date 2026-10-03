# Spec — refresh the KB's digest.py on every prompt, including slash commands (v1.8.1)

## Goal
Commands call `~/.claude/lifecycle-guard/bin/digest.py`, which `ensure_data_dir()` refreshes from the
plugin. The prompt hook returned early for slash commands BEFORE refreshing, so right after
`/plugin update`, running `/lifecycle-guard:audit` used the previous version (seen live: no size line,
no duplicate flag).

## Behaviour
`on_prompt.py` calls `ensure_data_dir()` before any early return (still skipped when headless).
Slash commands are still not logged and get no nudges.

## Edge cases
ensure_data_dir failing → caught by the hook's top-level try/except (never breaks the prompt).
Cost: a ~30 KB file copy per prompt — unchanged from today for normal prompts.

## Acceptance
- Given a stale bin/digest.py, when the user types `/lifecycle-guard:audit`, then bin/digest.py equals
  the plugin's scripts/digest.py and nothing is logged to prompts.jsonl.
- Normal prompts behave as before.

## Out of scope
A SessionStart hook (not registered today; this fix covers the reported path).
