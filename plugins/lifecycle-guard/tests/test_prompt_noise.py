#!/usr/bin/env python3
"""Only the user's own words feed learning: no task notifications, pasted text or placeholders.

Run: python3 plugins/lifecycle-guard/tests/test_prompt_noise.py  (temp LG_DATA_DIR, never the real KB)
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
sys.path.insert(0, str(ROOT / "scripts"))
from digest import clean_prompt, is_correction  # noqa: E402

NOTIFICATION = ("<task-notification>\n<task-id>abc</task-id>\n<status>completed</status>\n"
                "<result>VERDICT: FAIL — admin view is missing, not handled</result>\n</task-notification>")
PASTED = ('<pasted_content id="70d1">\nYou missed the point; the file is not done.\n'
          '</pasted_content id="70d1">\n\nnext question')


class CleanPrompt(unittest.TestCase):
    def test_machine_blocks_are_dropped(self):
        for t in (NOTIFICATION, "<system-reminder>x</system-reminder>", "<command-name>/plugin</command-name>",
                  "<local-command-stdout>ok</local-command-stdout>", "Caveat: x", "[Request interrupted by user]"):
            self.assertEqual(clean_prompt(t), "", t)

    def test_pasted_content_removed_user_text_kept(self):
        self.assertEqual(clean_prompt(PASTED), "next question")
        self.assertFalse(is_correction(PASTED))

    def test_unclosed_paste_is_stripped_to_end(self):
        self.assertEqual(clean_prompt('reply to this <pasted_content id="1">you missed it'), "reply to this")

    def test_placeholders_removed(self):
        self.assertEqual(clean_prompt("you missed the refund [Image #2]"), "you missed the refund")
        self.assertEqual(clean_prompt("[Image #2]"), "")

    def test_nested_and_multiple_pastes_do_not_leak(self):
        nested = ('<pasted_content id="a">x <pasted_content id="b">y</pasted_content id="b"> you missed'
                  '</pasted_content id="a"> q')
        self.assertEqual(clean_prompt(nested), "q")
        two = '<pasted_content id="1">you forgot</pasted_content id="1"> ok <pasted_content id="2">missing</pasted_content id="2"> yes'
        self.assertEqual(clean_prompt(two), "ok yes")
        self.assertFalse(is_correction(nested) or is_correction(two))

    def test_leading_machine_block_peeled_user_text_kept(self):
        self.assertEqual(clean_prompt("<system-reminder>a</system-reminder>you forgot X"), "you forgot X")
        self.assertEqual(clean_prompt('<ide_opened_file>The user opened a.py</ide_opened_file> fix it'), "fix it")
        self.assertEqual(clean_prompt("<system-reminder>never closed"), "")
        self.assertEqual(clean_prompt("This session is being continued from a previous conversation that ran "
                                      "out of context. You missed nothing."), "")

    def test_user_html_is_not_mistaken_for_machine_text(self):
        self.assertEqual(clean_prompt("<div> is missing a class"), "<div> is missing a class")

    def test_real_corrections_still_detected(self):
        self.assertTrue(is_correction("you forgot the admin side"))
        self.assertTrue(is_correction("also one important point is you missed the minimum order value"))
        self.assertTrue(is_correction("the refund button is missing."))
        self.assertFalse(is_correction("ok commit and push"))


class HookAndReaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.env = {**os.environ, "LG_DATA_DIR": str(self.data), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, prompt):
        return subprocess.run([sys.executable, str(ROOT / "hooks" / "on_prompt.py")],
                              input=json.dumps({"prompt": prompt, "cwd": "/x/shop", "session_id": "s"}),
                              capture_output=True, text=True, env=self.env).stdout

    def lines(self, name):
        p = self.data / name
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_hook_ignores_notification(self):
        self.assertEqual(self.hook(NOTIFICATION), "")
        self.assertEqual(self.lines("prompts.jsonl"), [])
        self.assertEqual(self.lines("corrections.jsonl"), [])

    def test_hook_pasted_comment_is_not_a_correction(self):
        self.assertEqual(self.hook(PASTED), "")
        self.assertEqual([r["prompt"] for r in self.lines("prompts.jsonl")], ["next question"])
        self.assertEqual(self.lines("corrections.jsonl"), [])

    def test_hook_real_correction_logged_clean(self):
        out = self.hook("you missed the refund on admin [Image #1]")
        self.assertIn("correction", json.loads(out)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.lines("corrections.jsonl")[0]["prompt"], "you missed the refund on admin")

    def test_slash_command_refreshes_stale_bin_copy_and_logs_nothing(self):
        (self.data / "bin").mkdir(parents=True)
        (self.data / "bin" / "digest.py").write_text("# stale copy from the previous plugin version\n")
        self.assertEqual(self.hook("/lifecycle-guard:audit"), "")
        self.assertEqual((self.data / "bin" / "digest.py").read_text(),
                         (ROOT / "scripts" / "digest.py").read_text())
        self.assertEqual(self.lines("prompts.jsonl"), [])

    def test_headless_learner_never_touches_the_kb(self):
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_prompt.py")],
                           input=json.dumps({"prompt": "/lifecycle-guard:learn auto", "cwd": "/x"}),
                           capture_output=True, text=True, env={**self.env, "LG_HEADLESS": "1"})
        self.assertEqual(r.stdout, "")
        self.assertFalse((self.data / "bin").exists())

    def test_old_polluted_logs_ignored_at_read_time(self):
        now = time.time()
        recs = [{"prompt": NOTIFICATION, "cwd": "/x/shop", "ts": now},
                {"prompt": PASTED, "cwd": "/x/shop", "ts": now},
                {"prompt": "you forgot the webhook retry", "cwd": "/x/shop", "ts": now}]
        for name in ("prompts.jsonl", "corrections.jsonl"):
            (self.data / name).write_text("".join(json.dumps(r) + "\n" for r in recs))
        stats = json.loads(subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--stats"],
                                          capture_output=True, text=True, env=self.env, check=True).stdout)
        self.assertEqual(stats["corrections_total"], 1)
        self.assertEqual(stats["prompts_total"], 2)  # "next question" + the real correction
        digest = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py")],
                                capture_output=True, text=True, env=self.env, check=True).stdout
        self.assertNotIn("task-notification", digest)
        self.assertNotIn("pasted_content", digest)
        self.assertIn("2 prompts, 1 flagged corrections", digest)
        self.assertIn("[shop] you forgot the webhook retry", digest)
        self.assertIn("[shop] next question", digest)
        code = ("import sys; sys.path.insert(0, %r); import lg_common; "
                "print(lg_common.count_since('corrections.jsonl', 0), lg_common.count_since('prompts.jsonl', 0))"
                % str(ROOT / "hooks"))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=self.env).stdout
        self.assertEqual(out.split(), ["1", "2"])


    def test_bootstrap_skips_injected_and_pasted_text(self):
        home = self.data / "home"
        proj = home / ".claude" / "projects" / "-x-shop"
        proj.mkdir(parents=True)
        turns = [NOTIFICATION, PASTED, "you forgot the webhook retry",
                 "This session is being continued from a previous conversation. You missed X."]
        (proj / "s.jsonl").write_text("".join(
            json.dumps({"type": "user", "cwd": "/x/shop-api", "timestamp": "2026-10-01T00:00:00Z",
                        "message": {"content": t}}) + "\n" for t in turns))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--bootstrap"],
                       capture_output=True, text=True, check=True, env={**self.env, "HOME": str(home)})
        text = "".join(f.read_text() for f in (self.data / "bootstrap").glob("part-*.md"))
        self.assertIn("[shop-api 2026-10-01] you forgot the webhook retry", text)
        self.assertIn("[shop-api 2026-10-01] next question", text)
        for leak in ("task-notification", "pasted_content", "previous conversation", "VERDICT"):
            self.assertNotIn(leak, text)
        corrections = text.split("## All prompts")[0]
        self.assertEqual(corrections.count("\n- ["), 1)

    def test_broken_digest_import_keeps_hooks_alive(self):
        fake = self.data / "plugin"
        (fake / "scripts").mkdir(parents=True)
        (fake / "scripts" / "digest.py").write_text("raise ImportError('broken')\n")
        env = {**self.env, "CLAUDE_PLUGIN_ROOT": str(fake)}
        for hook in ("on_prompt.py", "on_stop.py"):
            r = subprocess.run([sys.executable, str(ROOT / "hooks" / hook)],
                               input=json.dumps({"prompt": "you missed it", "cwd": str(self.data)}),
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("digest import failed", (self.data / "hook-errors.log").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
