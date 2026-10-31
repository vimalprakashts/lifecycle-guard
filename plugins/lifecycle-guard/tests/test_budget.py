#!/usr/bin/env python3
"""Context budget (issue #1): every tier of text the plugin puts into a model's context has a ceiling,
so growth is a deliberate, reviewed change instead of drift. Raise a budget only with a reason in the
commit and a CHANGELOG line — see "Context budget" in plugins/lifecycle-guard/CLAUDE.md.

Run: python3 plugins/lifecycle-guard/tests/test_budget.py  (temp HOME + LG_DATA_DIR)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "lifecycle-guard"

# bytes; measured at v1.12.0 plus a little headroom
ALWAYS_ON = 1450        # model-visible descriptions: every turn of every session
HOOK_NOTE = 700         # one UserPromptSubmit injection
SKILL_MD = 7200         # loaded when the skill triggers, then re-sent every later turn
SPEC_TEMPLATE = 4800    # read only when writing a full spec
REVIEW_FALLBACK = 4500  # fallback critic prompt
BUILDER_CONTEXT = 9000  # --context for one domain on the 60-rule fixture KB below
USER_ONLY = {"audit", "bootstrap", "lg-status"}  # never auto-invoked: keep their descriptions out of context


def frontmatter(p):
    m = re.match(r"^---\n(.*?)\n---\n", p.read_text(), re.S)
    fm = dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M)) if m else {}
    assert fm.get("description", "").strip() not in (">", "|", ">-", "|-"), f"{p.name}: multi-line description"
    return fm


class AlwaysOn(unittest.TestCase):
    def test_model_visible_descriptions_within_budget(self):
        files = [SKILL / "SKILL.md", *(ROOT / "agents").glob("*.md"), *(ROOT / "commands").glob("*.md")]
        visible = {p.name: len(fm.get("description", "").encode()) for p in files
                   if (fm := frontmatter(p)).get("disable-model-invocation") != "true"}
        self.assertLessEqual(sum(visible.values()), ALWAYS_ON, visible)

    def test_user_only_commands_hidden_from_the_model(self):
        for name in USER_ONLY:
            self.assertEqual(frontmatter(ROOT / "commands" / f"{name}.md").get("disable-model-invocation"),
                             "true", name)


class PerFeature(unittest.TestCase):
    def test_instruction_files_within_budget(self):
        for path, budget in ((SKILL / "SKILL.md", SKILL_MD),
                             (SKILL / "references" / "spec-template.md", SPEC_TEMPLATE),
                             (SKILL / "references" / "review.md", REVIEW_FALLBACK)):
            self.assertLessEqual(len(path.read_bytes()), budget, path.name)


class Runtime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data = base / "kb"
        (self.data / "domains").mkdir(parents=True)
        self.repo = base / "home" / "a-realistic-thirty-char-project"  # the name appears twice in notes
        (self.repo / ".git").mkdir(parents=True)
        self.env = {**os.environ, "HOME": str(base / "home"), "LG_DATA_DIR": str(self.data),
                    "CLAUDE_PLUGIN_ROOT": str(ROOT)}
        self.env.pop("LG_HEADLESS", None)

        def kb(name, n, title):
            rules = "".join(f"- [ ] {title} rule {i}: " + ("when this situation happens check that thing " * 6)[:220]
                            + f" _(learned 2026-01-01 @ shop: cause {i})_\n" for i in range(n))
            return f"# {title}\n\n## Things\n- [ ] A seed item\n\n## Learned\n{rules}"
        (self.data / "core.md").write_text(kb("core", 30, "Core"))
        (self.data / "style.md").write_text(kb("style", 10, "Style"))
        (self.data / "domains" / "payments.md").write_text(kb("payments", 10, "Payments"))
        (self.data / "domains" / "auth.md").write_text(kb("auth", 10, "Auth"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_py(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, str(ROOT / script), *map(str, args)], input=stdin,
                              capture_output=True, text=True, env=self.env).stdout

    def test_hook_notes_within_budget(self):
        for prompt in ("you missed the admin refund view again",
                       "please build a refunds feature for the admin panel"):
            out = self.run_py("hooks/on_prompt.py", stdin=json.dumps({"prompt": prompt, "cwd": str(self.repo)}))
            note = json.loads(out)["hookSpecificOutput"]["additionalContext"]
            note = note.replace(str(self.data), "~/.claude/lifecycle-guard")  # temp paths are longer
            self.assertLessEqual(len(note.encode()), HOOK_NOTE, prompt)

    def test_builder_loads_an_index_reviewer_loads_everything(self):
        builder = self.run_py("scripts/digest.py", "--context", "--domains", "payments", "--cwd", self.repo)
        full = self.run_py("scripts/digest.py", "--context", "--full", "--domains", "payments", "--cwd", self.repo)
        self.assertLessEqual(len(builder.encode()), BUILDER_CONTEXT)
        self.assertNotIn("Auth rule", builder)  # unloaded domain
        self.assertIn("…", builder)  # core/style rules as headlines
        self.assertEqual(builder.count("] Payments rule"), 10)
        self.assertNotIn("…\n", full.split("\n", 1)[1])  # reviewer: no headlines
        self.assertGreater(len(full), len(builder) * 1.5)
        ids = re.findall(r"^- \[([0-9a-f]{8})\] Core rule 3:", builder, re.M)
        fetched = self.run_py("scripts/digest.py", "--rule", ids[0])
        self.assertIn("check that thing", fetched)
        self.assertNotIn("…", fetched)

    def test_long_rules_are_flagged_at_write_time(self):
        with open(self.data / "core.md", "a") as f:
            f.write("- [ ] " + "x " * 200 + "_(learned 2026-01-01 @ shop: c)_\n")
        out = self.run_py("scripts/digest.py", "--lint-rules")
        self.assertIn("too-long", out)
        with open(self.data / "core.md", "a") as f:
            f.write("- [ ] short rule _(learned 2026-01-01 @ shop: " + "a very long story " * 8 + ")_\n")
        self.assertIn("long-cause", self.run_py("scripts/digest.py", "--lint-rules"))
        self.assertIn("too-long: 1", self.run_py("scripts/digest.py", "--audit"))
        self.assertIn("context per feature: builder", self.run_py("scripts/digest.py", "--footprint"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
