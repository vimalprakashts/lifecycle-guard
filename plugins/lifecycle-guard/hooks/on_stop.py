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
from lg_common import headless, load_config, read_hook_input  # noqa: E402

OPEN = re.compile(r"^\s*[-*] \[ \]\s+(.*)$")


def active_task_files(cwd: Path):
    root = cwd / ".lifecycle"
    if not root.is_dir():
        return []
    files = []
    for f in root.glob("*/tasks.md"):
        try:
            head = f.read_text(encoding="utf-8")[:500].lower()
        except Exception:
            continue
        if "status: active" in head:
            files.append(f)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def main() -> None:
    if headless():
        return
    data = read_hook_input()
    if data.get("stop_hook_active"):
        return  # already continued once because of us; don't loop forever
    if not load_config().get("stop_gate", True):
        return
    cwd = Path(data.get("cwd") or os.getcwd())
    blockers = []
    for f in active_task_files(cwd):
        open_items = [m.group(1).strip() for line in f.read_text(encoding="utf-8").splitlines()
                      if (m := OPEN.match(line))]
        if open_items:
            blockers.append((f.relative_to(cwd), open_items))
    if not blockers:
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
