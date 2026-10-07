#!/usr/bin/env python3
"""Prepare raw material for /lifecycle-guard:learn.

  digest.py            new prompts + corrections since last learn (markdown to stdout)
  digest.py --bootstrap  mine ALL past Claude Code sessions in ~/.claude/projects
                         into chunk files under ~/.claude/lifecycle-guard/bootstrap/
  digest.py --mark     record that learning finished now
  digest.py --stats    counts only
  digest.py --audit [--json]
                       review learned rules: date, origin project, scope, age, usage, and flags
                       (no-origin / stale / looks-project-specific) for /lifecycle-guard:audit
  digest.py --rules [--cwd DIR]
                       list learned rules with ids (cited in review.md); scoped rules that don't
                       apply to DIR's project are marked "N/A here"
  digest.py --lint-spec FILE...
                       flag spec/task lines that could be pasted into any feature's spec unchanged
                       ("handle errors gracefully") — advisory; the reviewer judges
  digest.py --prune-logs
                       drop log records older than log_retention_days (never unlearned ones)
  digest.py --project [DIR]
                       the project label for DIR and the names a [scope: X] tag matches
  digest.py --usage    which rules reviews applied / caught misses with (for /lg-status)
"""
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA = Path(os.environ.get("LG_DATA_DIR", Path.home() / ".claude" / "lifecycle-guard"))
PROJECTS = Path.home() / ".claude" / "projects"
CHUNK_CHARS = 45000

# Single source of truth for "what did the user actually type" and "is it a correction".
# hooks/on_prompt.py and hooks/lg_common.py import these, so detection can't drift between
# the live hook and /learn or /bootstrap.
CORRECTION = re.compile(
    r"\b("
    r"you (missed|forgot|skipped|ignored|didn'?t|did not|haven'?t|have not|never)"
    r"|(is|are|was) missing|missing|forgot|left out"
    r"|not (done|complete|completed|finished|working|handled|implemented|covered)"
    r"|half[- ]?(done|baked|way)?|incomplete|partially"
    r"|where (is|are) the|what about (the)?"
    r"|(also|still) (need|needs|add|handle|missing)"
    r"|should (also|have)|why (didn'?t|did ?n'?t|no|is there no)"
    r"|again (you|it)|same mistake|i told you|as i said"
    r")\b",
    re.I,
)
# Text the harness injects as a "user" turn: never the user's own words.
# Tag blocks are stripped when they LEAD the prompt (user text after them is kept);
# plain-text markers mean the whole turn is injected.
MACHINE_TAGS = ("task-notification", "system-reminder", "command-name", "command-message", "command-args",
                "command-contents", "local-command-stdout", "local-command-stderr", "local-command-caveat",
                "bash-input", "bash-stdout", "bash-stderr", "user-prompt-submit-hook", "session-start-hook",
                "ide_opened_file", "ide_selection", "ide_diagnostics", "tool_use_error", "teammate-message")
MACHINE_TEXT = ("Caveat:", "[Request interrupted", "This session is being continued from a previous conversation")
LEADING_TAG = re.compile(r"^<(%s)\b[^>]*>" % "|".join(re.escape(t) for t in MACHINE_TAGS), re.I)
# Someone else's words pasted in (e.g. a comment being answered) — not the user's voice or corrections.
# Innermost-first, repeated, so nested/multiple blocks can't leak; unclosed = strip to the end.
PASTED_INNER = re.compile(r"<pasted_content\b[^>]*>(?:(?!<pasted_content\b).)*?</pasted_content\b[^>]*>",
                          re.S | re.I)
PASTED_OPEN = re.compile(r"<pasted_content\b.*\Z", re.S | re.I)
PASTED_STRAY = re.compile(r"</pasted_content\b[^>]*>", re.I)
PLACEHOLDER = re.compile(r"\[(?:Image|Pasted text) #\d+[^\]]*\]", re.I)


def clean_prompt(text):
    """The part of a prompt the user typed, or "" if there is none."""
    t = (text or "").strip()
    while True:  # peel leading injected blocks; keep what the user typed after them
        if t.startswith(MACHINE_TEXT):
            return ""
        m = LEADING_TAG.match(t)
        if not m:
            break
        close = re.search(r"</%s\s*>" % re.escape(m.group(1)), t, re.I)
        if not close:
            return ""
        t = t[close.end():].lstrip()
    prev = None
    while prev != t:
        prev, t = t, PASTED_INNER.sub(" ", t)
    t = PASTED_STRAY.sub(" ", PASTED_OPEN.sub("", t))
    t = PLACEHOLDER.sub(" ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r" ?\n ?", "\n", t).strip()


def is_correction(text):
    return bool(CORRECTION.search(clean_prompt(text)))


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


def _ancestors(cwd):
    """cwd and its parents, stopping below $HOME (or at the filesystem root)."""
    home = Path.home()
    p = Path(cwd)
    while p != p.parent and p != home:
        yield p
        p = p.parent


@lru_cache(maxsize=256)
def project_name(cwd):
    """Origin label for a directory: the enclosing git repo's folder name, so a session started in
    a subfolder (src/, apps/ui) is labelled with its repo. No git repo → the folder's own name.
    Folder names, not remote names: remotes can differ from folders and would relabel old rules."""
    if not cwd:
        return "?"
    for p in _ancestors(cwd):
        if (p / ".git").exists():
            return p.name
    return Path(cwd).name or "?"


def project_scopes(cwd):
    """Names a `[scope: X]` rule may use to apply here: the project plus every enclosing folder, so a
    scope on an umbrella folder (one holding several repos) covers each repo inside it."""
    names = [project_name(cwd)] + [p.name for p in _ancestors(cwd)] if cwd else []
    return list(dict.fromkeys(n for n in names if n and n != "?"))


def in_scope(scope, cwd):
    return not scope or scope.lower() in {n.lower() for n in project_scopes(cwd)}


def user_records(name, since=0.0, corrections=False):
    """Log records reduced to the user's own words. Filters at read time, so records logged by
    older versions (task notifications, pasted text) are ignored without rewriting user data."""
    out = []
    for r in read_jsonl(DATA / name, since):
        text = clean_prompt(r.get("prompt"))
        if text and (not corrections or CORRECTION.search(text)):
            out.append({**r, "prompt": text})
    return out


def since_last():
    since = cfg().get("last_learn_ts", 0)
    prompts = user_records("prompts.jsonl", since)
    corrections = user_records("corrections.jsonl", since, corrections=True)
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
            t = clean_prompt(t)
            if t and not t.startswith("/"):
                yield r.get("timestamp", ""), r.get("cwd", ""), t


def bootstrap():
    if not PROJECTS.is_dir():
        print(f"No Claude Code history at {PROJECTS}")
        return
    rows = []
    for f in PROJECTS.glob("*/*.jsonl"):
        # same origin label the prompt hook uses (digest.project_name: the git repo folder), so rules learned in the
        # moment and from bootstrap name their project identically
        fallback = f.parent.name.split("-")[-1] or f.parent.name
        for ts, cwd, t in user_texts(f):
            rows.append((ts, project_name(cwd) if cwd else fallback, t))
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


def prune_logs(now=None):
    """Drop prompt/correction log records older than log_retention_days (0 = keep forever), but never
    one newer than the last learn (not yet distilled). Lines that don't parse are kept. Atomic rewrite.
    usage.jsonl and changelog.md are kept: they are small and are the evidence/audit trail."""
    c = cfg()
    days = int(c.get("log_retention_days", 180))
    if days <= 0:
        return {}
    cutoff = min((now or time.time()) - days * 86400, c.get("last_learn_ts", 0))
    removed = {}
    for name in ("prompts.jsonl", "corrections.jsonl"):
        path = DATA / name
        if not path.exists():
            continue
        keep, dropped = [], 0
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                ts = json.loads(line).get("ts")
                old = isinstance(ts, (int, float)) and ts < cutoff  # no usable ts → keep
            except Exception:
                old = False
            if old:
                dropped += 1
            else:
                keep.append(line)
        if dropped:
            tmp = path.with_suffix(".jsonl.tmp")
            tmp.write_text("".join(l + "\n" for l in keep), encoding="utf-8")
            os.replace(tmp, path)
        removed[name] = dropped
    return removed


# --- spec lint ---------------------------------------------------------------
# The portability test (adapted from petergyang/no-ai-slop): a spec line that could move unchanged into
# any other feature's spec specifies nothing, and a vague box is easy to tick while the work is half done.
SPEC_SLOP = [
    (r"\bgraceful(ly)?\b", "say what happens: which error, what the actor sees, which state the entity ends in"),
    (r"\b(properly|correctly|appropriately|adequately|as expected)\b",
     "state the expected result (value, state, message)"),
    (r"\b(as needed|if needed|if necessary|when appropriate|where applicable)\b", "name the condition"),
    (r"\b(robust|seamless(ly)?|user[- ]friendly|intuitive|efficient(ly)?|scalable|performant)\b",
     "replace with something checkable (limit, latency, step count, failure handled)"),
    (r"\bbest practices?\b", "name the practice"),
    (r"\b(all|any|every) (edge|corner) cases?\b|\bedge cases (are )?(handled|covered)\b", "list the edge cases"),
    (r"(?<![/\w])etc\b\.?|\band so on\b|\bvarious\b", "list the items"),  # not /etc/hosts
    (r"\b(TBD|TODO|FIXME)\b|\?\?\?", "decide it, or move it to Out of scope"),
    (r"\b(ensure|make sure|keep)\b.{0,25}\bsecur(e|ity)\b|\bsecurity (is )?(handled|ensured)\b",
     "name the permission check, tenant scope or threat"),
    (r"\bhandle (all |any )?(the )?(errors?|failures?|exceptions?)\b", "name each failure and its outcome"),
    (r"\bnotif(y|ies|ied) (the )?(users?|customers?|admins?)\b"
     r"(?!.*\b(e-?mail|sms|whatsapp|push|in-app|webhook|slack|toast|banner)\b)",
     "name the channel and the message"),
]
SPEC_SLOP_RE = [(re.compile(p, re.I), hint) for p, hint in SPEC_SLOP]
# mentions, not requirements; a single-quoted span needs non-word chars around it, so the apostrophes in
# "user's … admin's" or "don't … won't" never swallow the text between them
QUOTED = re.compile(r"`[^`]*`|\"[^\"]*\"|“[^”]*”|(?<!\w)'[^'\n]{3,}'(?!\w)")
# Only requirement sections are linted when a spec has them; Goal / Root cause / Out of scope narrative
# isn't something anyone ticks. A file with none of these headings (tasks.md) is linted in full.
REQUIREMENT_SECTIONS = re.compile(r"\b(actors?|states?|state machine|capabilit\w*|failures?|edge|cross-cutting|"
                                  r"acceptance|criteri\w*|behaviou?rs?|requirements?)\b", re.I)
NEVER_LINT_SECTIONS = re.compile(r"out of scope|checklist coverage", re.I)


def lint_spec_text(text):
    """Return [(line_no, phrase, hint)] for vague requirement lines. Skips code fences, headings,
    quoted mentions and N/A lines; in a spec with requirement sections, lints only those."""
    lines = text.splitlines()
    sectioned = any(l.lstrip().startswith("#") and REQUIREMENT_SECTIONS.search(l) for l in lines)
    hits, fenced, active = [], False, not sectioned
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if s.startswith("#"):
            active = (not NEVER_LINT_SECTIONS.search(s)) and (not sectioned or bool(REQUIREMENT_SECTIONS.search(s)))
            continue
        if not active or not s or "N/A" in s:
            continue
        body = QUOTED.sub(" ", s)
        for rx, hint in SPEC_SLOP_RE:
            m = rx.search(body)
            if m:
                hits.append((n, m.group(0), hint))
                break  # one finding per line is enough to make the writer look at it
    return hits


def lint_spec(paths):
    total = 0
    for p in paths:
        path = Path(p)
        if not path.is_file():
            print(f"{p}: not found")
            continue
        for n, phrase, hint in lint_spec_text(path.read_text(encoding="utf-8", errors="replace")):
            print(f"{p}:{n} — \"{phrase}\" — {hint}")
            total += 1
    print(f"{total} vague line(s). Each could be pasted into any feature's spec: rewrite it to name the "
          "concrete actor / state / trigger / channel / error / limit." if total else
          "0 vague lines — every requirement is specific to this feature.")


def mark():
    c = cfg()
    c["last_learn_ts"] = time.time()
    save_cfg(c)
    print("marked")


def stats():
    since = cfg().get("last_learn_ts", 0)
    print(json.dumps({
        "prompts_total": len(user_records("prompts.jsonl")),
        "corrections_total": len(user_records("corrections.jsonl", corrections=True)),
        "prompts_new": len(user_records("prompts.jsonl", since)),
        "corrections_new": len(user_records("corrections.jsonl", since, corrections=True)),
        "domains": sorted(p.stem for p in (DATA / "domains").glob("*.md")),
        "last_learn": time.strftime("%Y-%m-%d %H:%M", time.localtime(since)) if since else "never",
    }, indent=2))


# --- rule audit -------------------------------------------------------------
# Rule line:  - [ ] [scope: proj] <rule> _(learned YYYY-MM-DD @ proj: cause)_ _(reviewed YYYY-MM-DD)_
# Legacy lines without "@ proj" still parse (flag no-origin); unstamped bullets under "## Learned" and
# stamps the regex can't read are kept and flagged too — the audit never silently drops a rule.
# Seed checklist items (outside "## Learned") are the plugin's baseline, not learned rules.
LEARNED = re.compile(r"_\(learned\s+(\d{4}-\d{2}-\d{2})(?:\s*@\s*(.+?))?\s*(?::\s*(.*?))?\)_", re.S)
REVIEWED = re.compile(r"_\(reviewed\s+(\d{4}-\d{2}-\d{2})[^)]*\)_")
SCOPE = re.compile(r"\[scope:\s*([^\]]+)\]", re.I)
HOSTNAME = re.compile(r"\b(?:[\w-]+\.)*[a-z][\w-]*\.(?:com|in|io|dev|app|net|org|city|co|ai|cloud)\b", re.I)
PLACEHOLDER_HOSTS = re.compile(r"(^|\.)(example|localhost|foo|bar|test|domain|yourdomain|mysite)\.", re.I)
# basenames too generic to mean "this rule is about that project"
GENERIC_NAMES = {"test", "tests", "code", "rule", "rules", "app", "apps", "src", "docs", "config", "node",
                 "project", "projects", "tmp", "temp", "repo", "work", "server", "client", "frontend",
                 "backend", "admin", "home", "desktop", "documents", "downloads", "scratch", "demo"}


def rule_id(text):
    """Stable id for a rule: hash of its normalized text (rewording a rule gives it a new id)."""
    norm = re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text or "")).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8]


SIMILARITY_STOP = set("a an the and or of to in on for not is are be by as at from with when every each must "
                      "its it this that new any all only never no than then into same one their own".split())


def rule_tokens(text):
    return {w for w in re.findall(r"[a-z][a-z0-9]+", (text or "").lower())
            if w not in SIMILARITY_STOP and len(w) > 2}


def similarity(a, b):
    """Word-set overlap (Jaccard). Catches the same lesson written twice in slightly different words;
    conceptual overlap (one rule a special case of another) is left to Claude in /audit."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def kb_files():
    files = [DATA / "core.md", DATA / "style.md"] + sorted((DATA / "domains").glob("*.md"))
    return [f for f in files if f.exists()]


def known_projects():
    """Project names seen in prompt history — a rule naming one is probably project-specific."""
    seen = Counter(project_name(r.get("cwd")) for r in read_jsonl(DATA / "prompts.jsonl"))
    return {n for n, k in seen.items()
            if k >= 2 and len(n) >= 4 and n != "?" and n.lower() not in GENERIC_NAMES}


def days_since(date_str, now):
    if not date_str:
        return None
    try:
        return int((now - time.mktime(time.strptime(date_str, "%Y-%m-%d"))) // 86400)
    except Exception:
        return None


def parse_rules():
    rules = []
    for f in kb_files():
        in_learned = False
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("#"):
                in_learned = line.lstrip("#").strip().lower().startswith("learned")
                continue
            if not line.lstrip().startswith(("-", "*")):
                continue
            m = LEARNED.search(line)
            stamped = "_(learned" in line
            if not (m or stamped or in_learned):
                continue
            scope = SCOPE.search(line)
            reviewed = REVIEWED.findall(line)
            text = LEARNED.sub("", REVIEWED.sub("", SCOPE.sub("", line)))
            text = re.sub(r"_\(learned\b[^)]*\)_", "", text)  # unreadable stamp, kept out of the text
            text = re.sub(r"^\s*[-*]\s*(\[[ x~]\]\s*)?", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            rules.append({
                "id": rule_id(text), "file": str(f.relative_to(DATA)), "line": n, "rule": text,
                "learned": m.group(1) if m else None,
                "origin": ((m.group(2) or "").strip() or None) if m else None,
                "cause": (m.group(3) or "").strip() if m else "",
                "scope": scope.group(1).strip() if scope else None,
                "reviewed": max(reviewed) if reviewed else None,
                "malformed": stamped and not m,
            })
    return rules


# --- rule usage ---------------------------------------------------------------
# review.md lists the rules a review applied; the Stop hook copies them into usage.jsonl:
#   ## Rules applied
#   - 1a2b3c4d caught — admin view was missing
#   - 5e6f7a8b satisfied
# lenient about decoration an LLM may add: **id**, [id], `id`, "id (core.md:55) — caught"
USAGE_LINE = re.compile(r"^\s*[-*]\s*[\[`*]*([0-9a-f]{8})[\]`*]*\b.*?\b(caught|satisfied)\b", re.I)


def parse_rules_applied(text):
    out, inside = [], False
    for line in (text or "").splitlines():
        if line.startswith("#"):
            inside = line.lstrip("#").strip().lower().startswith("rules applied")
            continue
        m = USAGE_LINE.match(line) if inside else None
        if m:
            out.append((m.group(1).lower(), m.group(2).lower()))
    return out


def ingest_usage(project_dir):
    """Append rule usage from every .lifecycle/*/review.md under project_dir. Idempotent: keyed on
    the review's parsed rules (not its prose), so repeated Stop runs and prose edits add nothing,
    while a re-review that changes the rules list counts as new evidence. Returns records added."""
    root = Path(project_dir) / ".lifecycle"
    if not root.is_dir():
        return 0
    usage = DATA / "usage.jsonl"
    seen = {r.get("review") for r in read_jsonl(usage)}
    added = []
    for rev in sorted(root.glob("*/review.md")):
        applied = parse_rules_applied(rev.read_text(encoding="utf-8", errors="ignore"))
        if not applied:
            continue
        ident = f"{Path(project_dir).resolve()}|{rev.parent.name}|{sorted(applied)}"
        key = hashlib.sha1(ident.encode()).hexdigest()[:16]
        if key in seen:
            continue
        seen.add(key)
        when = rev.stat().st_mtime  # when the review happened, not when we noticed it
        for rid, outcome in applied:
            added.append({"ts": when, "rule": rid, "outcome": outcome,
                          "project": project_name(str(project_dir)), "feature": rev.parent.name, "review": key})
    if added:
        DATA.mkdir(parents=True, exist_ok=True)
        with open(usage, "a", encoding="utf-8") as f:
            for r in added:
                f.write(json.dumps(r) + "\n")
    return len(added)


def usage_by_rule():
    stats = {}
    for r in read_jsonl(DATA / "usage.jsonl"):
        s = stats.setdefault(r.get("rule"), {"applied": 0, "caught": 0, "last_applied": None})
        s["applied"] += 1
        s["caught"] += r.get("outcome") == "caught"
        day = time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0)))
        s["last_applied"] = max(filter(None, [s["last_applied"], day]))
    return stats


def usage_summary():
    """Compact usage report for /lg-status: catches, never-applied count, top rules."""
    rules, _ = audit_rules()
    never = [r for r in rules if not r["applied"]]
    top = sorted((r for r in rules if r["applied"]), key=lambda r: (-r["caught"], -r["applied"]))[:5]
    print(f"{len(rules)} learned rules · {sum(1 for r in rules if r['caught'])} have caught a miss · "
          f"{len(never)} never applied in a review")
    for r in top:
        print(f"- `{r['id']}` applied {r['applied']}× (caught {r['caught']}, last {r['last_applied']}) — {r['rule'][:100]}")


def rules_list():
    cwd = sys.argv[sys.argv.index("--cwd") + 1] if "--cwd" in sys.argv else os.getcwd()
    print(f"# learned rules for project `{project_name(cwd)}` — skip lines marked N/A here")
    for r in parse_rules():
        scope = ""
        if r["scope"]:
            scope = f" [scope: {r['scope']}]" if in_scope(r["scope"], cwd) else f" N/A here (scope: {r['scope']})"
        print(f"{r['id']}  {r['file']}:{r['line']}{scope}  {r['rule'][:160]}")


def project_info():
    cwd = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    print(f"project: {project_name(cwd)}")
    print(f"scope matches: {', '.join(project_scopes(cwd))}")


def audit_rules():
    c = cfg()
    limit = int(c.get("review_after_days", 90))
    now = time.time()
    projects = known_projects()
    rules = parse_rules()
    usage = usage_by_rule()
    threshold = float(c.get("duplicate_threshold", 0.5))
    tokens = {id(r): rule_tokens(r["rule"]) for r in rules}
    for r in rules:
        r["similar_to"] = [o["id"] for o in rules if o is not r
                           and similarity(tokens[id(r)], tokens[id(o)]) >= threshold]
        r["exact_duplicate"] = any(o is not r and o["id"] == r["id"] for o in rules)
    for r in rules:
        r.update(usage.get(r["id"], {"applied": 0, "caught": 0, "last_applied": None}))
        flags = ["malformed"] if r["malformed"] else []
        if r["similar_to"]:
            flags.append("possible-duplicate")
        if not r["origin"]:
            flags.append("no-origin")
        # a rule that keeps getting applied stays fresh; only unreviewed AND unused rules go stale
        last_seen = max(filter(None, [r["learned"], r["reviewed"], r["last_applied"]]), default=None)
        age = days_since(last_seen, now)
        r["age_days"] = age
        if age is not None and age > limit:
            flags.append("stale")
        if not r["scope"]:
            body = f"{r['rule']} {r['cause']}"
            hits = sorted(p for p in projects if re.search(rf"\b{re.escape(p)}\b", body, re.I))
            hits += sorted({m.group(0).lower() for m in HOSTNAME.finditer(body)
                            if not PLACEHOLDER_HOSTS.search(m.group(0))})
            if hits:
                flags.append("looks-project-specific")
                r["mentions"] = hits
        r["flags"] = flags
    return rules, limit


def kb_sizes():
    budget = float(cfg().get("kb_budget_kb", 12))
    return budget, [(str(f.relative_to(DATA)), round(f.stat().st_size / 1024, 1)) for f in kb_files()]


def audit():
    rules, limit = audit_rules()
    budget, sizes = kb_sizes()
    over = [(name, kb) for name, kb in sizes if kb > budget]
    if "--json" in sys.argv:
        print(json.dumps({"review_after_days": limit, "kb_budget_kb": budget,
                          "kb_files": [{"file": n, "kb": kb, "over_budget": kb > budget} for n, kb in sizes],
                          "rules": rules}, indent=2, ensure_ascii=False))
        return
    if not rules:
        print("No learned rules found in the knowledge base.")
        return
    flagged = [r for r in rules if r["flags"]]
    counts = Counter(fl for r in rules for fl in r["flags"])
    scoped = sum(1 for r in rules if r["scope"])
    never = sum(1 for r in rules if not r["applied"])
    caught = sum(1 for r in rules if r["caught"])
    print(f"# Rule audit — {len(rules)} learned rules, {len(flagged)} need review "
          f"(stale after {limit} days)")  # header is one block (lg-status reads up to the first blank line)
    print(f"no-origin: {counts['no-origin']} · stale: {counts['stale']} · "
          f"looks-project-specific: {counts['looks-project-specific']} · "
          f"possible-duplicate: {counts['possible-duplicate']} · scoped: {scoped}")
    print(f"usage: {caught} rules have caught a miss · {never} never applied in a review")
    if over:
        print("size: " + ", ".join(f"{n} {kb} KB" for n, kb in over) +
              f" over the {budget:g} KB budget — consolidate overlapping rules")
    print()
    for r in flagged:
        where = f"@ {r['origin']}" if r["origin"] else "@ ?"
        scope = f" [scope: {r['scope']}]" if r["scope"] else ""
        rev = f", reviewed {r['reviewed']}" if r["reviewed"] else ""
        rev += f", applied {r['applied']}× (caught {r['caught']})" if r["applied"] else ", never applied"
        print(f"- `{r['id']}` `{r['file']}:{r['line']}` learned {r['learned'] or '?'} {where}{scope}{rev} "
              f"({'age unknown' if r['age_days'] is None else str(r['age_days']) + 'd'}) — **{', '.join(r['flags'])}**")
        if r.get("mentions"):
            print(f"  mentions: {', '.join(r['mentions'])}")
        if r["exact_duplicate"]:
            print(f"  exact duplicate: the same rule text appears more than once (id {r['id']})")
        others = [i for i in r["similar_to"] if i != r["id"]]
        if others:
            print(f"  similar to: {', '.join(others)}")
        print(f"  rule: {r['rule'][:220]}")
        if r["cause"]:
            print(f"  cause: {r['cause'][:160]}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--lint-spec":
        lint_spec(sys.argv[2:])
        sys.exit(0)
    if arg == "--prune-logs":
        print(json.dumps(prune_logs()))
        sys.exit(0)
    if arg == "--ingest-usage":  # used by the Stop hook; also handy by hand
        print(ingest_usage(sys.argv[2] if len(sys.argv) > 2 else "."))
        sys.exit(0)
    {"--bootstrap": bootstrap, "--mark": mark, "--stats": stats,
     "--audit": audit, "--rules": rules_list, "--usage": usage_summary,
     "--project": project_info}.get(arg, since_last)()
