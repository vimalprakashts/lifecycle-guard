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
import time

sys.path.insert(0, os.path.dirname(__file__))
from lg_common import (DATA, count_since, ensure_data_dir, headless, is_automated, load_config,  # noqa: E402
                       maintain, prune_logs, update_config)

COMPACT_EVERY = 86400         # a background reword of too-long rules runs at most once a day…
COMPACT_SAME_EVERY = 7 * 86400  # …and at most weekly while the same rules stay too long (it isn't helping)
LOCK_STALE = 2 * 3600         # a lock this old is left over from a crashed run
READ_DIGEST = "~/.claude/lifecycle-guard/bin/lg-digest.py"  # as learn.md spells it
LEARN_RETRY = 86400           # after a learn run that didn't apply: wait a day…
LEARN_RETRY_SLOW = 7 * 86400  # …and a week after 3 in a row


def main() -> None:
    if headless():
        return
    ensure_data_dir()
    try:  # retention: the prompt log shouldn't grow forever (never drops unlearned records)
        prune_logs()
    except Exception:
        pass
    try:  # budget upkeep without a model: trim long causes, note too-long rules / over-budget files
        status = maintain()
    except Exception:
        status = {}
    # a `claude -p` / Agent SDK session (another plugin, a script) ends often: upkeep only, never a paid run
    if is_automated(os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")):
        return
    cfg = load_config()
    if not cfg.get("auto_learn"):
        return
    now = time.time()
    since = cfg.get("last_learn_ts", 0)
    corrections = count_since("corrections.jsonl", since)
    prompts = count_since("prompts.jsonl", since)
    enough = corrections >= cfg["auto_learn_min_corrections"] or prompts >= cfg["auto_learn_min_prompts"]
    # a previous run that didn't advance last_learn_ts failed (blocked, crashed, bad proposal): back off
    failed = cfg.get("learn_failures", 0) if cfg.get("last_learn_attempt_ts", 0) > since else 0
    if enough and failed and now - cfg.get("last_learn_attempt_ts", 0) < (LEARN_RETRY_SLOW if failed >= 3
                                                                       else LEARN_RETRY):
        enough = False
    # too-long rules (learned in the moment, or from before v1.12) need a model to reword them; /learn auto
    # does that with nothing new to learn too. Throttled so a rule it can't shorten doesn't loop.
    too_long = status.get("too_long") or []
    same = too_long == cfg.get("last_compact_ids")
    wait = COMPACT_SAME_EVERY if same else COMPACT_EVERY
    compact = bool(too_long) and now - cfg.get("last_compact_ts", 0) > wait
    if not (enough or compact):
        return
    # throttles and last_learn_ts live in config.json: if it exists but can't be read, nothing could be
    # recorded and a paid run would start every session — start none until it's readable again
    if not update_config():
        return
    claude = shutil.which("claude")
    if not claude:
        return
    lock = DATA / ".learn.lock"
    if lock.exists():
        if now - lock.stat().st_mtime < LOCK_STALE:
            return
        lock.unlink()  # left by a run that crashed: don't block learning forever
    lock.write_text(str(os.getpid()))
    try:
        update_config(last_learn_attempt_ts=now, learn_failures=failed + 1,
                      **({"last_compact_ts": now, "last_compact_ids": too_long} if compact else {}))
        env = {**os.environ, "LG_HEADLESS": "1"}
        # read-only: Claude Code refuses an unattended session's writes under ~/.claude, so the run only
        # PROPOSES (JSON as its final message) and lg-digest.py — run by this shell, not a Claude tool —
        # applies it: validated, backed up, logged, and never dropping a rule.
        cmd = [
            claude, "-p", "/lifecycle-guard:learn auto",
            "--add-dir", str(DATA),
            # Bash only for the digest script (prompt text is untrusted input to this run)
            "--allowedTools", f"Read,Glob,Grep,Bash(python3 {READ_DIGEST}:*)",
        ]
        proposal = DATA / ".learn-proposal"
        digest = DATA / "bin" / "lg-digest.py"
        q = shlex.quote
        wrapper = (f"{shlex.join(cmd)} 2>>{q(str(DATA / 'learn.log'))} | tee {q(str(proposal))} "
                   f">>{q(str(DATA / 'learn.log'))}; "
                   f"{q(sys.executable)} {q(str(digest))} --apply-proposal {q(str(proposal))} "
                   f">>{q(str(DATA / 'learn.log'))} 2>&1; rm -f {q(str(proposal))} {q(str(lock))}")
        with open(DATA / "learn.log", "a") as log:
            subprocess.Popen(["/bin/sh", "-c", wrapper], cwd=str(DATA), env=env,
                             stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                             start_new_session=True)
    except Exception:
        lock.unlink(missing_ok=True)  # never leave a lock behind for a run that didn't start
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
