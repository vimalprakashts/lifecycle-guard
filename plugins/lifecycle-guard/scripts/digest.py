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
  digest.py --context [--domains a,b] [--cwd DIR] [--full]
                       one compact load for a feature: core + style + the named domains, learned rules
                       as [id] text, rules scoped to other projects omitted; core/style rules as a
                       headline index unless --full (skill uses the index, the reviewer --full)
  digest.py --rule ID[,ID]  full text of those rules
  digest.py --lint-rules    rules over rule_max_chars, files over kb_budget_kb (write-time budget)
  digest.py --footprint     what a feature costs in context with this knowledge base
  digest.py --maintain      automatic upkeep (SessionEnd): trim long causes; record too-long rules and
                            over-budget files in config.json for the hooks
  digest.py --ids / --verify-ids SNAPSHOT
                            snapshot every rule id, then check none was lost (unattended-edit guard)
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
import shutil
import sys
import tempfile
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

VERSION = "1.12.0"  # the hooks never replace bin/lg-digest.py with an older copy
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


def write_atomic(path, text, newline=None):
    """Replace a file's content all at once: readers never see half a file. Writes next to the REAL file
    (a symlinked KB or config stays a symlink) and keeps its permissions."""
    real = Path(os.path.realpath(path))
    tmp = real.with_name(f".{real.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        if real.exists():
            try:
                shutil.copymode(real, tmp)
            except OSError:
                pass
        os.replace(tmp, real)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def save_cfg(c):
    write_atomic(DATA / "config.json", json.dumps(c, indent=2))


def update_cfg(**changes):
    """Merge keys into config.json. A config that exists but doesn't parse is the user's (maybe mid-write
    by another session): leave it alone rather than replace it with just these keys."""
    p = DATA / "config.json"
    try:
        current = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return False
    if not isinstance(current, dict):
        return False
    current.update(changes)
    save_cfg(current)
    return True


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


# --- automated sessions ---------------------------------------------------------
# Claude Code sets CLAUDE_CODE_ENTRYPOINT=sdk-cli for `claude -p` (sdk-ts / sdk-py for Agent SDK apps);
# an interactive terminal is `cli`. Prompts in those sessions are written by tools (other plugins'
# summarizers, app backends, scripts), not by the user, so they must never become rules.
# The per-user system temp dir only (macOS /var/folders/…/T): where tools run throwaway sessions. /tmp is
# never a root — people work there, and the observed leak (a summarizer's cwd) was under /var/folders.
TEMP_ROOTS = tuple(({os.path.realpath(tempfile.gettempdir()), "/private/var/folders", "/var/folders"})
                   - {"/tmp", "/private/tmp"})  # on Linux gettempdir() IS /tmp: only the entrypoint check applies


def learn_from_automated():
    return cfg().get("learn_from_automated") is True  # a string "false" must not opt in


def is_automated(entrypoint):
    return (entrypoint or "").startswith("sdk-") and not learn_from_automated()


def in_temp_dir(cwd):
    real = os.path.realpath(cwd) if cwd else ""
    return any(real == t or real.startswith(t + os.sep) for t in TEMP_ROOTS)


_ENTRYPOINTS = {}


def session_entrypoint(session):
    """Entrypoint recorded in the session's transcript, None if there's no transcript."""
    if not session or not re.fullmatch(r"[\w-]+", session):
        return None
    if session not in _ENTRYPOINTS:
        _ENTRYPOINTS[session] = None
        for f in PROJECTS.glob(f"*/{session}.jsonl"):
            try:
                with open(f, encoding="utf-8", errors="ignore") as fh:
                    for _, line in zip(range(50), fh):
                        if '"entrypoint"' in line:
                            try:
                                _ENTRYPOINTS[session] = json.loads(line).get("entrypoint")
                            except Exception:
                                continue
                            break
            except OSError:
                pass  # unreadable transcript: treat as missing
            break
    return _ENTRYPOINTS[session]


def automated_record(r):
    """Read-time filter. New records carry the entrypoint; older ones are looked up in their transcript,
    and one with no transcript that ran in the system temp dir was a tool's throwaway session."""
    if "entrypoint" in r:
        return is_automated(r["entrypoint"])
    ep = session_entrypoint(r.get("session"))
    if ep is not None:
        return is_automated(ep)
    return in_temp_dir(r.get("cwd")) and not learn_from_automated()


def user_records(name, since=0.0, corrections=False):
    """Log records reduced to the user's own words. Filters at read time, so records logged by
    older versions (task notifications, pasted text, automated sessions) are ignored without rewriting
    user data."""
    out = []
    for r in read_jsonl(DATA / name, since):
        if automated_record(r):
            continue
        text = clean_prompt(r.get("prompt"))
        if text and (not corrections or CORRECTION.search(text)):
            out.append({**r, "prompt": text})
    return out


def digest_max():
    try:
        return int(cfg().get("digest_max_chars", 20000))
    except (TypeError, ValueError):
        return 20000


def since_last():
    """New material for /learn, capped at digest_max_chars. The window is contiguous and oldest first, so
    --mark can advance exactly to the last record shown and the rest stays pending for the next run."""
    since = cfg().get("last_learn_ts", 0)
    prompts = user_records("prompts.jsonl", since)
    corrections = user_records("corrections.jsonl", since, corrections=True)
    budget, cutoff, used, last = digest_max(), None, 0, None
    for r in sorted(corrections + prompts, key=lambda r: r.get("ts", 0)):
        used += min(len(r["prompt"]), 800) + 40  # what printing it costs
        if used > budget:
            cutoff = last if last is not None else r.get("ts", 0)  # always show at least one record
            break
        last = r.get("ts", 0)
    if cutoff is not None:
        hidden = sum(1 for r in prompts + corrections if r.get("ts", 0) > cutoff)
        prompts = [r for r in prompts if r.get("ts", 0) <= cutoff]
        corrections = [r for r in corrections if r.get("ts", 0) <= cutoff]
    update_cfg(digest_cursor=cutoff)  # --mark advances only this far when the digest was cut
    print(f"# Digest since {time.strftime('%Y-%m-%d %H:%M', time.localtime(since)) if since else 'beginning'}\n")
    print(f"{len(prompts)} prompts, {len(corrections)} flagged corrections\n")
    if cutoff is not None:
        print(f"({hidden} newer records not shown — they stay pending for the next /lifecycle-guard:learn)\n")
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
        if r.get("type") != "user" or r.get("isMeta") or is_automated(r.get("entrypoint")):
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
    cursor = cfg().get("digest_cursor")  # the digest was cut: only what it showed counts as learned
    done = update_cfg(last_learn_ts=cursor or time.time(), digest_cursor=None)
    print("marked" if done else "config.json unreadable: not marked")


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
# a reworded or merged rule keeps the ids it used to have, so its usage history follows it
WAS = re.compile(r"_\(was\s+([0-9a-f]{8}(?:[\s,]+[0-9a-f]{8})*)\)_")
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
        rules += parse_lines(f.read_text(encoding="utf-8").split("\n"), str(f.relative_to(DATA)))
    return rules


def parse_lines(lines, rel):
    """Learned rules in one file's lines (parse_rules for a file; maintain checks an edit with it)."""
    rules = []
    in_learned = False
    for n, line in enumerate(lines, 1):
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
        was = [i for m in WAS.findall(line) for i in re.findall(r"[0-9a-f]{8}", m)]
        text = LEARNED.sub("", REVIEWED.sub("", SCOPE.sub("", WAS.sub("", line))))
        text = re.sub(r"_\(learned\b[^)]*\)_", "", text)  # unreadable stamp, kept out of the text
        text = re.sub(r"^\s*[-*]\s*(\[[ x~]\]\s*)?", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        rules.append({
            "id": rule_id(text), "file": rel, "line": n, "rule": text,
            "learned": m.group(1) if m else None,
            "origin": ((m.group(2) or "").strip() or None) if m else None,
            "cause": (m.group(3) or "").strip() if m else "",
            "scope": scope.group(1).strip() if scope else None,
            "reviewed": max(reviewed) if reviewed else None,
            "was": was,
            # a stamp closed with ")" instead of ")_" makes the cause swallow the next stamp
            "malformed": (stamped and not m) or bool(m and "_(" in (m.group(3) or "")),
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


def merged_usage(usage, ids):
    """Usage of a rule across its current id and the ids it had before a reword/merge."""
    out = {"applied": 0, "caught": 0, "last_applied": None}
    for i in ids:
        s = usage.get(i)
        if s:
            out["applied"] += s["applied"]
            out["caught"] += s["caught"]
            out["last_applied"] = max(filter(None, [out["last_applied"], s["last_applied"]]), default=None)
    return out


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
    cwd = os.path.abspath(flag_value("--cwd") or os.getcwd())
    print(f"# learned rules for project `{project_name(cwd)}` — skip lines marked N/A here")
    for r in parse_rules():
        scope = ""
        if r["scope"]:
            scope = f" [scope: {r['scope']}]" if in_scope(r["scope"], cwd) else f" N/A here (scope: {r['scope']})"
        print(f"{r['id']}  {r['file']}:{r['line']}{scope}  {r['rule'][:160]}")


def flag_values(name):
    """Every token after `name` up to the next flag: `--domains a, b` and `--domains a b` both work."""
    if name not in sys.argv:
        return []
    out = []
    for tok in sys.argv[sys.argv.index(name) + 1:]:
        if tok.startswith("--"):
            break
        out.append(tok)
    return out


def flag_value(name):
    """The value after `name` in argv, or None when it's missing or is the next flag."""
    if name in sys.argv:
        i = sys.argv.index(name) + 1
        if i < len(sys.argv) and not sys.argv[i].startswith("--"):
            return sys.argv[i]
    return None


HEADLINE_CHARS = 100


def headline(text):
    """A rule's index line: the whole rule if short, else its first ~100 chars cut at a word."""
    if len(text) <= HEADLINE_CHARS + 20:
        return text
    return text[:HEADLINE_CHARS].rsplit(" ", 1)[0].rstrip(",;:—- ") + " …"


def context():
    """One compact load of the checklists for a feature: core + style + the named domains, learned rules
    with ids, out-of-scope rules dropped, provenance stamps stripped. Replaces reading the KB files and
    --rules separately (they overlap). Like a tool search with detail levels: rules in the loaded domains
    print in full; core/style rules print as a headline index (full text via --rule ids). --full prints
    every rule in full (the reviewer, whose context is discarded after the review)."""
    cwd = os.path.abspath(flag_value("--cwd") or os.getcwd())
    full = "--full" in sys.argv
    wanted = [d.removesuffix(".md") for d in re.split(r"[,\s]+", " ".join(flag_values("--domains"))) if d]
    available = sorted(p.stem for p in (DATA / "domains").glob("*.md"))
    # the reviewer (--full) loads every domain: the builder's pick is a hint, not a blind spot it inherits
    load = available if full else [d for d in wanted if d in available]
    files = [DATA / "core.md", DATA / "style.md"] + [DATA / "domains" / f"{d}.md" for d in load]
    rules = {(r["file"], r["line"]): r for r in parse_rules()}
    out, skipped = [], 0
    for f in files:
        if not f.exists():
            continue
        rel = str(f.relative_to(DATA))
        out.append(f"## {rel}")
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            r = rules.get((rel, n))
            if r:
                if r["scope"] and not in_scope(r["scope"], cwd):
                    skipped += 1
                else:
                    short = not full and not rel.startswith("domains/")
                    out.append(f"- [{r['id']}] {headline(r['rule']) if short else r['rule']}")
            elif line.strip():
                line = re.sub(r"^(\s*[-*]\s*)\[[ x~]\]\s*", r"\1", line)
                line = re.sub(r"\s*_\([^)]*\)_\s*$", "", line)  # trailing provenance note
                out.append("#" + line if line.startswith("#") else line)  # nest under the file header
    print(f"# lifecycle-guard checklists for `{project_name(cwd)}` — learned rules are mandatory, cite [id]s;"
          f" {skipped} rule(s) scoped to other projects omitted")
    if not full:
        print("rules ending in … are headlines: read the full text of every one that touches this feature "
              "with `digest.py --rule <id>,<id>` before writing the spec")
    print(f"domains available: {', '.join(available) or '(none)'}; loaded: {', '.join(load) or '(none)'}"
          + (f" (builder named: {', '.join(wanted) or 'none'})" if full else ""))
    for d in wanted:
        if d not in available:
            print(f"no domain file: {d} (create domains/{d}.md if the feature needs one)")
    print("\n".join(out))


def rule_lookup():
    """Full text of the rules whose ids are given (comma or space separated)."""
    ids = set(re.findall(r"\b[0-9a-f]{8}\b", " ".join(sys.argv[2:])))
    if not ids:
        print("usage: digest.py --rule <8-char id>[,<id>…]  (ids come from --context)")
        return
    found = [r for r in parse_rules() if r["id"] in ids or ids & set(r["was"])]
    for r in found:
        scope = f" [scope: {r['scope']}]" if r["scope"] else ""
        old = sorted(ids & set(r["was"]))
        was = f" (was {', '.join(old)})" if old else ""
        print(f"- [{r['id']}]{was} ({r['file']}){scope} {r['rule']}")
    for i in sorted(ids - ids_of(found)):
        print(f"no rule with id {i} (reworded rules get a new id: rerun --context)")


CAUSE_MAX = 80


def rule_max():
    try:
        return int(cfg().get("rule_max_chars", 250))
    except (TypeError, ValueError):
        return 250


def lint_rules():
    """Write-time budget check for /learn and the correction hook: rules over rule_max_chars and
    knowledge files over kb_budget_kb. Advisory output, exit 0."""
    limit = rule_max()
    rules = parse_rules()
    long_rules = [r for r in rules if len(r["rule"]) > limit]
    long_causes = [r for r in rules if len(r["cause"]) > CAUSE_MAX]
    budget, sizes = kb_sizes()
    for r in long_rules:
        print(f"too-long {r['id']} {r['file']}:{r['line']} {len(r['rule'])}/{limit} chars — "
              f"{headline(r['rule'])}")
    for r in long_causes:  # provenance only, but it's most of a file's bytes when it rambles
        print(f"long-cause {r['id']} {r['file']}:{r['line']} {len(r['cause'])}/{CAUSE_MAX} chars — "
              f"keep the cause under 10 words")
    for name, kb in sizes:
        if kb > budget:
            print(f"over-budget {name} {kb} KB > {budget:g} KB — merge overlapping rules")
    if not long_rules and not long_causes and all(kb <= budget for _, kb in sizes):
        print(f"ok: every rule ≤ {limit} chars, every file ≤ {budget:g} KB")


LOCK_STALE = 2 * 3600  # a .learn.lock older than this is left over from a crashed run


def learn_locked(now=None):
    """True while a background /learn may be editing the KB files."""
    lock = DATA / ".learn.lock"
    try:
        return (now or time.time()) - lock.stat().st_mtime < LOCK_STALE
    except OSError:
        return False


def over_budget_now():
    budget, sizes = kb_sizes()
    return [n for n, kb in sizes if kb > budget]


def maintain(now=None):
    """Automatic KB upkeep, no model call (SessionEnd runs it every session):
    - trims `cause` stamps over CAUSE_MAX at a word boundary (provenance only: ids and rules unchanged),
      backing the file up and logging each original to changelog.md — skipped while a background /learn
      holds the lock, so it never overwrites that run's edits;
    - records what only a model or a person can fix: rules over rule_max_chars (the hook then starts a
      background reword) and files over kb_budget_kb (the prompt hook reminds the user to /audit)."""
    now = now or time.time()
    trimmed = []
    for f in ([] if learn_locked(now) else kb_files()):
        rel = str(f.relative_to(DATA))
        with open(f, encoding="utf-8", newline="") as fh:  # keep the user's line endings
            original = fh.read()
        lines = original.split("\n")
        for n, line in enumerate(lines):
            for m in reversed(list(LEARNED.finditer(line))):  # every stamp; right to left keeps offsets
                c = m.group(3) or ""
                if len(c) > CAUSE_MAX and "_(" not in c and ")_" not in c:  # else it ran into another stamp
                    short = m.group(3)[:CAUSE_MAX - 2].rsplit(" ", 1)[0].rstrip(",;:—- ") + " …"
                    line = line[:m.start(3)] + short + line[m.end(3):]
                    trimmed.append((rel, m.group(3), short))
            lines[n] = line
        updated = "\n".join(lines)
        if updated != original and not same_ids(original, updated, rel):
            trimmed = [t for t in trimmed if t[0] != rel]  # never change a rule's id unattended
            continue
        if updated != original:
            (DATA / "backups").mkdir(exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M", time.localtime(now))
            with open(DATA / "backups" / f"{f.name}.{stamp}-maintain.bak", "w", encoding="utf-8", newline="") as fh:
                fh.write(original)
            write_atomic(f, updated, newline="")
    if trimmed:
        with open(DATA / "changelog.md", "a", encoding="utf-8") as fh:
            fh.write(f"\n## {time.strftime('%Y-%m-%d', time.localtime(now))} maintain (causes trimmed to "
                     f"{CAUSE_MAX} chars; rules unchanged)\n")
            for rel, old, short in trimmed:
                fh.write(f"- cause {rel}: {short}\n    was: {old}\n")
    limit = rule_max()
    too_long = sorted(r["id"] for r in parse_rules() if len(r["rule"]) > limit)
    over = over_budget_now()
    update_cfg(kb_too_long=too_long, kb_over_budget=over)
    return {"causes_trimmed": len(trimmed), "too_long": too_long, "over_budget": over}


def ids_of(rules):
    return {i for r in rules for i in [r["id"], *r["was"]]}


def same_ids(before, after, rel):
    return ids_of(parse_lines(before.split("\n"), rel)) == ids_of(parse_lines(after.split("\n"), rel))


def known_ids():
    """Every id a rule answers to: its current id and the ids in its `was` stamps."""
    return ids_of(parse_rules())


def verify_ids():
    """Guard for unattended edits: every id listed in FILE (a --ids snapshot) must still exist, as a rule
    or in a `was` stamp. Exit 1 and name the missing ones otherwise (the caller restores its backup)."""
    path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if not path or not path.exists():
        print("usage: digest.py --verify-ids <snapshot from --ids>")
        sys.exit(2)
    missing = sorted(set(re.findall(r"\b[0-9a-f]{8}\b", path.read_text())) - known_ids())
    if missing:
        print("missing: " + " ".join(missing) + " — a rule was dropped or reworded without `_(was <id>)_`")
        sys.exit(1)
    print("ok: every rule id is still present")


def footprint():
    """What a feature costs in context with this knowledge base (builder vs reviewer load)."""
    def run(*extra):
        saved = sys.argv
        sys.argv = [saved[0], "--context", *extra]
        try:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                context()
            return len(buf.getvalue().encode("utf-8"))
        finally:
            sys.argv = saved
    domains = sorted(p.stem for p in (DATA / "domains").glob("*.md"))
    rules = parse_rules()
    builder, everything, reviewer = run(), run("--domains", ",".join(domains)), run("--full", "--domains", ",".join(domains))
    print(f"context per feature: builder {builder / 1024:.1f} KB (core + style)"
          f" to {everything / 1024:.1f} KB (all {len(domains)} domains); reviewer up to {reviewer / 1024:.1f} KB")
    print(f"learned rules: {len(rules)}, {sum(len(r['rule']) for r in rules) / 1024:.1f} KB of text; "
          f"{sum(len(r['rule']) > rule_max() for r in rules)} over {rule_max()} chars")
    for r in sorted(rules, key=lambda r: -len(r["rule"]))[:3]:
        print(f"  longest: {r['id']} {len(r['rule'])} chars — {headline(r['rule'])}")


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
    max_len = rule_max()
    tokens = {id(r): rule_tokens(r["rule"]) for r in rules}
    for r in rules:
        r["similar_to"] = [o["id"] for o in rules if o is not r
                           and similarity(tokens[id(r)], tokens[id(o)]) >= threshold]
        r["exact_duplicate"] = any(o is not r and o["id"] == r["id"] for o in rules)
    for r in rules:
        r.update(merged_usage(usage, [r["id"], *r["was"]]))
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
        if len(r["rule"]) > max_len:
            flags.append("too-long")
        r["flags"] = flags
    return rules, limit


def kb_budget():
    try:
        return float(cfg().get("kb_budget_kb", 12))
    except (TypeError, ValueError):
        return 12.0  # a hand-edited "12 KB" must not break the hooks


def kb_sizes():
    budget = kb_budget()
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
          f"possible-duplicate: {counts['possible-duplicate']} · too-long: {counts['too-long']} · scoped: {scoped}")
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



# --- unattended learning: the model proposes, this code applies -------------------------------------
# Claude Code refuses an unattended session's writes under ~/.claude, so `/learn auto` runs read-only and
# ends with a JSON proposal; the SessionEnd wrapper (a plain shell, not a Claude tool) hands it here.
# Only three operations exist — add, reword, cause — so a drop or merge can't happen unattended.
KB_TARGET = re.compile(r"^(core\.md|style\.md|domains/[a-z0-9][a-z0-9-]*\.md)$")


def _log_error(msg):
    try:
        with open(DATA / "hook-errors.log", "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M')} {msg}\n")
    except OSError:
        pass


def _extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the proposal")
    return json.loads(text[start:end + 1])


def _insert_learned(lines, new_lines):
    """Append bullets at the end of the first ## Learned section (create one at the end if missing)."""
    head = next((i for i, l in enumerate(lines) if l.startswith("#")
                 and l.lstrip("#").strip().lower().startswith("learned")), None)
    if head is None:
        while lines and not lines[-1].strip():
            lines.pop()
        return lines + ["", "## Learned"] + new_lines + [""]
    end = head + 1
    while end < len(lines) and not lines[end].startswith("#"):
        end += 1
    while end > head + 1 and not lines[end - 1].strip():
        end -= 1
    return lines[:end] + new_lines + lines[end:]


def apply_proposal(path):
    """Apply a learn proposal {add:[{file,rule,project,cause,scope?}], reword:[{id,rule}], cause:[{id,cause}]}.
    All or nothing: validated, backed up, every rule id still present afterwards (else nothing is written),
    originals logged verbatim, then the digest is marked as learned — unless a proposed lesson had to be
    skipped, so it isn't lost: the run then counts as failed and the material stays pending. Exit code."""
    try:
        return _apply_proposal(path)
    except Exception as e:  # never a traceback into learn.log: refuse cleanly and say why
        _log_error(f"learn proposal not applied: {e!r}")
        print(f"not applied: {e!r}")
        return 1


def _ops(prop, key):
    ops = prop.get(key)
    return [op for op in (ops if isinstance(ops, list) else []) if isinstance(op, dict)]


def _stamp_free(text):
    return "_(" not in text and ")_" not in text  # no forged _(was …)_ / _(learned …)_ inside a field


def _apply_proposal(path):
    try:
        prop = _extract_json(Path(path).read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        _log_error(f"learn proposal not applied: {e!r}")
        print(f"not applied: {e}")
        return 1
    if not isinstance(prop, dict):
        _log_error("learn proposal not applied: not a JSON object")
        return 1
    limit, today = rule_max(), time.strftime("%Y-%m-%d")
    rules = {r["id"]: r for r in parse_rules()}
    before = ids_of(rules.values())
    texts, log, skipped = {}, [], []

    def lines_of(rel):
        if rel not in texts:
            f = DATA / rel
            texts[rel] = f.read_text(encoding="utf-8").split("\n") if f.exists() else \
                [f"# {Path(rel).stem.replace('-', ' ').title()}", "", "> seeded by Claude — unverified", ""]
        return texts[rel]

    def clean(t):
        return re.sub(r"\s+", " ", str(t or "")).strip()

    for op in _ops(prop, "reword"):
        r, text = rules.get(str(op.get("id"))), clean(op.get("rule"))
        if not r or not text or len(text) > limit or not _stamp_free(text):
            skipped.append(f"reword {op.get('id')}: unknown id, empty, over {limit} chars or has a stamp")
            continue
        lines = lines_of(r["file"])
        old = lines[r["line"] - 1]
        stamps = " ".join(m.group(0) for m in LEARNED.finditer(old))
        reviewed = " ".join(m.group(0) for m in REVIEWED.finditer(old))
        scope = f"[scope: {r['scope']}] " if r["scope"] else ""
        head = re.match(r"^(\s*[-*]\s*(?:\[[ x~]\]\s*)?)", old).group(1)  # keeps indent + checkbox state
        lines[r["line"] - 1] = " ".join(x for x in (f"{head}{scope}{text}", stamps,
                                                    f"_(was {', '.join([*r['was'], r['id']])})_", reviewed) if x)
        log.append(f"- reword {r['file']}: {text[:80]}\n    was: {old}")
    for op in _ops(prop, "cause"):
        r, cause = rules.get(str(op.get("id"))), clean(op.get("cause"))[:CAUSE_MAX]
        if not r or not cause or not _stamp_free(cause):
            skipped.append(f"cause {op.get('id')}: unknown id or bad text")
            continue
        lines = lines_of(r["file"])
        old = lines[r["line"] - 1]
        m = LEARNED.search(old)
        if not m or m.group(3) is None:
            skipped.append(f"cause {op.get('id')}: no readable stamp")
            continue
        lines[r["line"] - 1] = old[:m.start(3)] + cause + old[m.end(3):]
        log.append(f"- cause {r['file']}: {r['id']} — {cause}\n    was: {m.group(3)}")
    known = {r["rule"].lower() for r in rules.values()}
    adds = {}
    lost_lessons = 0
    for op in _ops(prop, "add"):
        rel, text = str(op.get("file") or ""), clean(op.get("rule"))
        project = re.sub(r"[^\w.-]", "", str(op.get("project") or "?")) or "?"
        cause = clean(op.get("cause"))[:CAUSE_MAX]
        scope = re.sub(r"[\[\]]", "", clean(op.get("scope")))
        if text.lower() in known:
            skipped.append(f"add {rel}: already a rule")  # nothing lost
            continue
        if (not KB_TARGET.match(rel) or not text or len(text) > limit or not _stamp_free(text)
                or not _stamp_free(cause) or not _stamp_free(scope)):
            skipped.append(f"add {rel}: bad file, empty, over {limit} chars, or stamp-like text — {text[:80]}")
            lost_lessons += 1
            continue
        known.add(text.lower())
        line = f"- [ ] {f'[scope: {scope}] ' if scope else ''}{text} _(learned {today} @ {project}: {cause or 'learned'})_"
        adds.setdefault(rel, []).append(line)
        log.append(f"- add {rel}: {text[:80]}")
    for rel, new_lines in adds.items():
        texts[rel] = _insert_learned(lines_of(rel), new_lines)
    after = set()
    for rel in {r["file"] for r in rules.values()} | set(texts):
        after |= ids_of(parse_lines(texts[rel] if rel in texts else
                                    (DATA / rel).read_text(encoding="utf-8").split("\n"), rel))
    lost = before - after
    if lost:  # never lose a lesson unattended: write nothing
        _log_error(f"learn proposal not applied: it would lose rule ids {sorted(lost)}")
        print(f"not applied: would lose {sorted(lost)}")
        return 1
    stamp = time.strftime("%Y%m%d-%H%M")
    (DATA / "backups").mkdir(exist_ok=True)
    for rel, lines in texts.items():
        f = DATA / rel
        if f.exists():
            shutil.copy2(f, DATA / "backups" / f"{f.name}.{stamp}-learn.bak")
        f.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(f, "\n".join(lines))
    with open(DATA / "changelog.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## {today} learn (auto, applied by digest.py)\n" + "\n".join(log or ["- nothing to change"]) + "\n")
        for s in skipped:
            fh.write(f"- skipped {s}\n")
    if skipped:
        _log_error("learn proposal: skipped " + "; ".join(skipped))
    if lost_lessons:  # a lesson couldn't be stored: keep its material pending, count the run as failed
        print(json.dumps({"applied": len(log), "skipped": skipped, "marked": False}))
        return 1
    update_cfg(learn_failures=0)  # the background run worked: no backoff
    mark()
    print(json.dumps({"applied": len(log), "skipped": skipped, "marked": True}))
    return 0

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--lint-spec":
        lint_spec(sys.argv[2:])
        sys.exit(0)
    if arg == "--ids":
        print("\n".join(sorted(known_ids())))
        sys.exit(0)
    if arg == "--verify-ids":
        verify_ids()
        sys.exit(0)
    if arg == "--maintain":
        print(json.dumps(maintain()))
        sys.exit(0)
    if arg == "--prune-logs":
        print(json.dumps(prune_logs()))
        sys.exit(0)
    if arg == "--ingest-usage":  # used by the Stop hook; also handy by hand
        print(ingest_usage(sys.argv[2] if len(sys.argv) > 2 else "."))
        sys.exit(0)
    if arg == "--apply-proposal":
        sys.exit(apply_proposal(sys.argv[2] if len(sys.argv) > 2 else ""))
    if arg == "--version":
        print(VERSION)
        sys.exit(0)
    commands = {"--bootstrap": bootstrap, "--mark": mark, "--stats": stats,
                "--audit": audit, "--rules": rules_list, "--usage": usage_summary,
                "--project": project_info, "--context": context, "--rule": rule_lookup,
                "--lint-rules": lint_rules, "--footprint": footprint}
    if arg.startswith("--") and arg not in commands:
        # never fall through to the prompt digest: an agent asking a stale copy for --context must notice
        print(f"digest.py {VERSION}: unknown flag {arg} — a stale copy? Use the plugin's scripts/digest.py",
              file=sys.stderr)
        sys.exit(2)
    commands.get(arg, since_last)()
