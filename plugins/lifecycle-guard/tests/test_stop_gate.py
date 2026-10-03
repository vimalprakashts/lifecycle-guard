#!/usr/bin/env python3
"""The Stop gate: the plugin's core promise. A feature can't be "done" while boxes are open or the
independent review hasn't passed.

Run: python3 plugins/lifecycle-guard/tests/test_stop_gate.py  (temp LG_DATA_DIR, never the real KB)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class StopGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / "proj"
        self.proj.mkdir()
        self.data = Path(self.tmp.name) / "kb"
        self.env = {**os.environ, "LG_DATA_DIR": str(self.data), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def feature(self, slug, tasks, review=None):
        d = self.proj / ".lifecycle" / slug
        d.mkdir(parents=True)
        (d / "tasks.md").write_text(tasks)
        if review is not None:
            (d / "review.md").write_text(review)

    def stop(self, **extra):
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_stop.py")],
                           input=json.dumps({"cwd": str(self.proj), **extra}),
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_no_lifecycle_dir_never_blocks(self):
        self.assertIsNone(self.stop())

    def test_open_boxes_block_and_are_listed(self):
        self.feature("refunds", "status: active\n## Backend\n- [x] done thing\n- [ ] admin refund\n* [ ] webhook\n")
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("2 open", out["reason"])
        self.assertIn("admin refund", out["reason"])
        self.assertIn("webhook", out["reason"])
        self.assertNotIn("done thing", out["reason"])

    def test_many_open_items_are_truncated(self):
        self.feature("big", "status: active\n" + "".join(f"- [ ] item {i}\n" for i in range(20)))
        reason = self.stop()["reason"]
        self.assertIn("item 11", reason)
        self.assertNotIn("item 12\n", reason)
        self.assertIn("and 8 more", reason)

    def test_deferred_and_ticked_items_pass_the_box_check(self):
        self.feature("f", "status: active\n- [x] a\n- [~] b — needs prod credentials\n", "VERDICT: PASS\n")
        self.assertIsNone(self.stop())

    def test_all_ticked_without_review_blocks_on_review(self):
        self.feature("f", "status: active\n- [x] a\n")
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("independent review", out["reason"])
        self.assertIn("f", out["reason"])

    def test_failed_review_still_blocks(self):
        self.feature("f", "status: active\n- [x] a\n", "VERDICT: FAIL\n1. [high] x\n")
        self.assertEqual(self.stop()["decision"], "block")

    def test_unedited_review_template_does_not_unblock(self):
        self.feature("f", "status: active\n- [x] a\n", "# Review — f\nVERDICT: PASS | FAIL\n")
        self.assertEqual(self.stop()["decision"], "block")

    def test_verdict_mentioned_in_prose_is_not_a_verdict(self):
        self.feature("f", "status: active\n- [x] a\n", "VERDICT: FAIL\nround 2 should reach verdict: pass\n")
        self.assertEqual(self.stop()["decision"], "block")

    def test_review_pass_or_explicit_deferral_unblocks(self):
        self.feature("a", "status: active\n- [x] a\n", "# Review\n**VERDICT: PASS** (2 rounds)\n")
        self.feature("b", "status: active\n- [x] b\n", "review: deferred — user will review after launch\n")
        self.assertIsNone(self.stop())

    def test_draft_and_done_features_never_block(self):
        self.feature("draft", "status: draft\n- [ ] not approved yet\n")
        self.feature("done", "status: done\n- [ ] leftover\n")
        self.assertIsNone(self.stop())

    def test_loop_guard_and_config_switch(self):
        self.feature("f", "status: active\n- [ ] open\n")
        self.assertIsNone(self.stop(stop_hook_active=True))
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "config.json").write_text(json.dumps({"stop_gate": False}))
        self.assertIsNone(self.stop())

    def test_every_active_feature_is_checked(self):
        self.feature("one", "status: active\n- [ ] first open\n")
        self.feature("two", "status: active\n- [ ] second open\n")
        reason = self.stop()["reason"]
        self.assertIn("first open", reason)
        self.assertIn("second open", reason)

    def test_status_phrase_inside_a_task_is_not_the_header(self):
        self.feature("draft", "status: draft\n- [ ] after approval set status: active\n")
        self.assertIsNone(self.stop())

    def test_decorated_status_headers_still_count(self):
        for i, head in enumerate(("> status: active", "- status: active", "**Status:** active", "Status: Active\r")):
            self.feature(f"f{i}", f"{head}\n- [ ] open {i}\n")
        reason = self.stop()["reason"]
        for i in range(4):
            self.assertIn(f"open {i}", reason)

    def test_status_header_is_case_insensitive(self):
        self.feature("f", "Status: Active\n- [ ] open\n")
        self.assertEqual(self.stop()["decision"], "block")


if __name__ == "__main__":
    unittest.main(verbosity=2)
