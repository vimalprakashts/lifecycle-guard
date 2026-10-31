# Review — v112-hardening
VERDICT: PASS
Reviewed: 2026-10-31 · rounds: 2 (round 1 FAIL: 2 high, 4 medium, 3 low → fixed; round 2 scoped: PASS)
Source: a 52-agent workflow review (5 lenses → defender/judge debate per finding → completeness critic):
22 confirmed + 2 critic findings, all fixed with one regression test each (all fail on the old code).
## Findings addressed
- [high] C0 background /learn auto could never write under ~/.claude → read-only run returns a JSON proposal; lg-digest.py --apply-proposal applies it (validated, path allowlist, stamp-free text, all-or-nothing id check, backups, verbatim log, atomic)
- [high] #5 reviewer inherited the builder's domain pick → --full loads every domain
- [high] #6 FAIL could become a builder-written PASS → round 2 after any FAIL or fix; review.md carries the critic's last verdict verbatim; still FAIL → deferred with gaps
- [high] #15 Linux CI / /tmp → /tmp never a temp root; tests independent of TMPDIR
- [high] (round 1) forged `_(was …)_` via proposal text → `_stamp_free` on every field
- [high] (round 1) wrong JSON shapes crashed → clean refusal, logged
- [medium] C1 automated sessions / failed runs spawned paid runs → upkeep only in sdk-*; failure backoff 1 d / 7 d
- [medium] #0/#18 seed rules too long (fresh install started a run) → shortened; fresh-install test
- [medium] #1/#11 maintain could erase a was stamp → skip mis-closed stamps; per-file id equality or no write; malformed flag
- [medium] #2 symlinks/modes → write next to the real file, copymode
- [medium] #4 bad kb_budget_kb silenced notes → guarded parse; reminder isolated
- [medium] #7 in-session strengthen lost history → was stamp in SKILL + hook note
- [medium] #10/#8 `--domains a, b` → all tokens parsed
- [medium] #14 /tmp legacy records → as #15
- [medium] #16 stale bin copy from older sessions → bin/lg-digest.py, VERSION no-downgrade, atomic copy, unknown flags exit 2
- [medium] #20 unbounded digest → digest_max_chars + cursor-honest --mark
- [medium] (round 1) all-skipped proposal still marked → invalid lesson = run failed, material pending
- [medium] (round 1) compaction lacked rule text → `D --rule` in learn step 6
- [medium] (round 1) Bash(python3:*) not read-only → narrowed to the digest script
- [medium] (round 1) non-atomic script copy → temp + os.replace
- [low] #3/#9 learn snapshot before edits + verbatim originals; #12 --rule former ids; #13 relative --cwd; #17 release notes from CHANGELOG; #19 bounded Stop reason; #21 ~ paths, notes never stack; line splitter unified; checkbox kept on reword; leftover bare digest.py names
## Known gaps (deferred)
- Live `claude -p` allow-rule matching not exercised (strings verified identical) — confirmed on the first real background run after release.
- Linux container run blocked: the Colima VM has no route to Docker Hub; GitHub CI runs Linux 3.9/3.13 on push.
- A rule line with a form feed / U+2028 / U+0085 gets a new id once (now parsed like LF) — vanishingly rare.
- Paid behavioural evals — after the weekly limit resets.
## Rules applied
