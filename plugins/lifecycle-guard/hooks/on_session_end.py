#!/usr/bin/env python3
"""SessionEnd hook: auto-learn in the background.

When enough new corrections or prompts have piled up since the last learn,
spawn a headless `claude -p` run of /lifecycle-guard:learn auto. It edits
only files inside ~/.claude/lifecycle-guard, writes a changelog, and exits.
Nothing to sit and review; check changelog.md whenever you like.
"""
import os
import shlex
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lg_common import DATA, count_since, ensure_data_dir, headless, load_config  # noqa: E402


def main() -> None:
    if headless():
        return
    ensure_data_dir()
    cfg = load_config()
    if not cfg.get("auto_learn"):
        return
    since = cfg.get("last_learn_ts", 0)
    corrections = count_since("corrections.jsonl", since)
    prompts = count_since("prompts.jsonl", since)
    if corrections < cfg["auto_learn_min_corrections"] and prompts < cfg["auto_learn_min_prompts"]:
        return
    claude = shutil.which("claude")
    if not claude:
        return
    lock = DATA / ".learn.lock"
    if lock.exists():
        return
    lock.write_text(str(os.getpid()))

    env = {**os.environ, "LG_HEADLESS": "1"}
    log = open(DATA / "learn.log", "a")
    cmd = [
        claude, "-p", "/lifecycle-guard:learn auto",
        "--add-dir", str(DATA),
        "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash(python3:*)",
        "--permission-mode", "acceptEdits",
    ]
    # Detached: survives this hook exiting. The learn command removes the lock.
    wrapper = f"{shlex.join(cmd)}; rm -f {shlex.quote(str(lock))}"
    subprocess.Popen(["/bin/sh", "-c", wrapper], cwd=str(DATA), env=env,
                     stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                     start_new_session=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
