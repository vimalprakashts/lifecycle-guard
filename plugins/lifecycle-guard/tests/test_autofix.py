#!/usr/bin/env python3
"""v1.12.0: the knowledge base stays within budget automatically, for every user, with no manual /audit:
SessionEnd trims long causes (no model) and starts a throttled background reword of too-long rules; the
prompt hook reminds the user, at most weekly, of the one fix that needs a person (merging rules).

Run: python3 plugins/lifecycle-guard/tests/test_autofix.py  (temp HOME + LG_DATA_DIR, fake `claude`)
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
from digest import rule_id  # noqa: E402

LONG_CAUSE = "the admin could not see refunds because the list page read a different store " * 2
LONG_RULE = "When a refund is approved " + "the admin and the customer both see the new state and the amount " * 5


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data, self.bin = base / "kb", base / "bin"
        (self.data / "domains").mkdir(parents=True)
        self.bin.mkdir()
        self.spawned = base / "spawned.log"
        fake = self.bin / "claude"  # stands in for the CLI: records each background run
        fake.write_text(f"#!/bin/sh\necho \"$@\" >> {self.spawned}\n")
        fake.chmod(0o755)
        self.env = {**os.environ, "HOME": str(base / "home"), "LG_DATA_DIR": str(self.data),
                    "CLAUDE_PLUGIN_ROOT": str(ROOT), "PATH": f"{self.bin}:/usr/bin:/bin",
                    "CLAUDE_CODE_ENTRYPOINT": "cli"}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def kb(self, *rules):
        (self.data / "core.md").write_text("# Core\n\n## Learned\n" + "".join(f"- [ ] {r}\n" for r in rules))

    def config(self, **kw):
        c = json.loads((self.data / "config.json").read_text()) if (self.data / "config.json").exists() else {}
        (self.data / "config.json").write_text(json.dumps({**c, **kw}))

    def cfg(self):
        return json.loads((self.data / "config.json").read_text())

    def session_end(self):
        subprocess.run([sys.executable, str(ROOT / "hooks" / "on_session_end.py")], input="{}",
                       capture_output=True, text=True, env=self.env, check=True)

    def runs(self, wait=3.0):
        end = time.time() + wait
        while time.time() < end:
            if self.spawned.exists() and not (self.data / ".learn.lock").exists():
                break
            time.sleep(0.05)
        return self.spawned.read_text().splitlines() if self.spawned.exists() else []

    def prompt(self, text="what does this function do"):
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_prompt.py")],
                           input=json.dumps({"prompt": text, "cwd": "/x/shop"}),
                           capture_output=True, text=True, env=self.env)
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout else ""


class Maintain(Base):
    def test_long_causes_trimmed_without_a_model_ids_kept_original_logged(self):
        self.kb(f"Admin sees refunds _(learned 2026-01-01 @ shop: {LONG_CAUSE})_")
        self.config(auto_learn=False)
        self.session_end()
        text = (self.data / "core.md").read_text()
        self.assertNotIn(LONG_CAUSE, text)
        self.assertIn("Admin sees refunds _(learned 2026-01-01 @ shop: the admin could not", text)
        self.assertIn(" …)_", text)
        self.assertIn(LONG_CAUSE.strip(), (self.data / "changelog.md").read_text())  # restorable
        self.assertTrue(list((self.data / "backups").glob("core.md.*-maintain.bak")))
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--rules"],
                             capture_output=True, text=True, env=self.env).stdout
        self.assertIn(rule_id("Admin sees refunds"), out)
        self.assertEqual(self.runs(wait=0.3), [])  # auto_learn off: no model run

    def test_clean_kb_is_left_alone(self):
        self.kb("Short rule _(learned 2026-01-01 @ shop: short cause)_")
        before = (self.data / "core.md").read_text()
        self.session_end()
        self.assertEqual((self.data / "core.md").read_text(), before)
        log = self.data / "changelog.md"  # the hook seeds a fresh KB; maintain must add nothing to it
        self.assertNotIn("maintain", log.read_text() if log.exists() else "")
        self.assertEqual(self.cfg()["kb_too_long"], [])


class Compaction(Base):
    def test_too_long_rule_starts_one_background_reword_a_day(self):
        self.kb(f"{LONG_RULE} _(learned 2026-01-01 @ shop: x)_")
        self.config(auto_learn=True, last_learn_ts=time.time())  # nothing new to learn
        self.session_end()
        runs = self.runs()
        self.assertEqual(len(runs), 1)
        self.assertIn("/lifecycle-guard:learn auto", runs[0])
        self.assertGreater(self.cfg()["last_compact_ts"], 0)
        self.session_end()  # same day: throttled, no second run
        self.assertEqual(len(self.runs(wait=0.5)), 1)

    def test_no_reword_run_when_rules_fit(self):
        self.kb("Short rule _(learned 2026-01-01 @ shop: x)_")
        self.config(auto_learn=True, last_learn_ts=time.time())
        self.session_end()
        self.assertEqual(self.runs(wait=0.5), [])


class BudgetNudge(Base):
    def test_over_budget_reminds_once_a_week_and_only_then(self):
        self.kb("Short rule _(learned 2026-01-01 @ shop: x)_")
        self.config(kb_budget_kb=0.01)
        self.session_end()
        self.assertIn("core.md", self.cfg()["kb_over_budget"])
        first = self.prompt()
        self.assertIn("/lifecycle-guard:audit", first)
        self.assertLessEqual(len(first.encode()), 700)
        self.assertEqual(self.prompt(), "")  # not again this week
        self.config(last_budget_nudge_ts=time.time() - 8 * 86400)
        self.assertIn("over its size budget", self.prompt())

    def test_within_budget_never_nudges(self):
        self.kb("Short rule _(learned 2026-01-01 @ shop: x)_")
        self.session_end()
        self.assertEqual(self.prompt(), "")



class Safety(Base):
    """Unattended edits on someone else's knowledge base: never lose a lesson or a setting."""

    def digest(self, *args, check=True):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), *map(str, args)],
                              capture_output=True, text=True, env=self.env, check=check)

    def test_no_file_edits_while_a_background_learn_holds_the_lock(self):
        self.kb(f"Admin sees refunds _(learned 2026-01-01 @ shop: {LONG_CAUSE})_")
        (self.data / ".learn.lock").write_text("123")
        before = (self.data / "core.md").read_text()
        self.digest("--maintain")
        self.assertEqual((self.data / "core.md").read_text(), before)
        self.assertEqual(self.cfg()["kb_too_long"], [])  # stats still recorded

    def test_stale_lock_is_cleared_and_a_failed_spawn_leaves_no_lock(self):
        self.kb(f"{LONG_RULE} _(learned 2026-01-01 @ shop: x)_")
        self.config(auto_learn=True, last_learn_ts=time.time())
        lock = self.data / ".learn.lock"
        lock.write_text("old")
        os.utime(lock, (time.time() - 3 * 3600,) * 2)
        (self.data / "learn.log").mkdir()  # opening the log fails → the spawn fails
        self.session_end()
        self.assertFalse(lock.exists())
        self.assertEqual(self.runs(wait=0.3), [])

    def test_unreadable_config_is_never_overwritten(self):
        self.kb(f"{LONG_RULE} _(learned 2026-01-01 @ shop: x)_")
        broken = '{"auto_learn": false, "rule_max_chars": 3'
        (self.data / "config.json").write_text(broken)
        self.digest("--maintain")
        self.digest("--mark")
        self.assertEqual((self.data / "config.json").read_text(), broken)

    def test_unreadable_config_starts_no_background_run(self):
        self.kb(f"{LONG_RULE} _(learned 2026-01-01 @ shop: x)_")
        (self.data / "config.json").write_text('{"auto_learn": true, ')
        for _ in range(2):
            self.session_end()
        self.assertEqual(self.runs(wait=0.5), [])

    def test_same_too_long_rules_retry_weekly_not_daily(self):
        self.kb(f"{LONG_RULE} _(learned 2026-01-01 @ shop: x)_")
        self.config(auto_learn=True, last_learn_ts=time.time())
        self.session_end()
        self.assertEqual(len(self.runs()), 1)
        self.config(last_compact_ts=time.time() - 2 * 86400)  # a day later, same rules still too long
        self.session_end()
        self.assertEqual(len(self.runs(wait=0.5)), 1)
        self.config(last_compact_ts=time.time() - 8 * 86400)
        self.session_end()
        self.assertEqual(len(self.runs()), 2)

    def test_every_stamp_trimmed_and_crlf_kept(self):
        line = (f"- [ ] Rule A _(learned 2026-01-01 @ shop: short)_ "
                f"_(learned 2026-02-01 @ shop: {LONG_CAUSE})_")
        (self.data / "core.md").write_bytes(f"# Core\r\n\r\n## Learned\r\n{line}\r\n".encode())
        self.digest("--maintain")
        raw = (self.data / "core.md").read_bytes()
        self.assertIn(b"\r\n## Learned\r\n", raw)
        self.assertNotIn(LONG_CAUSE.encode(), raw)
        self.assertIn(b"ok", self.digest("--lint-rules").stdout.encode())

    def test_id_snapshot_catches_a_dropped_rule_and_accepts_a_was_stamp(self):
        self.kb("Rule one _(learned 2026-01-01 @ shop: x)_", "Rule two _(learned 2026-01-01 @ shop: y)_")
        snap = self.data / ".ids-before"
        snap.write_text(self.digest("--ids").stdout)
        old = rule_id("Rule two")
        self.kb("Rule one _(learned 2026-01-01 @ shop: x)_")
        r = self.digest("--verify-ids", snap, check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn(old, r.stdout)
        self.kb("Rule one _(learned 2026-01-01 @ shop: x)_",
                f"Rule two, shorter _(learned 2026-01-01 @ shop: y)_ _(was {old})_")
        self.assertIn("ok", self.digest("--verify-ids", snap).stdout)

    def test_reminder_rechecks_size_after_an_audit(self):
        self.kb("Short rule _(learned 2026-01-01 @ shop: x)_")
        self.config(kb_over_budget=["core.md"])  # recorded at SessionEnd, since fixed
        self.assertEqual(self.prompt(), "")


if __name__ == "__main__":
    unittest.main(verbosity=1)
