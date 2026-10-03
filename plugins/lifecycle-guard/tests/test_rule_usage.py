#!/usr/bin/env python3
"""Rule usage: reviews record which learned rules they applied; the audit uses it.

Run: python3 plugins/lifecycle-guard/tests/test_rule_usage.py  (temp LG_DATA_DIR, never the real KB)
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
from digest import parse_rules_applied, rule_id  # noqa: E402

OLD = time.strftime("%Y-%m-%d", time.localtime(time.time() - 200 * 86400))


class Usage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "kb"
        self.proj = Path(self.tmp.name) / "shop"
        (self.data / "domains").mkdir(parents=True)
        (self.proj / ".lifecycle" / "refunds").mkdir(parents=True)
        self.env = {**os.environ, "LG_DATA_DIR": str(self.data), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)
        (self.data / "core.md").write_text(
            "## Learned\n"
            f"- [ ] Admin can refund _(learned {OLD} @ shop: missed)_\n"
            f"- [ ] Never used rule _(learned {OLD} @ shop: x)_\n"
            f"- [ ] [scope: shop] Scoped **bold** rule _(learned {OLD} @ shop: y)_ _(reviewed {OLD})_\n")
        self.refund, self.unused = rule_id("Admin can refund"), rule_id("Never used rule")

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), *args],
                              capture_output=True, text=True, env=self.env, check=True).stdout

    def stop(self):
        r = subprocess.run([sys.executable, str(ROOT / "hooks" / "on_stop.py")],
                           input=json.dumps({"cwd": str(self.proj)}), capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def write_review(self, body):
        (self.proj / ".lifecycle" / "refunds" / "review.md").write_text(body)

    def usage(self):
        p = self.data / "usage.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def audit(self):
        return {r["rule"]: r for r in json.loads(self.digest("--audit", "--json"))["rules"]}

    def test_ids_are_stable_and_match_between_rules_and_audit(self):
        self.assertEqual(rule_id("Admin  can   refund"), rule_id("admin can refund"))
        self.assertEqual(rule_id("Scoped **bold** rule"), rule_id("Scoped bold rule"))
        listed = {line.split()[0] for line in self.digest("--rules").splitlines()}
        self.assertEqual(listed, {r["id"] for r in self.audit().values()})

    def test_parse_rules_applied_only_reads_its_section(self):
        text = (f"VERDICT: PASS\n## Findings addressed\n- {self.unused} caught — not in section\n"
                f"## Rules applied\n- `{self.refund}` caught — admin refund missing\n- {self.unused} satisfied\n"
                "- zzzzzzzz caught\n- not a rule line\n## Known gaps\n- deadbeef caught\n")
        self.assertEqual(parse_rules_applied(text), [(self.refund, "caught"), (self.unused, "satisfied")])
        decorated = (f"## Rules applied\n- **{self.refund}** caught — x\n- [{self.unused}] satisfied\n"
                     f"- {self.refund} (core.md:2) — caught: y\n* `{self.unused}`  Satisfied\n")
        self.assertEqual(parse_rules_applied(decorated), [(self.refund, "caught"), (self.unused, "satisfied"),
                                                          (self.refund, "caught"), (self.unused, "satisfied")])

    def test_stop_hook_ingests_once(self):
        self.write_review(f"VERDICT: PASS\n## Rules applied\n- {self.refund} caught — admin refund missing\n")
        self.stop()
        self.stop()  # repeated Stop runs must not double-count
        recs = self.usage()
        self.assertEqual(len(recs), 1)
        self.assertEqual((recs[0]["rule"], recs[0]["outcome"], recs[0]["project"], recs[0]["feature"]),
                         (self.refund, "caught", "shop", "refunds"))
        self.write_review(f"VERDICT: PASS — typo fixed\n## Known gaps\n- none\n"
                          f"## Rules applied\n- {self.refund} caught — admin refund missing\n")
        self.stop()  # prose edit, same rules → no recount
        self.assertEqual(len(self.usage()), 1)
        self.write_review(f"VERDICT: PASS\n## Rules applied\n- {self.refund} satisfied\n")  # re-review
        self.stop()
        self.assertEqual(len(self.usage()), 2)

    def test_record_time_is_review_time_not_ingest_time(self):
        self.write_review(f"## Rules applied\n- {self.unused} satisfied\n")
        old = time.time() - 200 * 86400
        os.utime(self.proj / ".lifecycle" / "refunds" / "review.md", (old, old))
        self.stop()
        self.assertAlmostEqual(self.usage()[0]["ts"], old, delta=2)
        self.assertIn("stale", self.audit()["Never used rule"]["flags"])  # an old use doesn't refresh it

    def test_usage_keeps_rules_fresh_and_unused_ones_go_stale(self):
        self.write_review(f"VERDICT: PASS\n## Rules applied\n- {self.refund} caught — x\n")
        self.stop()
        rules = self.audit()
        used, unused = rules["Admin can refund"], rules["Never used rule"]
        self.assertEqual((used["applied"], used["caught"]), (1, 1))
        self.assertNotIn("stale", used["flags"])
        self.assertEqual(unused["applied"], 0)
        self.assertIn("stale", unused["flags"])
        report = self.digest("--audit")
        self.assertIn("usage: 1 rules have caught a miss · 2 never applied", report)
        self.assertIn("never applied", report)

    def test_usage_summary_for_status(self):
        self.write_review(f"## Rules applied\n- {self.refund} caught — x\n")
        self.stop()
        out = self.digest("--usage")
        self.assertIn("3 learned rules · 1 have caught a miss · 2 never applied in a review", out)
        self.assertIn(f"`{self.refund}` applied 1× (caught 1", out)

    def test_no_lifecycle_dir_and_unknown_ids_are_harmless(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        self.assertEqual(self.digest("--ingest-usage", str(empty)).strip(), "0")
        self.write_review("## Rules applied\n- abcdef12 caught — rule since reworded\n")
        self.stop()
        self.assertEqual(len(self.usage()), 1)
        self.assertTrue(all(r["applied"] == 0 for r in self.audit().values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
