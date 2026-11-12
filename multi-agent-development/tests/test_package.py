#!/usr/bin/env python3
"""只读检查技能包与场景用例结构；不执行模型、插件、自动触发或交付流程。"""
from __future__ import annotations

import json
import re
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_required_documents_exist(self):
        for name in (
            "SKILL.md",
            "references/model-routing.md",
            "references/async-runs.md",
            "references/acceptance.md",
            "agents/openai.yaml",
            "tests/cases.json",
        ):
            with self.subTest(path=name):
                self.assertTrue((ROOT / name).is_file())

    def test_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        parts = text.split("---\n", 2)
        self.assertEqual(len(parts), 3)
        fields = [line.split(":", 1) for line in parts[1].splitlines() if line]
        self.assertEqual(
            [key for key, _ in fields],
            ["name", "display_name_zh", "display_name_en", "description", "description_en", "version"],
        )
        values = {key: value.strip() for key, value in fields}
        self.assertEqual(values["name"], ROOT.name)
        for key in ("description", "description_en"):
            self.assertIsInstance(json.loads(values[key]), str)
            self.assertTrue(json.loads(values[key]).strip())
        self.assertRegex(values["version"], r"^v\d{8}$")
        datetime.strptime(values["version"], "v%Y%m%d")

    def test_local_markdown_links(self):
        for document in ROOT.rglob("*.md"):
            text = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", text):
                parsed = urlsplit(target.strip().strip("<>"))
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(document=str(document.relative_to(ROOT)), target=target):
                    path = (document.parent / unquote(parsed.path)).resolve()
                    self.assertTrue(path.is_relative_to(ROOT), "相对链接越出技能包")
                    self.assertTrue(path.is_file(), "链接目标不存在")

    def test_scenario_fixture_structure(self):
        data = json.loads((ROOT / "tests/cases.json").read_text(encoding="utf-8"))
        self.assertTrue(data["scope"])
        self.assertTrue(data["cases"])
        ids = []
        for case in data["cases"]:
            with self.subTest(case=case.get("id")):
                ids.append(case["id"])
                for key in ("requirement", "prompt"):
                    self.assertTrue(case[key].strip())
                self.assertIsInstance(case["fixtures"], dict)
                for key in ("expected_actions", "forbidden_actions", "checks"):
                    self.assertIsInstance(case[key], list)
                    self.assertTrue(case[key])
                    self.assertTrue(all(isinstance(item, str) and item.strip() for item in case[key]))
                self.assertIn(case["verification"], {"not_run", "passed", "failed", "blocked"})
        self.assertEqual(len(ids), len(set(ids)), "用例 ID 重复")

    def test_default_prompt(self):
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn(f"${ROOT.name}", text)
        self.assertNotRegex(text, r"allow_implicit_invocation:\s*false")

    def test_manifest_if_distributed(self):
        path = ROOT / ".zcode-plugin/plugin.json"
        if not path.exists():
            self.skipTest("DSH 市场分发不携带 ZCode 隐藏清单")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], ROOT.name)
        self.assertEqual(data["skills"], ".")
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
