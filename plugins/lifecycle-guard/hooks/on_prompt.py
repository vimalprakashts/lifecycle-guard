#!/usr/bin/env python3
"""UserPromptSubmit hook.

1. Logs every prompt (raw material for learning your style).
2. Detects corrections ("you missed the admin side") -> queues them AND tells
   Claude to write the lesson into the domain checklist right now.
3. Detects feature requests -> reminds Claude to run the lifecycle-guard workflow.
Never blocks the prompt.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from lg_common import (CORRECTION, DATA, append_jsonl, clean_prompt,  # noqa: E402
                       ensure_data_dir, headless, is_automated, load_config, over_budget_now, project_of,
                       read_hook_input, update_config)

NUDGE_EVERY = 7 * 86400  # the over-budget reminder: at most once a week

FEATURE = re.compile(
    r"\b(build|implement|develop|create|add|integrate|design|make|set ?up|wire up)\b"
    r".{0,80}\b(feature|module|flow|page|screen|api|endpoint|service|integration|"
    r"system|dashboard|portal|payment|checkout|auth|login|signup|onboarding|"
    r"notification|report|crud|workflow|upload|invoice|subscription|booking|"
    r"order|cart|admin|panel|form|webhook|scheduler|job)\b",
    re.I,
)


def emit(context: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


def main() -> None:
    if headless():
        return
    # refresh the KB (incl. bin/digest.py) before any early return: right after a plugin update the
    # first prompt is often a slash command (/lifecycle-guard:audit), which must use the new script
    ensure_data_dir()
    data = read_hook_input()
    # only the user's own words: drop task notifications, system reminders, pasted text, placeholders
    prompt = clean_prompt(data.get("prompt"))
    if not prompt or prompt.startswith("/"):
        return
    cfg = load_config()
    # a `claude -p` / Agent SDK session's prompts are written by a tool, not the user: never learn from
    # them, and don't spend that session's context on nudges either
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    if is_automated(entrypoint):
        return

    rec = {"prompt": prompt[:4000], "cwd": data.get("cwd", ""), "session": data.get("session_id", ""),
           "entrypoint": entrypoint}
    append_jsonl("prompts.jsonl", rec)

    notes = []
    if CORRECTION.search(prompt):
        append_jsonl("corrections.jsonl", rec)
        project = project_of(rec["cwd"])
        notes.append(
            "[lifecycle-guard] Looks like a correction. After fixing it, add the item to the active "
            ".lifecycle/*/tasks.md and record ONE rule under '## Learned' in "
            f"{DATA}/domains/<domain>.md (core.md if it applies to every feature, style.md if it's a "
            f"convention): '- [ ] <rule> _(learned YYYY-MM-DD @ {project}: <cause>)_'. The rule: portable (no "
            "project names), at most 250 chars, leading with the situation and the check (its first 100 chars "
            f"are its headline). Prefix '[scope: {project}]' if it only holds here. Strengthen an existing "
            "rule rather than duplicate. One silent edit; mention it in one line."
        )
    elif cfg.get("feature_nudge") and FEATURE.search(prompt) and len(prompt.split()) >= 4:
        notes.append(
            "[lifecycle-guard] This looks like a feature request. Use the lifecycle-guard skill: load the "
            f"checklists in one call (python3 {DATA}/bin/digest.py --context --domains <relevant ones from "
            f"{DATA}/domains/>), write "
            ".lifecycle/<feature-slug>/spec.md + tasks.md covering every actor, state, failure path and "
            "cross-cutting concern BEFORE writing code. Skip only if the request is a trivial tweak."
        )

    # the one budget fix that needs a person: merging rules in an over-budget file (SessionEnd records it)
    if cfg.get("kb_over_budget") and time.time() - cfg.get("last_budget_nudge_ts", 0) > NUDGE_EVERY:
        over = over_budget_now()  # re-check: an /audit since SessionEnd may have fixed it
        if over and update_config(last_budget_nudge_ts=time.time()):
            notes.append(f"[lifecycle-guard] {', '.join(over)} is over its size budget, which costs context on "
                         "every feature. At a natural pause, suggest the user run /lifecycle-guard:audit to merge "
                         "rules.")

    if notes:
        emit("\n\n".join(notes))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a learning hook must never break the session
