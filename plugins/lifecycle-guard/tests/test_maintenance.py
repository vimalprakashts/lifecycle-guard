#!/usr/bin/env python3
"""v1.8.0 hardening: project identity + nested scopes, log retention, duplicate/size audit.

Run: python3 plugins/lifecycle-guard/tests/test_maintenance.py  (temp HOME + LG_DATA_DIR)
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODAY = time.strftime("%Y-%m-%d")
DAY = 86400


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.data = base / "kb"
        (self.data / "domains").mkdir(parents=True)
        # home/work/umbrella/{repo/.git, repo/apps/ui, other/.git}; umbrella itself is not a repo
        self.umbrella = self.home / "work" / "umbrella"
        self.repo = self.umbrella / "repo"
        self.ui = self.repo / "apps" / "ui"
        self.ui.mkdir(parents=True)
        (self.repo / ".git").mkdir()
        (self.umbrella / "other").mkdir()
        (self.umbrella / "other" / ".git").write_text("gitdir: /somewhere/else\n")  # worktree-style
        self.env = {**os.environ, "HOME": str(self.home), "LG_DATA_DIR": str(self.data),
                    "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), *map(str, args)],
                              capture_output=True, text=True, env=self.env, check=True).stdout

    def config(self, **kw):
        (self.data / "config.json").write_text(json.dumps(kw))


class ProjectIdentity(Base):
    def test_label_is_the_git_root_not_the_subfolder(self):
        out = self.digest("--project", self.ui)
        self.assertIn("project: repo", out)
        self.assertIn("scope matches: repo, ui, apps, umbrella, work", out)
        self.assertNotIn("home", out.split("scope matches:")[1])  # stops below $HOME

    def test_git_file_worktree_and_non_repo_folders(self):
        self.assertIn("project: other", self.digest("--project", self.umbrella / "other"))
        self.assertIn("project: umbrella", self.digest("--project", self.umbrella))
        self.assertIn("project: gone", self.digest("--project", self.home / "nowhere" / "gone"))

    def test_hook_stamps_the_repo_name_from_a_subfolder(self):
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_prompt.py")],
                           input=json.dumps({"prompt": "you missed the admin view", "cwd": str(self.ui)}),
                           capture_output=True, text=True, env=self.env)
        self.assertIn("@ repo:", json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_umbrella_scope_covers_nested_repos_and_others_are_na(self):
        (self.data / "core.md").write_text(
            "## Learned\n"
            f"- [ ] [scope: umbrella] Test on the staging tenant _(learned {TODAY} @ umbrella: x)_\n"
            f"- [ ] [scope: Repo] Repo-only rule _(learned {TODAY} @ repo: x)_\n"
            f"- [ ] [scope: elsewhere] Someone else's rule _(learned {TODAY} @ elsewhere: x)_\n"
            f"- [ ] Global rule _(learned {TODAY} @ repo: x)_\n")
        out = self.digest("--rules", "--cwd", self.ui)
        line = {l.split("  ", 2)[-1]: l for l in out.splitlines()[1:]}
        self.assertIn("[scope: umbrella]", line["Test on the staging tenant"])
        self.assertIn("[scope: Repo]", line["Repo-only rule"])  # case-insensitive
        self.assertIn("N/A here (scope: elsewhere)", line["Someone else's rule"])
        self.assertNotIn("scope", line["Global rule"])
        self.assertIn("project `repo`", out.splitlines()[0])
        other = self.digest("--rules", "--cwd", self.umbrella / "other")
        self.assertIn("N/A here (scope: Repo)", other)
        self.assertIn("[scope: umbrella]", other)


class Retention(Base):
    def write_logs(self, *ages_days):
        now = time.time()
        for name in ("prompts.jsonl", "corrections.jsonl"):
            lines = [json.dumps({"prompt": f"p{a}", "ts": now - a * DAY}) for a in ages_days] + [
                "{corrupt", json.dumps({"prompt": "no-ts"})]
            (self.data / name).write_text("\n".join(lines) + "\n")

    def kept(self, name="prompts.jsonl"):
        return [l for l in (self.data / name).read_text().splitlines()]

    def test_old_learned_records_pruned_unlearned_kept(self):
        self.write_logs(400, 200, 10)
        self.config(log_retention_days=180, last_learn_ts=time.time() - 300 * DAY)
        removed = json.loads(self.digest("--prune-logs"))
        self.assertEqual(removed, {"prompts.jsonl": 1, "corrections.jsonl": 1})  # only the 400-day one
        kept = self.kept()
        self.assertFalse(any('"p400"' in l for l in kept))
        self.assertTrue(any('"p200"' in l for l in kept))  # old, but not yet learned
        self.assertIn("{corrupt", kept)  # never destroy what can't be parsed
        self.assertTrue(any("no-ts" in l for l in kept))  # no usable timestamp → keep

    def test_never_learned_means_nothing_pruned_and_zero_disables(self):
        self.write_logs(400)
        self.config(log_retention_days=180)  # last_learn_ts missing → 0
        self.assertEqual(json.loads(self.digest("--prune-logs")), {"prompts.jsonl": 0, "corrections.jsonl": 0})
        self.config(log_retention_days=0, last_learn_ts=time.time())
        self.assertEqual(json.loads(self.digest("--prune-logs")), {})
        self.assertEqual(len(self.kept()), 3)

    def test_session_end_prunes(self):
        self.write_logs(400, 1)
        self.config(log_retention_days=30, last_learn_ts=time.time(), auto_learn=False)
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_session_end.py")],
                           input="{}", capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any('"p400"' in l for l in self.kept()))
        self.assertTrue(any('"p1"' in l for l in self.kept()))


class DuplicatesAndSize(Base):
    def audit(self):
        return json.loads(self.digest("--audit", "--json"))

    def test_near_and_exact_duplicates_flagged_unrelated_not(self):
        (self.data / "core.md").write_text(
            "## Learned\n"
            f"- [ ] Same validation and limits across every entry point for an action (bulk vs single, API vs UI) _(learned {TODAY} @ a: x)_\n"
            f"- [ ] Apply identical validation limits on every entry point: bulk and single, API and UI _(learned {TODAY} @ a: y)_\n"
            f"- [ ] Charts are interactive with hover tooltips _(learned {TODAY} @ a: z)_\n"
            f"- [ ] Charts are interactive with hover tooltips _(learned {TODAY} @ b: z)_\n"
            f"- [ ] Webhooks retry with exponential backoff _(learned {TODAY} @ a: w)_\n")
        rules = self.audit()["rules"]
        same = [r for r in rules if r["rule"].startswith(("Same", "Apply"))]
        self.assertEqual({tuple(r["similar_to"]) for r in same}, {(same[1]["id"],), (same[0]["id"],)})
        charts = [r for r in rules if r["rule"].startswith("Charts")]
        self.assertTrue(all("possible-duplicate" in r["flags"] for r in charts))  # identical text, same id
        webhook = [r for r in rules if r["rule"].startswith("Webhooks")][0]
        self.assertEqual(webhook["similar_to"], [])
        self.assertNotIn("possible-duplicate", webhook["flags"])

    def test_size_budget_warning(self):
        (self.data / "core.md").write_text("## Learned\n" + "x" * 3000 + "\n")
        self.config(kb_budget_kb=2)
        header = self.digest("--audit")
        self.assertIn("No learned rules", header)  # no rules: plain message, nothing else to warn about
        (self.data / "core.md").write_text("## Learned\n" + f"- [ ] rule _(learned {TODAY} @ a: x)_\n" + "x" * 3000)
        out = self.digest("--audit")
        self.assertIn("size: core.md 3.", out)
        self.assertIn("over the 2 KB budget", out)
        self.assertTrue(self.audit()["kb_files"][0]["over_budget"])
        status_header = out.split("\n\n")[0]  # what /lg-status reads (up to the first blank line)
        self.assertIn("size:", status_header)
        self.assertIn("usage:", status_header)


if __name__ == "__main__":
    unittest.main(verbosity=2)
