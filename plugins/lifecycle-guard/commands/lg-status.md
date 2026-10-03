---
description: Show what lifecycle-guard has learned and what's pending
---

Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --stats`, `python3 ~/.claude/lifecycle-guard/bin/digest.py --usage` and `python3 ~/.claude/lifecycle-guard/bin/digest.py --audit | head -3`, read the last 30 lines of `~/.claude/lifecycle-guard/changelog.md`, and check `.lifecycle/*/tasks.md` in the current project.

Report briefly: last learn time, pending prompts and corrections, domain files with their Learned-rule counts, rule usage (from `--usage`: how many rules have caught a miss, how many were never applied in a review, and the top rules by catches), rules needing review (no-origin / stale / looks-project-specific / scoped counts — suggest `/lifecycle-guard:audit` if any are flagged), recent changelog entries, and any active feature with its open task count.
