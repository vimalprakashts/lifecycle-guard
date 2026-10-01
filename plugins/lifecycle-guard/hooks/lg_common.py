"""Shared helpers for lifecycle-guard hooks.

All learned data lives OUTSIDE the plugin so it survives plugin updates:
  ~/.claude/lifecycle-guard/
    core.md            universal lifecycle checklist (seeded, then learns)
    style.md           your coding/product style (learned from prompts)
    domains/*.md       per-domain checklists (payments, auth, ...), auto-created
    prompts.jsonl      every prompt you type (raw material for style learning)
    corrections.jsonl  prompts that look like "you missed X" (raw material for gaps)
    changelog.md       every change /learn made (audit + revert reference)
    backups/           file snapshots before each learn
    bin/digest.py      copied here so commands can call a fixed path
    config.json        thresholds + last learn timestamp
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LG_DATA_DIR", Path.home() / ".claude" / "lifecycle-guard"))
SEED = PLUGIN_ROOT / "skills" / "lifecycle-guard" / "seed"

DEFAULT_CONFIG = {
    "auto_learn": True,            # run /learn in background at session end
    "auto_learn_min_corrections": 2,
    "auto_learn_min_prompts": 40,
    "stop_gate": True,             # block "done" while tasks.md has open boxes
    "feature_nudge": True,         # inject lifecycle reminder on feature-like prompts
    "last_learn_ts": 0,
}


def headless() -> bool:
    """True inside the background learner, so hooks don't recurse."""
    return os.environ.get("LG_HEADLESS") == "1"


def ensure_data_dir() -> None:
    (DATA / "domains").mkdir(parents=True, exist_ok=True)
    (DATA / "backups").mkdir(exist_ok=True)
    (DATA / "bin").mkdir(exist_ok=True)
    for name in ("core.md", "style.md"):
        if not (DATA / name).exists() and (SEED / name).exists():
            shutil.copy(SEED / name, DATA / name)
    seed_domains = SEED / "domains"
    if seed_domains.is_dir():
        for f in seed_domains.glob("*.md"):
            if not (DATA / "domains" / f.name).exists():
                shutil.copy(f, DATA / "domains" / f.name)
    # always refresh the digest script so plugin updates propagate
    src = PLUGIN_ROOT / "scripts" / "digest.py"
    if src.exists():
        shutil.copy(src, DATA / "bin" / "digest.py")
    if not (DATA / "changelog.md").exists():
        (DATA / "changelog.md").write_text("# lifecycle-guard changelog\n\n")
    if not (DATA / "config.json").exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> dict:
    try:
        cfg = json.loads((DATA / "config.json").read_text())
    except Exception:
        cfg = {}
    return {**DEFAULT_CONFIG, **cfg}


def save_config(cfg: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "config.json").write_text(json.dumps(cfg, indent=2))


def append_jsonl(name: str, record: dict) -> None:
    record.setdefault("ts", time.time())
    with open(DATA / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def count_since(name: str, since: float) -> int:
    p = DATA / name
    if not p.exists():
        return 0
    n = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                if json.loads(line).get("ts", 0) > since:
                    n += 1
            except Exception:
                pass
    return n


def read_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}
