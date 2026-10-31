#!/usr/bin/env python3
"""v1.12.0 hardening: one regression test per finding of the five-lens review + debate (see
.lifecycle/v112-hardening/spec.md). Each test names its finding.

Run: python3 plugins/lifecycle-guard/tests/test_hardening.py  (temp HOME + LG_DATA_DIR, fake `claude`)
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
SEED = ROOT / "skills" / "lifecycle-guard" / "seed"
LONG_CAUSE = "the admin could not see refunds because the list page read a different store " * 2


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home, self.data, self.bin = base / "home", base / "kb", base / "bin"
        (self.data / "domains").mkdir(parents=True)
        self.bin.mkdir()
        self.spawned = base / "spawned.log"
        fake = self.bin / "claude"
        fake.write_text(f"#!/bin/sh\necho \"$@\" >> {self.spawned}\n")
        fake.chmod(0o755)
        self.repo = self.home / "work" / "shop"
        (self.repo / ".git").mkdir(parents=True)
        self.env = {**os.environ, "HOME": str(self.home), "LG_DATA_DIR": str(self.data),
                    "CLAUDE_PLUGIN_ROOT": str(ROOT), "PATH": f"{self.bin}:/usr/bin:/bin",
                    "CLAUDE_CODE_ENTRYPOINT": "cli"}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, *args, check=True, env=None, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), *map(str, args)],
                              capture_output=True, text=True, env=env or self.env, check=check, cwd=cwd)

    def hook(self, name, payload=None, env=None):
        return subprocess.run([sys.executable, str(ROOT / "hooks" / name)], input=json.dumps(payload or {}),
                              capture_output=True, text=True, env=env or self.env)

    def runs(self, wait=0.5):
        time.sleep(wait)
        return self.spawned.read_text().splitlines() if self.spawned.exists() else []

    def kb(self, text, name="core.md"):
        (self.data / name).write_text(text)


class FreshInstall(Base):
    def test_0_18_seed_is_in_budget_and_starts_no_paid_run(self):
        out = self.digest("--lint-rules", env={**self.env, "LG_DATA_DIR": str(SEED)}).stdout
        self.assertTrue(out.startswith("ok:"), out)
        self.hook("on_session_end.py")  # seeds the KB, then maintains it
        self.assertEqual(self.runs(), [])
        cfg = json.loads((self.data / "config.json").read_text())
        self.assertEqual(cfg["kb_too_long"], [])
        self.assertFalse(list((self.data / "backups").glob("*maintain*")))


class MaintainSafety(Base):
    def test_1_11_malformed_stamp_never_loses_ids(self):
        line = (f"- [ ] Every admin list needs filters _(learned 2025-01-01 @ p: {LONG_CAUSE}) "
                "_(was 1a2b3c4d)_ _(reviewed 2025-06-01)_")
        self.kb(f"# Core\n\n## Learned\n{line}\n")
        before = self.digest("--ids").stdout
        self.digest("--maintain")
        self.assertEqual(self.digest("--ids").stdout, before)
        self.assertIn("1a2b3c4d", before)
        audit = json.loads(self.digest("--audit", "--json").stdout)["rules"]
        self.assertTrue(audit[0]["malformed"])

    def test_2_symlinked_files_stay_links_and_keep_their_mode(self):
        real = Path(self.tmp.name) / "dotfiles"
        real.mkdir()
        (real / "core.md").write_text(f"# Core\n\n## Learned\n- [ ] Rule _(learned 2025-01-01 @ p: {LONG_CAUSE})_\n")
        (real / "config.json").write_text("{}")
        for name in ("core.md", "config.json"):
            os.chmod(real / name, 0o600)
            (self.data / name).symlink_to(real / name)
        self.digest("--maintain")
        for name in ("core.md", "config.json"):
            self.assertTrue((self.data / name).is_symlink(), name)
            self.assertEqual(stat.S_IMODE(os.stat(real / name).st_mode), 0o600, name)
        self.assertNotIn(LONG_CAUSE, (real / "core.md").read_text())
        self.assertIn("kb_too_long", (real / "config.json").read_text())


class Hooks(Base):
    def test_4_bad_budget_value_never_silences_the_feature_nudge(self):
        self.hook("on_session_end.py")
        cfg = json.loads((self.data / "config.json").read_text())
        cfg.update(kb_budget_kb="12 KB", kb_over_budget=["core.md"], last_budget_nudge_ts=0)
        (self.data / "config.json").write_text(json.dumps(cfg))
        out = self.hook("on_prompt.py", {"prompt": "please build a refunds feature for the admin panel",
                                         "cwd": str(self.repo)}).stdout
        self.assertIn("feature request", out)
        self.assertIn("ok:", self.digest("--lint-rules").stdout)  # falls back to 12 KB

    def test_7_21_notes_use_tilde_carry_was_and_never_stack(self):
        self.hook("on_session_end.py")
        cfg = json.loads((self.data / "config.json").read_text())
        cfg.update(kb_budget_kb=0.01, kb_over_budget=["core.md"], last_budget_nudge_ts=0)
        (self.data / "config.json").write_text(json.dumps(cfg))
        env = {**self.env, "HOME": str(self.data.parent)}  # DATA under HOME → shown as ~
        out = self.hook("on_prompt.py", {"prompt": "you missed the admin refund view",
                                         "cwd": str(self.repo)}, env=env).stdout
        note = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("~/kb/domains", note)
        self.assertIn("_(was", note)
        self.assertNotIn("over its size budget", note)  # waits for a prompt with no other note
        self.assertLessEqual(len(note.encode()), 700)
        later = self.hook("on_prompt.py", {"prompt": "what does this function do", "cwd": str(self.repo)},
                          env=env).stdout
        self.assertIn("over its size budget", later)

    def test_19_stop_reason_is_bounded_and_names_every_feature(self):
        for f in range(8):
            d = self.repo / ".lifecycle" / f"feat{f}"
            d.mkdir(parents=True)
            (d / "tasks.md").write_text("status: active\n" + "".join(f"- [ ] {'x' * 200} {i}\n" for i in range(30)))
        reason = json.loads(self.hook("on_stop.py", {"cwd": str(self.repo)}).stdout)["reason"]
        for f in range(8):
            self.assertIn(f"feat{f}", reason)
        self.assertLessEqual(len(reason.encode()), 6000)

    def test_c1_automated_session_end_never_spawns(self):
        self.kb(f"# Core\n\n## Learned\n- [ ] {'too long rule text ' * 20} _(learned 2025-01-01 @ p: x)_\n")
        self.hook("on_session_end.py", env={**self.env, "CLAUDE_CODE_ENTRYPOINT": "sdk-cli"})
        self.assertEqual(self.runs(), [])

    def test_c1_failed_learn_backs_off(self):
        self.hook("on_session_end.py")
        now = time.time()
        with open(self.data / "corrections.jsonl", "a") as f:
            for i in range(3):
                f.write(json.dumps({"prompt": f"you missed thing {i}", "cwd": "/x", "ts": now}) + "\n")
        self.hook("on_session_end.py")
        self.assertEqual(len(self.runs(wait=1.0)), 1)  # the fake run never applies → no mark
        (self.data / ".learn.lock").unlink(missing_ok=True)
        self.hook("on_session_end.py")
        self.assertEqual(len(self.runs()), 1)  # backed off: no second paid run the same day


class Context(Base):
    def setUp(self):
        super().setUp()
        self.kb("# Core\n\n## Learned\n- [ ] Core rule _(learned 2025-01-01 @ p: x)_\n")
        for d in ("payments", "notifications", "auth"):
            self.kb(f"# {d}\n\n## Learned\n- [ ] {d} rule _(learned 2025-01-01 @ p: x)_\n", f"domains/{d}.md")

    def test_5_reviewer_full_loads_every_domain(self):
        out = self.digest("--context", "--full", "--domains", "payments").stdout
        for d in ("payments", "notifications", "auth"):
            self.assertIn(f"{d} rule", out)
        self.assertIn("builder named: payments", out)
        self.assertNotIn("auth rule", self.digest("--context", "--domains", "payments").stdout)

    def test_8_10_domains_with_spaces_all_load(self):
        for args in (["payments,", "notifications"], ["payments", "notifications"], ["payments, notifications"]):
            out = self.digest("--context", "--domains", *args).stdout
            self.assertIn("payments rule", out, args)
            self.assertIn("notifications rule", out, args)

    def test_12_rule_resolves_former_ids(self):
        self.kb("# Core\n\n## Learned\n- [ ] New wording _(learned 2025-01-01 @ p: x)_ _(was 1a2b3c4d)_\n")
        out = self.digest("--rule", "1a2b3c4d").stdout
        self.assertIn("New wording", out)
        self.assertNotIn("no rule", out)

    def test_13_relative_cwd_resolves_the_project(self):
        self.kb("# Core\n\n## Learned\n- [ ] [scope: shop] Shop-only rule _(learned 2025-01-01 @ shop: x)_\n")
        out = self.digest("--context", "--cwd", ".", cwd=self.repo).stdout
        self.assertIn("Shop-only rule", out)
        self.assertIn("`shop`", out)


class Platform(Base):
    def test_14_15_tmp_is_never_a_temp_root(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import digest; "
                "print(digest.in_temp_dir('/tmp/scratch-app'), digest.in_temp_dir('/var/folders/xy/T/x'))")
        for tmpdir in ("/tmp", None):
            env = {**self.env, **({"TMPDIR": tmpdir} if tmpdir else {})}
            if not tmpdir:
                env.pop("TMPDIR", None)
            out = subprocess.run([sys.executable, "-c", code, str(ROOT / "scripts")], capture_output=True,
                                 text=True, env=env).stdout.split()
            self.assertEqual(out, ["False", "True"], tmpdir)

    def test_16_lg_digest_copy_never_downgraded_and_unknown_flags_fail(self):
        self.hook("on_prompt.py", {"prompt": "/lifecycle-guard:lg-status", "cwd": "/x"})
        copy = self.data / "bin" / "lg-digest.py"
        self.assertIn('VERSION = "', copy.read_text())
        copy.write_text('VERSION = "99.0.0"\n# a newer copy from another session\n')
        self.hook("on_prompt.py", {"prompt": "/lifecycle-guard:lg-status", "cwd": "/x"})
        self.assertIn("99.0.0", copy.read_text())  # not replaced by this older plugin
        r = self.digest("--context-typo", check=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown flag", r.stderr)

    def test_17_release_notes_carry_the_changelog_section(self):
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
        top = re.search(rf"^## {re.escape(version)} .*?\n(.+?)\n", (REPO / "CHANGELOG.md").read_text(),
                        re.M | re.S).group(1)
        notes = subprocess.run(["bash", ".github/release-notes.sh", f"v{version}"], cwd=REPO,
                               capture_output=True, text=True)
        self.assertEqual(notes.returncode, 0, notes.stderr)
        self.assertIn(top.strip()[:40], notes.stdout)


class Learning(Base):
    def test_c0_proposal_applies_without_losing_anything(self):
        self.kb("# Core\n\n## Learned\n- [ ] Admin can refund with a reason _(learned 2025-01-01 @ shop: m)_\n")
        old = self.digest("--ids").stdout.split()[0]
        prop = Path(self.tmp.name) / "proposal"
        prop.write_text("Done.\n```json\n" + json.dumps({
            "reword": [{"id": old, "rule": "Admin refunds need a reason the customer sees"}],
            "add": [{"file": "domains/payments.md", "rule": "Refund never exceeds paid", "project": "shop",
                     "cause": "refund over paid"}]}) + "\n```\n")
        r = self.digest("--apply-proposal", prop)
        self.assertEqual(json.loads(r.stdout.splitlines()[-1])["applied"], 2)
        self.assertIn(old, self.digest("--ids").stdout)  # history kept via was
        self.assertIn("Refund never exceeds paid", (self.data / "domains" / "payments.md").read_text())
        log = (self.data / "changelog.md").read_text()
        self.assertIn("was: - [ ] Admin can refund with a reason", log)  # original verbatim
        self.assertGreater(json.loads((self.data / "config.json").read_text())["last_learn_ts"], 0)

    def test_c0_bad_proposal_changes_nothing(self):
        self.kb("# Core\n\n## Learned\n- [ ] Keep me _(learned 2025-01-01 @ shop: m)_\n")
        before = (self.data / "core.md").read_text()
        prop = Path(self.tmp.name) / "proposal"
        prop.write_text("I could not finish: the session was blocked.")
        self.assertEqual(self.digest("--apply-proposal", prop, check=False).returncode, 1)
        self.assertEqual((self.data / "core.md").read_text(), before)
        self.assertIn("not applied", (self.data / "hook-errors.log").read_text())

    def test_c0_background_run_is_read_only_and_applied_by_code(self):
        src = (ROOT / "hooks" / "on_session_end.py").read_text()
        self.assertIn('f"Read,Glob,Grep,Bash(python3 {READ_DIGEST}:*)"', src)  # Bash limited to the digest
        self.assertNotIn("Bash(python3:*)", src)
        self.assertNotIn("acceptEdits", src)
        self.assertIn("--apply-proposal", src)

    def proposal(self, obj):
        prop = Path(self.tmp.name) / "proposal"
        prop.write_text(obj if isinstance(obj, str) else json.dumps(obj))
        return self.digest("--apply-proposal", prop, check=False)

    def test_r2_1_stamp_like_text_is_never_written(self):
        self.kb("# Core\n\n## Learned\n- [ ] Keep me _(learned 2025-01-01 @ shop: m)_\n")
        rid = self.digest("--ids").stdout.split()[0]
        before = (self.data / "core.md").read_text()
        self.proposal({"cause": [{"id": rid, "cause": "x _(was deadbeef) y"}],
                       "add": [{"file": "core.md", "rule": "ok rule", "project": "p", "cause": "c _(was deadbeef)_"}]})
        self.assertNotIn("deadbeef", (self.data / "core.md").read_text())
        self.assertEqual((self.data / "core.md").read_text(), before)

    def test_c0_paths_outside_the_kb_are_refused(self):
        self.kb("# Core\n\n## Learned\n- [ ] Keep me _(learned 2025-01-01 @ shop: m)_\n")
        for rel in ("../evil.md", "/etc/evil.md", "domains/../../evil.md", "Domains/X.md"):
            self.assertEqual(self.proposal({"add": [{"file": rel, "rule": "x", "project": "p", "cause": "c"}]})
                             .returncode, 1, rel)
        self.assertFalse(list(Path(self.tmp.name).rglob("evil.md")))

    def test_r2_2_wrong_shapes_refused_cleanly(self):
        self.kb("# Core\n\n## Learned\n- [ ] Keep me _(learned 2025-01-01 @ shop: m)_\n")
        for bad in ({"reword": 5}, {"add": [1, "x"]}, {"cause": {"id": "x"}}, [1, 2]):
            r = self.proposal(bad)
            self.assertNotIn("Traceback", r.stdout + r.stderr, bad)

    def test_r2_3_skipped_lessons_keep_the_material_pending(self):
        self.hook("on_session_end.py")
        r = self.proposal({"add": [{"file": "core.md", "rule": "y" * 400, "project": "p", "cause": "c"}]})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads((self.data / "config.json").read_text()).get("last_learn_ts", 0), 0)
        self.assertIn("skipped", (self.data / "hook-errors.log").read_text())

    def test_r2_7_8_odd_line_breaks_and_checkbox_state_survive_a_reword(self):
        self.kb("# Core\u2028note\n\n## Learned\n- [x] Old wording _(learned 2025-01-01 @ shop: m)_\n")
        rid = self.digest("--ids").stdout.split()[0]
        r = self.proposal({"reword": [{"id": rid, "rule": "New wording"}]})
        self.assertEqual(r.returncode, 0, r.stdout)
        text = (self.data / "core.md").read_text()
        self.assertIn("- [x] New wording", text)
        self.assertIn("\u2028note", text)

    def test_r2_6_script_copy_is_atomic(self):
        src = (ROOT / "hooks" / "lg_common.py").read_text()
        self.assertIn("os.replace(tmp, dst)", src)

    def test_20_digest_is_capped_and_mark_keeps_the_rest_pending(self):
        self.hook("on_session_end.py")
        now = time.time()
        with open(self.data / "prompts.jsonl", "w") as f:
            for i in range(1500):
                f.write(json.dumps({"prompt": f"prompt {i} " + "word " * 80, "cwd": "/x", "ts": now - 1500 + i}) + "\n")
        out = self.digest().stdout
        self.assertLessEqual(len(out), 20000 + 2000)
        self.assertIn("newer records not shown", out)
        self.digest("--mark")
        self.assertIn("prompt", self.digest().stdout.split("All prompts")[1])  # the rest is still pending

    def test_3_9_learn_snapshots_before_edits_and_logs_originals(self):
        text = (ROOT / "commands" / "learn.md").read_text()
        self.assertLess(text.index("--ids >"), text.index("Apply the edits"))
        self.assertIn("verbatim", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
