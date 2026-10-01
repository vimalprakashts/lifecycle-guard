---
description: One-time scan of all past Claude Code sessions to seed checklists and style
---

Seed the lifecycle-guard knowledge base from the user's entire Claude Code history, so nothing has to be written by hand.

1. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --bootstrap`.
2. Process each `~/.claude/lifecycle-guard/bootstrap/part-NN.md` in order. For each part, apply steps 2–7 of the `/lifecycle-guard:learn` procedure (read the knowledge files, extract missed-scope lessons into domain/core `## Learned`, extract style into `style.md`, dedupe, back up, log to changelog). Re-read the knowledge files between parts so later parts dedupe against earlier ones.
3. Be stricter than usual on style: with this much history, only record patterns seen in 3+ prompts across at least 2 projects, plus explicit "always/never/prefer" instructions.
4. Run `python3 ~/.claude/lifecycle-guard/bin/digest.py --mark`.
5. Summarize: projects scanned, domain files created, rules per file, top 10 style rules found.
