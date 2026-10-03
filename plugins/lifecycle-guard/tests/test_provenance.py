#!/usr/bin/env python3
"""Rule provenance: the hook names the origin project, the audit parses and flags rules.

Run: python3 plugins/lifecycle-guard/tests/test_provenance.py
Uses a throwaway LG_DATA_DIR, so it never touches ~/.claude/lifecycle-guard.
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
OLD = time.strftime("%Y-%m-%d", time.localtime(time.time() - 200 * 86400))

KB = f"""# Core
## Learned
- [ ] Legacy rule without origin _(learned {TODAY}: old format)_
- [ ] Fresh rule _(learned {TODAY} @ shop-api: missed admin view)_
- [ ] Old rule _(learned {OLD} @ shop-api: whatever)_
- [ ] Old but reviewed _(learned {OLD} @ shop-api: x)_ _(reviewed {TODAY})_
- [ ] Test on staging.shopco.com only _(learned {TODAY} @ shop-api: hit prod)_
- [ ] [scope: shop-api] Test on staging.shopco.com only _(learned {TODAY} @ shop-api: hit prod)_
- [ ] Always check the shop-api tenant header _(learned {TODAY} @ other: y)_
- [ ] Hand-added under Learned, no stamp
"""


class Provenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.env = {**os.environ, "LG_DATA_DIR": str(self.data), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, prompt, cwd):
        out = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_prompt.py")],
                             input=json.dumps({"prompt": prompt, "cwd": cwd, "session_id": "s1"}),
                             capture_output=True, text=True, env=self.env)
        return out.stdout

    def audit(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--audit", "--json"],
                             capture_output=True, text=True, env=self.env, check=True)
        return {r["rule"]: r for r in json.loads(out.stdout)["rules"]}

    def test_hook_injects_origin_project(self):
        out = self.run_hook("you missed the refund on the admin side", "/Users/x/code/shop-api")
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("@ shop-api:", ctx)
        self.assertIn("[scope: shop-api]", ctx)
        rec = json.loads((self.data / "corrections.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["cwd"], "/Users/x/code/shop-api")

    def test_hook_without_cwd_uses_placeholder(self):
        ctx = json.loads(self.run_hook("you forgot the webhook retry", ""))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("@ ?:", ctx)

    def test_audit_flags(self):
        for _ in range(2):  # seen in 2+ prompts → a known project
            self.run_hook("hello there", "/Users/x/code/shop-api")
        (self.data / "core.md").write_text(KB)
        rules = self.audit()
        self.assertEqual(len(rules), 7)  # two identical texts collapse in the dict
        self.assertEqual(rules["Legacy rule without origin"]["flags"], ["no-origin"])
        self.assertEqual(rules["Fresh rule"]["flags"], [])
        self.assertEqual(rules["Fresh rule"]["origin"], "shop-api")
        self.assertIn("stale", rules["Old rule"]["flags"])
        self.assertNotIn("stale", rules["Old but reviewed"]["flags"])
        self.assertEqual(rules["Hand-added under Learned, no stamp"]["flags"], ["no-origin"])
        self.assertIn("looks-project-specific", rules["Always check the shop-api tenant header"]["flags"])

    def test_scope_suppresses_project_specific(self):
        (self.data / "core.md").write_text(KB)
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--audit", "--json"],
                             capture_output=True, text=True, env=self.env, check=True)
        same = [r for r in json.loads(out.stdout)["rules"] if r["rule"].startswith("Test on staging")]
        unscoped, scoped = sorted(same, key=lambda r: bool(r["scope"]))
        self.assertIn("looks-project-specific", unscoped["flags"])
        self.assertEqual(scoped["scope"], "shop-api")
        self.assertNotIn("looks-project-specific", scoped["flags"])

    def test_review_after_days_config(self):
        (self.data / "core.md").write_text(KB)
        (self.data / "config.json").write_text(json.dumps({"review_after_days": 365}))
        self.assertNotIn("stale", self.audit()["Old rule"]["flags"])

    def test_lenient_and_unstamped_rules_are_never_dropped(self):
        (self.data / "core.md").write_text(
            "# Core\n- seed checklist item, not audited\n## Learned\n"
            f"- [ ] Odd origin _(learned {TODAY} @ foo(1): cause)_\n"
            "- [ ] Hand-added rule with no stamp\n"
            "- [ ] Broken stamp _(learned yesterday)_\n"
            f"- [ ] Legacy   spacing _(learned {TODAY}: x)_ trailing\n")
        rules = self.audit()
        self.assertNotIn("seed checklist item, not audited", rules)
        self.assertEqual(rules["Odd origin"]["origin"], "foo(1)")
        self.assertEqual(rules["Hand-added rule with no stamp"]["flags"], ["no-origin"])
        self.assertIsNone(rules["Hand-added rule with no stamp"]["age_days"])
        self.assertIn("malformed", rules["Broken stamp"]["flags"])
        self.assertIn("Legacy spacing trailing", rules)

    def test_project_heuristic_ignores_generic_names_and_placeholders(self):
        for cwd in ("/x/test", "/x/test", "/x/config", "/x/config", "/x/shop-api"):
            self.run_hook("hello there", cwd)  # shop-api seen once only
        (self.data / "core.md").write_text(
            "## Learned\n"
            f"- [ ] Run the test suite and check config _(learned {TODAY} @ a: b)_\n"
            f"- [ ] Mention shop-api once _(learned {TODAY} @ a: b)_\n"
            f"- [ ] Docs use example.com and version 1.5.com _(learned {TODAY} @ a: b)_\n")
        for rule in self.audit().values():
            self.assertNotIn("looks-project-specific", rule["flags"], rule["rule"])

    def test_empty_kb(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--audit"],
                             capture_output=True, text=True, env=self.env, check=True)
        self.assertIn("No learned rules", out.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
