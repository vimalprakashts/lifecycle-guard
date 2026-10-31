# Spec — v1.12.0 hardening: fixes from the five-lens review + debate (22 confirmed + 2 critic)

## Goal
Close every confirmed finding before release. The biggest: background `/learn auto` can't write under
~/.claude (Claude Code protects it) — auto-learn has never applied anything, and v1.12's automatic reword
depends on it. Redesign: the model PROPOSES (JSON on stdout), deterministic Python APPLIES.

## Actors
Background learner (headless claude -p, read-only), the SessionEnd wrapper shell + digest.py
(applies), builder agent, reviewer agent (all three dispatch paths), interactive /learn and /audit users,
older plugin versions running in parallel sessions, CI (Linux 3.9/3.13), release workflow.

## Behaviour (by finding)
- C0 learn auto: allowedTools read-only (Read, Glob, Grep, Bash(python3:*) for digest reads); the run's
  final message is a JSON proposal {add:[{file,rule,project,cause,scope?}], reword:[{id,rule}],
  cause:[{id,cause}]}; the wrapper saves stdout to .learn-proposal and runs `lg-digest.py
  --apply-proposal`: validates (file inside KB, rule ≤ rule_max_chars, ids exist, no drop/merge op
  exists), backs up, appends/rewords with `_(was id)_`, logs originals verbatim, verifies no id lost
  (rolls back otherwise), atomic writes, then marks the digest cursor. Bad JSON → nothing applied,
  logged to hook-errors.log.
- C1 + backoff: SessionEnd in automated sessions (sdk-*) does upkeep only, never spawns. Any spawn
  records last_learn_attempt_ts; an `enough`-triggered spawn waits 24 h after an attempt that didn't
  advance last_learn_ts (longer — 7 d — after 3 such attempts).
- #0/#18 seed core.md learned rules ≤ 250 chars, causes ≤ 80; a freshly seeded KB lints `ok` and its
  first SessionEnd starts no run (test).
- #1/#11 maintain never trims a cause containing `_(` or `)_`; per file, ids before == ids after or the
  file isn't written; parse_rules flags such a cause `malformed`.
- #2 atomic writes resolve symlinks (write next to the real file) and keep the file mode.
- #4 kb_budget_kb non-numeric → 12; the reminder block can't suppress other notes.
- #5 reviewer `--full` loads EVERY domain (the builder's choice is a hint); prompts say so.
- #6 round 2 when round 1 is FAIL or any code changed for a finding; fix every finding that opens a hard
  gate; review.md VERDICT = the critic's last verdict verbatim; still FAIL after round 2 → `review:
  deferred — <reason>` with the open gaps listed.
- #7 strengthening a rule in-session appends `_(was <old id>)_` (SKILL + hook note).
- #8/#10 `--domains a, b` / `a b` / `a,b` all load every named domain.
- #9 learn changelog logs every reworded original verbatim (code does it for auto).
- #12 `--rule` resolves former ids. #13 relative `--cwd` resolved.
- #14/#15 /tmp is never a temp root (Linux CI + users); tests independent of TMPDIR; run the suite in a
  Linux python:3.9 container.
- #16 scripts copy to bin/lg-digest.py (old versions only write bin/digest.py), never downgraded
  (VERSION compare); unknown flags exit 2 instead of dumping prompts; SKILL/reviewer: no `[id]` rules
  or `# Digest since` output = stale copy → use the plugin's own script.
- #17 release notes body = the CHANGELOG section for the tag.
- #19 Stop reason: items cut to 120 chars, ≤ 5 items per feature when > 3 features; every feature path
  always shown; capped in test_budget.
- #20 digest output capped (digest_max_chars 20000), corrections first, oldest first; `--mark` advances
  only to the last record shown.
- #21 hook notes show `~` for the home dir; reminder lists ≤ 3 files; correction + reminder together
  ≤ 700 B or the reminder waits for the next prompt.
- #3 interactive /learn: backup + id snapshot before any edit.

## Acceptance criteria
One regression test per finding (named in tasks.md); full suite green on macOS and in a Linux
python:3.9 container with TMPDIR unset; budget tests still pass.

## Out of scope
Rewriting unpushed history; paid evals (after the limit resets).
