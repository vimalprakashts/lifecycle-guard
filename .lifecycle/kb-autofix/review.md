# Review — kb-autofix
VERDICT: PASS
Reviewed: 2026-10-31 · rounds: 2 (round 1 FAIL with 2 high → fixed; round 2 scoped to the fixes: PASS)
## Findings addressed
- [high] maintain() could overwrite a background /learn's edits → no file writes while .learn.lock (< 2h) is held; temp file + os.replace
- [high] corrupt config.json wiped settings → update_cfg/update_config merge only their keys into the file's current content, refuse an unparseable file; atomic saves; --mark too
- [medium] leaked/stale lock blocked learning forever → stale after 2h; failed spawn unlinks it
- [medium] unbounded paid runs → same too-long set retries weekly, a changed set daily
- [medium] unattended drop/merge possible → --ids snapshot + --verify-ids (exit 1) in learn.md; supersede/merge/sharpen carry `_(was id)_`
- [medium] over-budget-only compaction run → learn stops unless too-long / long-cause
- [medium] (round 2) corrupt config → throttles unrecordable → a run every session → no background run while config.json is unreadable; tested
- [low] every stamp trimmed; CRLF kept; reminder re-checks the size before nudging
## Known gaps (deferred)
- Tiny race between maintain's lock check and its write (a learn starting in between) — bounded to one lost trim, never a corrupt file; next session redoes it.
- Paid behavioural evals — after the weekly limit resets.
## Rules applied
- 9b09bd45 satisfied
