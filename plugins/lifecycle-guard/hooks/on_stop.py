#!/usr/bin/env python3
"""Stop hook: the definition-of-done gate.

If the project has an active feature (.lifecycle/<slug>/tasks.md containing
'status: active') with unchecked '- [ ]' items, Claude is not allowed to end
its turn. It must finish them, or explicitly defer them as '- [~] item — reason'.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from lg_common import headless, ingest_usage, load_config, read_hook_input  # noqa: E402

OPEN = re.compile(r"^\s*[-*] \[ \]\s+(.*)$")
# header line, tolerating markdown decoration: "status: active", "> status: active", "- status: active",
# "**Status:** active" — but not a task ("- [ ] … set status: active")
STATUS = re.compile(r"^[\s>*_-]*status\W{0,3}:\W*(\w+)", re.I | re.M)
# a filled-in verdict line — not the unedited template "VERDICT: PASS | FAIL"
VERDICT_OK = re.compile(r"^\W*verdict:\W*pass\b(?!\s*\|)|^\W*review:\s*deferred\b", re.I | re.M)


def active_task_files(cwd: Path):
    root = cwd / ".lifecycle"
    if not root.is_dir():
        return []
    files = []
    for f in root.glob("*/tasks.md"):
        try:
            head = f.read_text(encoding="utf-8")[:500]
        except Exception:
            continue
        # the header line, not the phrase anywhere ("- [ ] set status: active" is a task, not a status)
        m = STATUS.search(head)
        if m and m.group(1).lower() == "active":
            files.append(f)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def main() -> None:
    if headless():
        return
    data = read_hook_input()
    cwd = Path(data.get("cwd") or os.getcwd())
    try:  # record which learned rules reviews applied (feeds /audit); never affects the gate
        ingest_usage(cwd)
    except Exception:
        pass
    if data.get("stop_hook_active"):
        return  # already continued once because of us; don't loop forever
    if not load_config().get("stop_gate", True):
        return
    blockers = []
    for f in active_task_files(cwd):
        open_items = [m.group(1).strip() for line in f.read_text(encoding="utf-8").splitlines()
                      if (m := OPEN.match(line))]
        if open_items:
            blockers.append((f.relative_to(cwd), open_items))

    # Even with every box ticked, a feature is NOT done until an independent review
    # passed. Require a committed review artifact (.lifecycle/<feature>/review.md with
    # "VERDICT: PASS", or an explicit "review: deferred" reason). This fires only at
    # completion (no open boxes), so it never blocks mid-implementation turns.
    if not blockers:
        review_missing = []
        for f in active_task_files(cwd):
            rev = f.parent / "review.md"
            ok = False
            try:
                if rev.exists():
                    ok = bool(VERDICT_OK.search(rev.read_text(encoding="utf-8")))
            except Exception:
                ok = False
            if not ok:
                review_missing.append(f.parent.name)
        if review_missing:
            reason = (
                "[lifecycle-guard] All tasks are ticked but the mandatory independent review "
                "hasn't passed for: " + ", ".join(review_missing) + ".\n"
                "Run the reviewer now (the `lifecycle-reviewer` agent, or `/lifecycle-guard:review`): "
                "it reviews actor coverage, CTA/deep-link coverage, interactivity, failure paths and "
                "security in a fresh context. Fix its findings, then write the verdict to "
                ".lifecycle/<feature>/review.md (VERDICT: PASS). Only then set status: done."
            )
            print(json.dumps({"decision": "block", "reason": reason}))
            return
        return

    lines = []
    for path, items in blockers:
        lines.append(f"{path}: {len(items)} open")
        lines += [f"  - {i}" for i in items[:12]]
        if len(items) > 12:
            lines.append(f"  ... and {len(items) - 12} more")
    reason = (
        "[lifecycle-guard] Definition of done not met. Open items:\n" + "\n".join(lines) +
        "\n\nContinue implementing them (code + test), ticking each box when truly done. "
        "If an item genuinely belongs to a later phase or needs the user's input, change it to "
        "'- [~] <item> — <reason>' instead of leaving it open. When everything is ticked or deferred, "
        "run the tests, then set 'status: done' at the top of tasks.md."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
