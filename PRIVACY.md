# Privacy

lifecycle-guard is a local plugin. It has no server, no telemetry and no account. Everything it stores
lives in `~/.claude/lifecycle-guard/` on your machine (or `$LG_DATA_DIR` if you set it).

## What it stores

| File | Contents | Kept |
|---|---|---|
| `prompts.jsonl` | Prompts you type, with the working directory and session id | `log_retention_days` (default 180), but never pruned before `/learn` has used them |
| `corrections.jsonl` | The subset of prompts that look like corrections ("you missed…") | Same as above |
| `usage.jsonl` | Which learned rules each review applied (rule id, `caught`/`satisfied`, project folder name, feature slug) | Until you delete it |
| `core.md`, `style.md`, `domains/*.md` | Your checklists and learned rules, as plain text you can read and edit | Until you edit or delete them |
| `changelog.md`, `backups/` | Every change `/learn` and `/audit` made, and the file versions before each change | Until you delete them |
| `bootstrap/` | Only if you run `/lifecycle-guard:bootstrap`: excerpts of your past Claude Code prompts | Until you delete it |

What is **not** stored: pasted content (`<pasted_content>` blocks), system-injected messages (task
notifications, reminders, command output) and image placeholders are stripped before anything is
logged. Inside rules and usage records, projects are labelled by folder name only; the prompt logs
keep the full working-directory path of each prompt (that's how origins are traced), and usage records
keep a hash of the project path to avoid counting a review twice.

## What leaves your machine

- **The plugin itself sends nothing anywhere.** The hooks only read and write local files.
- **Claude Code sessions** work as they always do: when the skill or the reviewer reads your knowledge
  base, that text becomes part of the conversation sent to Anthropic, like any file Claude reads.
- **Background learning** (`auto_learn`, on by default) starts a headless `claude -p
  /lifecycle-guard:learn auto` run at session end once enough prompts have piled up. That run sends the
  new prompts and corrections to Anthropic to distill them into rules. Turn it off with
  `"auto_learn": false` in `config.json` and run `/lifecycle-guard:learn` by hand when you choose.

The `/learn` step is instructed never to write secrets, credentials, customer names or personal data
into the checklists. Review what it learned any time with `/lifecycle-guard:audit`.

## Deleting your data

- Everything: `rm -rf ~/.claude/lifecycle-guard` (uninstalling the plugin leaves this folder in place).
- Just the prompt logs: delete `prompts.jsonl` and `corrections.jsonl`; learned rules are unaffected.
- Keep logs forever instead: set `"log_retention_days": 0`.
