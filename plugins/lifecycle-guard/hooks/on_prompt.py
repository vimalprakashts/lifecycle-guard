#!/usr/bin/env python3
"""UserPromptSubmit hook.

1. Logs every prompt (raw material for learning your style).
2. Detects corrections ("you missed the admin side") -> queues them AND tells
   Claude to write the lesson into the domain checklist right now.
3. Detects feature requests -> reminds Claude to run the lifecycle-guard workflow.
Never blocks the prompt.
"""
import json
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from lg_common import (CORRECTION, DATA, append_jsonl, clean_prompt,  # noqa: E402
                       ensure_data_dir, headless, load_config, project_of, read_hook_input)

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
    data = read_hook_input()
    # only the user's own words: drop task notifications, system reminders, pasted text, placeholders
    prompt = clean_prompt(data.get("prompt"))
    if not prompt or prompt.startswith("/"):
        return
    ensure_data_dir()
    cfg = load_config()

    rec = {"prompt": prompt[:4000], "cwd": data.get("cwd", ""), "session": data.get("session_id", "")}
    append_jsonl("prompts.jsonl", rec)

    notes = []
    if CORRECTION.search(prompt):
        append_jsonl("corrections.jsonl", rec)
        project = project_of(rec["cwd"])
        notes.append(
            "[lifecycle-guard] This message looks like a correction of missed scope or a repeated mistake. "
            "After fixing it: (1) add the missing item to the active .lifecycle/<feature>/tasks.md; "
            f"(2) generalise it into a reusable rule and append it under '## Learned' in the matching file in "
            f"{DATA}/domains/ (create the domain file if none fits) or {DATA}/core.md if it applies to every "
            f"feature; format: '- [ ] <rule> _(learned YYYY-MM-DD @ {project}: <one-line cause>)_'. "
            f"If the rule only makes sense in this project (names its tenants, hosts, paths, entities), "
            f"prefix it with '[scope: {project}]' so it is not applied elsewhere. Skip duplicates. "
            "If it is a style/convention correction rather than missed scope, append it to "
            f"{DATA}/style.md instead. Do this silently in one edit; mention it in one short line at the end."
        )
    elif cfg.get("feature_nudge") and FEATURE.search(prompt) and len(prompt.split()) >= 4:
        notes.append(
            "[lifecycle-guard] This looks like a feature request. Use the lifecycle-guard skill: load "
            f"{DATA}/core.md, {DATA}/style.md and any relevant {DATA}/domains/*.md, write "
            ".lifecycle/<feature-slug>/spec.md + tasks.md covering every actor, state, failure path and "
            "cross-cutting concern BEFORE writing code. Skip only if the request is a trivial tweak."
        )

    if notes:
        emit("\n\n".join(notes))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a learning hook must never break the session
