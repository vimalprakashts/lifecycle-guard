#!/usr/bin/env python3
"""Prepare raw material for /lifecycle-guard:learn.

  digest.py            new prompts + corrections since last learn (markdown to stdout)
  digest.py --bootstrap  mine ALL past Claude Code sessions in ~/.claude/projects
                         into chunk files under ~/.claude/lifecycle-guard/bootstrap/
  digest.py --mark     record that learning finished now
  digest.py --stats    counts only
"""
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

DATA = Path.home() / ".claude" / "lifecycle-guard"
PROJECTS = Path.home() / ".claude" / "projects"
CHUNK_CHARS = 45000

CORRECTION = re.compile(
    r"\b(you (missed|forgot|skipped|ignored|didn'?t|did not|haven'?t|never)|missing|forgot|left out|"
    r"not (done|complete|working|handled|implemented|covered)|half|incomplete|partially|"
    r"where (is|are) the|what about|(also|still) (need|add|handle)|should (also|have)|"
    r"why (didn'?t|no)|same mistake|i told you|as i said|again)\b", re.I)
NOISE = ("<command-", "<local-command", "Caveat:", "[Request interrupted", "<system-reminder")


def cfg():
    try:
        return json.loads((DATA / "config.json").read_text())
    except Exception:
        return {}


def save_cfg(c):
    (DATA / "config.json").write_text(json.dumps(c, indent=2))


def read_jsonl(path, since=0.0):
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("ts", 0) > since:
            out.append(r)
    return out


def project_name(cwd):
    return Path(cwd).name if cwd else "?"


def since_last():
    since = cfg().get("last_learn_ts", 0)
    prompts = read_jsonl(DATA / "prompts.jsonl", since)
    corrections = read_jsonl(DATA / "corrections.jsonl", since)
    print(f"# Digest since {time.strftime('%Y-%m-%d %H:%M', time.localtime(since)) if since else 'beginning'}\n")
    print(f"{len(prompts)} prompts, {len(corrections)} flagged corrections\n")
    print("## Flagged corrections (highest signal: missed scope / repeated mistakes)\n")
    for r in corrections:
        print(f"- [{project_name(r.get('cwd'))}] {r['prompt'][:800]}")
    print("\n## All prompts (mine for style, stack, conventions, recurring asks)\n")
    for r in prompts:
        print(f"- [{project_name(r.get('cwd'))}] {r['prompt'][:600]}")


def user_texts(path):
    """Yield user-typed text from a Claude Code transcript .jsonl."""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") != "user" or r.get("isMeta"):
            continue
        content = (r.get("message") or {}).get("content")
        texts = []
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        for t in texts:
            t = t.strip()
            if t and not t.startswith(NOISE) and not t.startswith("/"):
                yield r.get("timestamp", ""), t


def bootstrap():
    if not PROJECTS.is_dir():
        print(f"No Claude Code history at {PROJECTS}")
        return
    rows = []
    for f in PROJECTS.glob("*/*.jsonl"):
        proj = f.parent.name.split("-")[-1] or f.parent.name
        for ts, t in user_texts(f):
            rows.append((ts, proj, t))
    rows.sort()
    seen, uniq = set(), []
    for ts, proj, t in rows:
        key = t[:200].lower()
        if key not in seen:
            seen.add(key)
            uniq.append((ts, proj, t))

    corrections = [r for r in uniq if CORRECTION.search(r[2])]
    out = DATA / "bootstrap"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("part-*.md"):
        old.unlink()

    def blocks():
        yield "## Flagged corrections across all history (highest signal)\n"
        for ts, proj, t in corrections:
            yield f"- [{proj} {ts[:10]}] {t[:900]}"
        yield "\n## All prompts (style, stack, conventions)\n"
        for ts, proj, t in uniq:
            yield f"- [{proj} {ts[:10]}] {t[:500]}"

    part, buf, n = 1, [], 0
    for b in blocks():
        if n + len(b) > CHUNK_CHARS and buf:
            (out / f"part-{part:02d}.md").write_text("\n".join(buf), encoding="utf-8")
            part, buf, n = part + 1, [], 0
        buf.append(b)
        n += len(b) + 1
    if buf:
        (out / f"part-{part:02d}.md").write_text("\n".join(buf), encoding="utf-8")

    projects = Counter(p for _, p, _ in uniq)
    print(f"Mined {len(uniq)} unique prompts ({len(corrections)} look like corrections) "
          f"from {len(projects)} projects.")
    print(f"Wrote {part} chunk file(s) to {out}/ — process each part-NN.md in order.")


def mark():
    c = cfg()
    c["last_learn_ts"] = time.time()
    save_cfg(c)
    print("marked")


def stats():
    since = cfg().get("last_learn_ts", 0)
    print(json.dumps({
        "prompts_total": len(read_jsonl(DATA / "prompts.jsonl")),
        "corrections_total": len(read_jsonl(DATA / "corrections.jsonl")),
        "prompts_new": len(read_jsonl(DATA / "prompts.jsonl", since)),
        "corrections_new": len(read_jsonl(DATA / "corrections.jsonl", since)),
        "domains": sorted(p.stem for p in (DATA / "domains").glob("*.md")),
        "last_learn": time.strftime("%Y-%m-%d %H:%M", time.localtime(since)) if since else "never",
    }, indent=2))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    {"--bootstrap": bootstrap, "--mark": mark, "--stats": stats}.get(arg, since_last)()
