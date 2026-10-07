#!/usr/bin/env python3
"""Spec lint: requirement lines that could be pasted into any feature's spec get flagged.

Run: python3 plugins/lifecycle-guard/tests/test_spec_lint.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from digest import lint_spec_text  # noqa: E402

SPEC = """# Refunds
## Goal
Make refunds robust and handle everything correctly.
## Root cause
The old flow worked properly until the gateway changed.
## Failure and edge cases
- Handle errors gracefully
- Gateway timeout → refund stays `pending`; retry job every 5 min, max 6 tries; admin sees "retrying (n/6)"
- All edge cases covered
## Acceptance criteria
- Given a refund, notify the customer
- Given a refund, notify the customer by email with the amount and reference
- Given a partial refund, the order shows Paid / Refunded / Balance
- Make sure everything is secure
- Validate input as needed, etc.
- The "handle errors gracefully" wording from the old spec is gone
```
handle errors gracefully  # inside a code fence: an example, not a requirement
```
- Ownership checked: an admin of tenant A gets 404 for tenant B's refund (N/A for webhooks)
## Out of scope
- Various TBD reporting things
## Checklist coverage
- Notifications ✓ — properly covered
"""


class Lint(unittest.TestCase):
    def hits(self, text=SPEC):
        return {n: phrase.lower() for n, phrase, _ in lint_spec_text(text)}

    def line_of(self, needle):
        return next(i for i, l in enumerate(SPEC.splitlines(), 1) if needle in l)

    def test_generic_requirement_lines_are_flagged(self):
        hits = self.hits()
        self.assertIn(hits[self.line_of("Handle errors gracefully")], {"gracefully", "handle errors"})
        self.assertEqual(hits[self.line_of("All edge cases covered")], "all edge cases")
        self.assertEqual(hits[self.line_of("Given a refund, notify the customer")], "notify the customer")
        self.assertIn("secure", hits[self.line_of("Make sure everything is secure")])
        self.assertEqual(hits[self.line_of("as needed, etc.")], "as needed")

    def test_specific_lines_pass(self):
        hits = self.hits()
        for needle in ("Gateway timeout", "by email with the amount", "Paid / Refunded / Balance"):
            self.assertNotIn(self.line_of(needle), hits, needle)

    def test_narrative_quoted_fenced_na_and_non_requirement_sections_skipped(self):
        hits = self.hits()
        for needle in ("Make refunds robust", "worked properly", "wording from the old spec",
                       "inside a code fence", "Ownership checked", "Various TBD", "properly covered"):
            self.assertNotIn(self.line_of(needle), hits, needle)

    def test_apostrophes_do_not_hide_slop_and_real_quotes_still_do(self):
        text = "## Failure cases\n- If the user's cart is empty, handle errors gracefully on the admin's page\n" \
               "- Don't retry; it won't help — handle errors gracefully\n" \
               "- The 'handle errors gracefully' phrase is banned here\n"
        self.assertEqual(sorted(self.hits(text)), [2, 3])

    def test_heading_words_must_match_whole_words(self):
        text = "# Spec\n## Acceptance criteria\n- order total shown in INR\n## Stateless design\n- handle errors gracefully\n"
        self.assertEqual(self.hits(text), {})  # 'Stateless' is not a requirement section

    def test_unix_paths_are_not_etc(self):
        text = "## Failure cases\n- DNS override in /etc/hosts is ignored; resolver result wins\n- retries, timeouts, etc.\n"
        self.assertEqual(list(self.hits(text)), [3])

    def test_files_without_requirement_headings_are_linted_in_full(self):
        tasks = "status: active\n## Backend\n- [ ] handle errors gracefully\n- [ ] refund endpoint returns 409 on double submit\n"
        self.assertEqual(list(self.hits(tasks)), [3])

    def test_cli_reports_and_never_fails(self):
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / "spec.md"
            spec.write_text(SPEC)
            out = subprocess.run([sys.executable, str(ROOT / "scripts" / "digest.py"), "--lint-spec",
                                  str(spec), str(Path(d) / "missing.md")], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0)
            self.assertIn(f"spec.md:{self.line_of('Handle errors gracefully')} — ", out.stdout)
            self.assertIn("missing.md: not found", out.stdout)
            self.assertIn("5 vague line(s)", out.stdout)

    def test_shipped_seed_checklists_are_clean(self):
        seeds = list((ROOT / "skills" / "lifecycle-guard" / "seed").rglob("*.md"))
        self.assertTrue(seeds)
        for f in seeds:
            self.assertEqual(lint_spec_text(f.read_text()), [], f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
