# Spec — filter system-injected text out of learning input (v1.6.1)

## Goal
Only words the user typed feed correction detection, `prompts.jsonl` style learning and the auto-learn
thresholds. Today 6/11 logged "corrections" are `<task-notification>` blocks; pasted third-party text
(`<pasted_content>`) also counts as the user's voice.

## Actors
User (types prompts); harness (injects task notifications, system reminders, command output, pasted
blocks, image placeholders); prompt hook; `/learn` + `/bootstrap` (digest); session-end auto-learn.

## Behaviour (one shared `clean_prompt()` in `scripts/digest.py`, single source of truth)
- Starts with a machine block (`<task-notification>`, `<system-reminder>`, `<command-…>`,
  `<local-command-…>`, `<bash-…>`, `Caveat:`, `[Request interrupted`) → `""` (ignored entirely).
- `<pasted_content …>…</pasted_content …>` blocks removed; the user's surrounding text kept.
- `[Image #N]` / `[Pasted text #N …]` placeholders removed.
- Whitespace trimmed; empty result → ignored.
- ONE `CORRECTION` regex (the hook's, the more specific one) used by hook and bootstrap.

## Failure / edge cases
- Old polluted records in existing users' logs: filtered at READ time (digest since_last, --stats,
  lg_common.count_since) — no rewrite of user data, no migration step to forget.
- Hook can't import digest (corrupt install) → hook's try/except keeps the session alive.
- Prompt that is ONLY pasted content → ignored (it isn't the user's words).
- Unclosed pasted tag → strip from the tag to end (conservative: never learn from pasted text).

## Cross-cutting
Placement: extends existing `digest.py` (already "source of truth", copied to KB bin) — hooks import it
from the plugin's `scripts/`; no new module, no new copy step. Privacy improves (pasted third-party text
no longer stored). Performance: regexes only, hook stays well under timeout.

## Checklist coverage
Same rules across entry points ✓ (hook, bootstrap, digest, thresholds share one filter + one regex).
Migration ✓ (read-time filter covers existing records). UI/tenant/payments N/A.

## Acceptance
- Given a `<task-notification>` containing "missing", the hook logs nothing and emits nothing.
- Given "<pasted_content>…you missed…</pasted_content> next question", no correction is logged; the
  prompt is logged as "next question".
- Given "you missed the refund [Image #2]", a correction is logged without the placeholder.
- Given an existing corrections.jsonl with notification records, digest/--stats/count_since ignore them.
- Bootstrap skips machine blocks and pasted text.

## Out of scope
Rewriting/deleting existing log lines; rules already learned from noise (audit handles those).
