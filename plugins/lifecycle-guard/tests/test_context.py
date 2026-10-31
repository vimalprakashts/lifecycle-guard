#!/usr/bin/env python3
"""v1.11.0 token diet: `digest.py --context` is one compact, de-duplicated checklist load, and the
skill/reviewer use it instead of reading the KB files + --rules.

Run: python3 plugins/lifecycle-guard/tests/test_context.py  (temp HOME + LG_DATA_DIR)
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "lifecycle-guard"

CORE = """# Core lifecycle checklist

Applies to every feature.

## Actors
- [ ] End user / customer flows identified

## Learned
- [ ] Admin can refund with a reason _(learned 2026-01-02 @ shop: missed admin refund)_ _(reviewed 2026-03-01)_
- [ ] [scope: elsewhere] Only for another project _(learned 2026-01-02 @ elsewhere: x)_
- [ ] [scope: umbrella] Holds for every repo under umbrella _(learned 2026-01-02 @ repo: y)_
"""
PAYMENTS = "# Payments\n\n## Learned\n- [ ] Refund never exceeds amount paid _(learned 2026-01-03 @ shop: z)_\n"


class Context(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home, self.data = base / "home", base / "kb"
        (self.data / "domains").mkdir(parents=True)
        self.repo = self.home / "umbrella" / "repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.data / "core.md").write_text(CORE)
        (self.data / "style.md").write_text("# Style\n\n## Stack\n- [ ] Use Mongoose\n")
        (self.data / "domains" / "payments.md").write_text(PAYMENTS)
        (self.data / "domains" / "auth.md").write_text("# Auth\n- [ ] MFA reset flow\n")
        self.env = {**os.environ, "HOME": str(self.home), "LG_DATA_DIR": str(self.data)}

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), *map(str, args)],
                              capture_output=True, text=True, env=self.env, check=True).stdout

    def test_loads_core_style_and_only_named_domains_without_boxes_or_stamps(self):
        out = self.digest("--context", "--domains", "payments", "--cwd", self.repo)
        self.assertIn("## core.md", out)
        self.assertIn("## style.md", out)
        self.assertIn("## domains/payments.md", out)
        self.assertNotIn("MFA reset", out)  # auth not requested
        self.assertIn("- End user / customer flows identified", out)
        self.assertIn("- Use Mongoose", out)
        self.assertNotIn("- [ ]", out)
        self.assertNotIn("_(learned", out)
        self.assertNotIn("_(reviewed", out)
        self.assertIn("domains available: auth, payments; loaded: payments", out)

    def test_out_of_scope_rules_omitted_and_counted_enclosing_scope_kept(self):
        out = self.digest("--context", "--cwd", self.repo)
        self.assertNotIn("Only for another project", out)
        self.assertIn("1 rule(s) scoped to other projects omitted", out)
        self.assertIn("Holds for every repo under umbrella", out)
        self.assertNotIn("[scope:", out)

    def test_ids_match_rules_output(self):
        ctx = self.digest("--context", "--domains", "payments", "--cwd", self.repo)
        ids = dict((m.group(2), m.group(1)) for m in re.finditer(r"^- \[([0-9a-f]{8})\] (.+)$", ctx, re.M))
        rules = self.digest("--rules", "--cwd", self.repo)
        self.assertEqual(len(ids), 3)
        for text, rid in ids.items():
            self.assertRegex(rules, rf"(?m)^{rid}\s.*{re.escape(text[:40])}")

    def test_unknown_domain_is_reported_and_no_domains_loads_core_and_style(self):
        out = self.digest("--context", "--domains", "nope,payments.md", "--cwd", self.repo)
        self.assertIn("no domain file: nope", out)
        self.assertIn("## domains/payments.md", out)  # a .md suffix is tolerated
        bare = self.digest("--context", "--cwd", self.repo)
        self.assertIn("loaded: (none)", bare)
        self.assertNotIn("## domains/", bare)

    def test_flags_without_values_never_crash_or_swallow_the_next_flag(self):
        out = self.digest("--context", "--domains", "--cwd", self.repo)
        self.assertIn("loaded: (none)", out)
        self.assertIn("Holds for every repo under umbrella", out)  # --cwd still honoured
        self.assertIn("## core.md", self.digest("--context", "--cwd"))

    def test_trailing_notes_stripped_from_plain_items(self):
        (self.data / "style.md").write_text("# Style\n- [ ] Use Mongoose _(always; stated many times)_\n")
        out = self.digest("--context", "--cwd", self.repo)
        self.assertIn("- Use Mongoose\n", out)

    def test_missing_style_file_is_skipped(self):
        (self.data / "style.md").unlink()
        out = self.digest("--context", "--cwd", self.repo)
        self.assertIn("## core.md", out)
        self.assertNotIn("## style.md", out)

    def test_smaller_than_reading_the_files_plus_rules(self):
        (self.data / "core.md").write_text(CORE + "".join(
            f"- [ ] rule number {i} about a thing _(learned 2026-01-0{i % 9 + 1} @ shop: cause {i} of the miss)_\n"
            for i in range(40)))
        old = sum(len(p.read_text()) for p in (self.data / "core.md", self.data / "style.md",
                                                self.data / "domains" / "payments.md"))
        old += len(self.digest("--rules", "--cwd", self.repo))
        new = len(self.digest("--context", "--domains", "payments", "--cwd", self.repo))
        self.assertLess(new, old * 0.6)


class Prose(unittest.TestCase):
    def test_skill_is_slim_and_points_to_context_and_template(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("--context --domains", text)
        self.assertIn("references/spec-template.md", text)
        self.assertTrue((SKILL / "references" / "spec-template.md").exists())
        self.assertIn("Round 2 only if round 1 had critical/high", text)

    def test_reviewers_load_context_not_kb_files(self):
        for p in (ROOT / "agents" / "lifecycle-reviewer.md", SKILL / "references" / "review.md"):
            text = p.read_text()
            self.assertIn("--context --full --domains", text, p.name)
            self.assertNotIn("--rules", text, p.name)
            self.assertNotRegex(text, r"\(`?core\.md`?, `?style\.md`?", p.name)
        self.assertIn("Round 2 only if round 1 had critical/high", (ROOT / "commands" / "review.md").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
