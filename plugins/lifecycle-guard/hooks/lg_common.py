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
    bin/lg-digest.py   copied here so commands can call a fixed path (never downgraded)
    config.json        thresholds + last learn timestamp
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LG_DATA_DIR", Path.home() / ".claude" / "lifecycle-guard"))
SEED = PLUGIN_ROOT / "skills" / "lifecycle-guard" / "seed"

# scripts/digest.py owns prompt cleaning + correction detection (shared with /learn, /bootstrap)
sys.path.append(str(PLUGIN_ROOT / "scripts"))
try:
    from digest import CORRECTION, clean_prompt, ingest_usage, prune_logs  # noqa: E402,F401
    from digest import is_automated, maintain, over_budget_now  # noqa: E402,F401
    from digest import project_name as project_of  # noqa: E402,F401
except Exception as _err:  # never let a broken digest import take down the Stop gate
    import re as _re
    try:  # leave a trace: with the fallback, correction logging is off
        DATA.mkdir(parents=True, exist_ok=True)
        with open(DATA / "hook-errors.log", "a", encoding="utf-8") as _f:
            _f.write(f"{time.strftime('%Y-%m-%d %H:%M')} digest import failed, learning paused: {_err!r}\n")
    except Exception:
        pass
    CORRECTION = _re.compile(r"(?!x)x")  # matches nothing: no false corrections, no crash

    def clean_prompt(text):
        t = (text or "").strip()
        return "" if t.startswith("<") else t

    def ingest_usage(project_dir):
        return 0

    def prune_logs(now=None):
        return {}

    def maintain(now=None):
        return {}

    def over_budget_now():
        return []

    def is_automated(entrypoint):
        try:
            opted_in = json.loads((DATA / "config.json").read_text()).get("learn_from_automated") is True
        except Exception:
            opted_in = False
        return (entrypoint or "").startswith("sdk-") and not opted_in

    def project_of(cwd):
        return (Path(cwd).name if cwd else "") or "?"

DEFAULT_CONFIG = {
    "auto_learn": True,            # run /learn in background at session end
    "auto_learn_min_corrections": 2,
    "auto_learn_min_prompts": 40,
    "stop_gate": True,             # block "done" while tasks.md has open boxes
    "feature_nudge": True,         # inject lifecycle reminder on feature-like prompts
    "review_after_days": 90,       # /audit flags learned rules older than this as stale
    "log_retention_days": 180,     # prune prompt/correction logs older than this (0 = keep forever)
    "duplicate_threshold": 0.5,    # /audit flags rule pairs this similar as possible duplicates
    "kb_budget_kb": 12,            # /audit warns when a knowledge file grows past this size
    "rule_max_chars": 250,         # /learn keeps new rules this short; /audit flags longer ones too-long
    "learn_from_automated": False, # log prompts from `claude -p` / Agent SDK sessions (tools, not you)
    "last_compact_ts": 0,          # last background reword of too-long rules (at most once a day)
    "last_budget_nudge_ts": 0,     # last "file over budget, run /audit" reminder (at most once a week)
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
    # refresh the digest script so plugin updates propagate. Commands and agents use bin/lg-digest.py:
    # older plugin versions (still running in other sessions) rewrite bin/digest.py on every prompt, so
    # that name can't be trusted, and lg-digest.py is never replaced by an older copy.
    src = PLUGIN_ROOT / "scripts" / "digest.py"
    if src.exists():
        shutil.copy(src, DATA / "bin" / "digest.py")  # what older commands call
        dst = DATA / "bin" / "lg-digest.py"
        if not dst.exists() or script_version(dst) <= script_version(src):
            tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
            shutil.copy(src, tmp)
            os.replace(tmp, dst)  # atomic: a crash mid-copy can't leave a truncated script behind
    if not (DATA / "changelog.md").exists():
        (DATA / "changelog.md").write_text("# lifecycle-guard changelog\n\n")
    if not (DATA / "config.json").exists():
        save_config(DEFAULT_CONFIG)


def script_version(path) -> tuple:
    """VERSION = "x.y.z" in a digest.py copy; (0,) when it has none (anything before 1.12.0)."""
    try:
        m = re.search(r'^VERSION = "(\d+(?:\.\d+)*)"', Path(path).read_text(encoding="utf-8"), re.M)
        return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)
    except OSError:
        return (0,)


def load_config() -> dict:
    try:
        cfg = json.loads((DATA / "config.json").read_text())
    except Exception:
        cfg = {}
    return {**DEFAULT_CONFIG, **cfg}


def save_config(cfg: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    real = Path(os.path.realpath(DATA / "config.json"))  # a symlinked config stays a symlink
    tmp = real.with_name(f".{real.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(cfg, indent=2))
        if real.exists():
            try:
                shutil.copymode(real, tmp)  # keep e.g. 600
            except OSError:
                pass
        os.replace(tmp, real)  # atomic: a concurrent reader never sees half a file
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def update_config(**changes) -> bool:
    """Merge just these keys into the file's current content (not a stale in-memory copy). A config that
    exists but doesn't parse is left alone: it's the user's, maybe mid-write by another session."""
    p = DATA / "config.json"
    try:
        current = json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return False
    if not isinstance(current, dict):
        return False
    save_config({**current, **changes})
    return True


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
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ts", 0) <= since or is_automated(r.get("entrypoint")):
                continue
            # ignore records older versions logged from injected/pasted text
            text = clean_prompt(r.get("prompt"))
            if text and (name != "corrections.jsonl" or CORRECTION.search(text)):
                n += 1
    return n


def read_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}
