#!/usr/bin/env python3
"""The plugin's shape: manifests, frontmatter, hook wiring, CI pinning and version consistency.
A broken command file or a forgotten CHANGELOG entry fails CI instead of shipping silently.

Run: python3 plugins/lifecycle-guard/tests/test_manifest.py
"""
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def frontmatter(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    return dict(re.findall(r"^([\w-]+):\s*(.+?)\s*$", m.group(1), re.M))


class Manifest(unittest.TestCase):
    def test_plugin_json(self):
        p = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(p["name"], "lifecycle-guard")
        self.assertRegex(p["version"], SEMVER)
        self.assertTrue(p.get("description"))
        self.assertTrue(p.get("author", {}).get("name"))

    def test_marketplace_lists_every_plugin_dir(self):
        m = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        listed = {e["name"]: e["source"] for e in m["plugins"]}
        for d in (REPO / "plugins").iterdir():
            if (d / ".claude-plugin" / "plugin.json").exists():
                self.assertIn(d.name, listed, f"{d.name} missing from marketplace.json")
                self.assertEqual(listed[d.name], f"./plugins/{d.name}")
                self.assertTrue(all(e.get("description") for e in m["plugins"]))

    def test_commands_have_descriptions(self):
        cmds = sorted((PLUGIN / "commands").glob("*.md"))
        self.assertTrue(cmds)
        for c in cmds:
            fm = frontmatter(c)
            self.assertIsNotNone(fm, f"{c.name}: no frontmatter")
            self.assertTrue(fm.get("description"), f"{c.name}: no description")

    def test_agents_have_name_description_tools(self):
        for a in (PLUGIN / "agents").glob("*.md"):
            fm = frontmatter(a)
            self.assertIsNotNone(fm, f"{a.name}: no frontmatter")
            for key in ("name", "description", "tools"):
                self.assertTrue(fm.get(key), f"{a.name}: missing {key}")
            self.assertEqual(fm["name"], a.stem)

    def test_skill_frontmatter(self):
        fm = frontmatter(PLUGIN / "skills" / "lifecycle-guard" / "SKILL.md")
        self.assertEqual(fm.get("name"), "lifecycle-guard")
        self.assertTrue(fm.get("description"))

    def test_hooks_point_at_existing_scripts(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertEqual(set(hooks), {"UserPromptSubmit", "Stop", "SessionEnd"})
        for event, groups in hooks.items():
            for g in groups:
                for h in g["hooks"]:
                    m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w/.]+\.py)", h["command"])
                    self.assertTrue(m, f"{event}: unexpected command {h['command']}")
                    self.assertTrue((PLUGIN / m.group(1)).is_file(), f"{event}: {m.group(1)} missing")
                    self.assertLessEqual(h.get("timeout", 60), 30, f"{event}: hooks must stay fast")

    def test_changelog_matches_version(self):
        version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
        top = re.search(r"^## (\d+\.\d+\.\d+)", (REPO / "CHANGELOG.md").read_text(), re.M)
        self.assertTrue(top, "CHANGELOG.md has no version entry")
        self.assertEqual(top.group(1), version, "bump CHANGELOG.md together with plugin.json")

    def test_ci_actions_pinned_to_commit_sha(self):
        for wf in (REPO / ".github" / "workflows").glob("*.yml"):
            for ref in re.findall(r"uses:\s*([^\s#]+)", wf.read_text()):
                if ref.startswith("./"):
                    continue  # local reusable workflow
                self.assertRegex(ref, r"@[0-9a-f]{40}$", f"{wf.name}: {ref} is not pinned to a commit SHA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
