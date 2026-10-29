"""直接导入交付检查器，用临时技能包验证只读行为及 CLI 契约。"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_skill.py"
SPEC = importlib.util.spec_from_file_location("validate_skill_under_test", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ValidateSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.skill = self.base / "sample-skill"
        self.skill.mkdir()
        self.document()

    def write(self, relative: str, content: str = "") -> Path:
        path = self.skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def document(self, body: str = "# 示例技能\n", header: str | None = None) -> Path:
        header = header if header is not None else 'name: sample-skill\ndescription: "测试技能：只读检查 # 描述"\n'
        return self.write("SKILL.md", f"---\n{header}---\n{body}")

    def check(self, strict: bool = False):
        return VALIDATOR.validate_skill(self.skill, strict=strict)

    def codes(self, report) -> set[str]:
        return {finding.code for finding in report.findings}

    def cli(self, *args: str):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", env=environment,
                              timeout=10, check=False)

    def test_normal_minimal_header_without_repository_profile(self):
        report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertTrue(report.complete)
        self.assertEqual(report.findings, [])
        self.assertEqual(report.scanned, [str(self.skill / "SKILL.md")])

    def test_cli_json_contract_and_zero_exit(self):
        result = self.cli(self.skill, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["complete"])
        self.assertEqual((payload["error"], payload["warn"], payload["unsupported"]), (0, 0, 0))
        self.assertTrue(any("§" in item for item in payload["coverage"]))
        self.assertTrue(any("不是完整" in item for item in payload["coverage"]))

    def test_cli_plain_output_is_chinese_and_contains_boundary(self):
        result = self.cli(self.skill)
        self.assertEqual(result.returncode, 0)
        self.assertIn("通过：扫描 1 个", result.stdout)
        self.assertIn("覆盖边界", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_missing_skill_file_is_error_not_argument_error(self):
        (self.skill / "SKILL.md").unlink()
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertTrue(report.complete)
        self.assertIn("SKILL_MISSING", self.codes(report))

    def test_missing_and_empty_required_header_fields(self):
        self.document(header='name: sample-skill\n')
        self.assertIn("FRONTMATTER_REQUIRED", self.codes(self.check()))
        self.document(header='name: sample-skill\ndescription: "  "\n')
        self.assertEqual(self.check().exit_code, 1)

    def test_directory_name_mismatch(self):
        self.document(header='name: another-skill\ndescription: "测试"\n')
        self.assertIn("NAME_DIRECTORY_MISMATCH", self.codes(self.check()))

    def test_quoted_scalars_and_comments(self):
        self.document(header='name: "sample-skill" # 合法注释\ndescription: \'测试 \'\'引用\'\'：值 # 内容\' # 注释\n')
        self.assertEqual(self.check().exit_code, 0)
        self.document(header='name: sample-skill\ndescription: "转义 \\"中文\\" \\u4e2d"\n')
        self.assertEqual(self.check().exit_code, 0)

    def test_invalid_quoted_scalar(self):
        self.document(header='name: sample-skill\ndescription: "错误 "引用" 内容"\n')
        report = self.check()
        self.assertIn("FRONTMATTER_SCALAR_INVALID", self.codes(report))
        self.assertEqual(report.exit_code, 1)

    def test_duplicate_header_fields(self):
        self.document(header='name: sample-skill\ndescription: "第一处"\ndescription: "第二处"\n')
        report = self.check()
        finding = next(f for f in report.findings if f.code == "FRONTMATTER_DUPLICATE")
        self.assertEqual(finding.line, 4)
        self.assertIn("第 3 行", finding.message)
        self.assertEqual(report.exit_code, 1)

    def test_block_scalar_is_unsupported_not_malformed_or_passed(self):
        self.document(header='name: sample-skill\ndescription: |-\n  合法多行\n  描述\n')
        report = self.check()
        self.assertFalse(report.complete)
        self.assertEqual(report.exit_code, 2)
        self.assertTrue(all(f.level == "UNSUPPORTED" for f in report.findings))
        self.assertIn("FRONTMATTER_UNSUPPORTED", self.codes(report))
        result = self.cli(self.skill, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], 0)
        self.assertEqual(payload["warn"], 0)
        self.assertGreater(payload["unsupported"], 0)
        self.assertEqual(result.stderr, "")

    def test_complex_yaml_is_explicitly_unchecked(self):
        self.document(header='name: sample-skill\ndescription: "测试"\nmetadata: {one: two}\n')
        report = self.check()
        self.assertEqual(report.exit_code, 2)
        self.assertIn("FRONTMATTER_UNSUPPORTED", self.codes(report))
        self.assertNotIn("FRONTMATTER_SCALAR_INVALID", self.codes(report))

    def test_missing_frontmatter_and_closing_marker(self):
        self.write("SKILL.md", "# 没有头部\n")
        self.assertIn("FRONTMATTER_MISSING", self.codes(self.check()))
        self.write("SKILL.md", '---\nname: sample-skill\ndescription: "测试"\n')
        self.assertIn("FRONTMATTER_UNCLOSED", self.codes(self.check()))

    def test_nested_relative_links_resolve_from_referencing_parent(self):
        self.document("[指南](references/nested/guide.md)\n")
        self.write("references/nested/guide.md", "[返回](../../SKILL.md)\n[同级](peer.md)\n[上级](../overview.md)\n")
        self.write("references/nested/peer.md", "# 同级\n")
        self.write("references/overview.md", "# 概览\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_broken_link_json_finding_and_exit_one(self):
        self.document("# 示例\n[缺失](references/missing.md)\n")
        result = self.cli(self.skill, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["complete"])
        self.assertEqual(result.stderr, "")
        finding = payload["findings"][0]
        self.assertEqual(finding["code"], "LINK_MISSING")
        self.assertEqual(finding["line"], 6)
        self.assertEqual(finding["path"], str(self.skill / "SKILL.md"))
        self.assertEqual(set(finding), {"level", "code", "path", "line", "message", "fix"})
        self.assertTrue(finding["fix"])

    def test_chinese_anchors_percent_encoding_and_duplicate_suffix(self):
        self.document("# 中文 标题！\n# 中文 标题！\n# Hello, World!\n"
                      "[中文](#中文-标题)\n[重复](#中文-标题-1)\n"
                      "[编码](#%E4%B8%AD%E6%96%87-%E6%A0%87%E9%A2%98)\n"
                      "[英文](#hello-world)\n[空](#)\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_duplicate_anchor_collision_and_setext_heading(self):
        self.document("# 相同\n# 相同-1\n# 相同\n二级 标题\n----\n"
                      "[冲突后缀](#相同-2)\n[下划线标题](#二级-标题)\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_anchor_missing_in_referenced_file(self):
        self.document("[指南](references/guide.md#不存在)\n")
        self.write("references/guide.md", "# 实际标题\n")
        self.assertIn("ANCHOR_MISSING", self.codes(self.check()))

    def test_fenced_templates_are_not_links_or_script_references(self):
        self.document("```markdown\n[模板](missing.md)\n` scripts/missing.py `\n# 模板标题\n```\n"
                      "~~~~python\n[模板][undefined]\n` scripts/another.py `\n~~~~\n"
                      "[有效](#真实标题)\n# 真实标题\n")
        report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertNotIn("模板标题", VALIDATOR.headings(VALIDATOR.without_fences(
            (self.skill / "SKILL.md").read_text(encoding="utf-8"), self.skill / "SKILL.md", report)))

    def test_inline_code_fake_links_and_escaped_brackets_ignored(self):
        self.document("`[伪链接](missing.md)`\n`` [伪链接][missing] ``\n"
                      "\\[不是链接](missing.md)\n<!-- [注释](missing.md) -->\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_inline_code_does_not_pair_across_blank_paragraph(self):
        self.document("第一段 `未闭合\n\n[真实断链](missing.md)\n\n另一段 `结尾\n")
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertEqual([f.code for f in report.findings], ["LINK_MISSING"])
        self.assertEqual(report.findings[0].line, 7)

    def test_inline_code_can_span_nonblank_lines(self):
        self.document("`跨行\n[伪链接](missing.md)\n代码`\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_fence_inside_html_comment_does_not_hide_real_link(self):
        self.document("<!--\n```markdown\n-->\n[真实断链](missing.md)\n")
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertEqual([f.code for f in report.findings], ["LINK_MISSING"])
        self.assertEqual(report.findings[0].line, 8)

    def test_html_comment_inside_fence_does_not_hide_real_link(self):
        for opening in ("```markdown", "```markdown <!--"):
            with self.subTest(opening=opening):
                self.document(f"{opening}\n<!--\n```\n[真实断链](missing.md)\n")
                report = self.check()
                self.assertEqual(report.exit_code, 1)
                self.assertEqual([f.code for f in report.findings], ["LINK_MISSING"])
                self.assertEqual(report.findings[0].line, 8)

    def test_reference_style_heading_slug_discards_reference_label(self):
        self.document("# [中文标题][guide]\n# [中文标题][]\n"
                      "[首个](#中文标题)\n[重复](#中文标题-1)\n"
                      "[guide]: SKILL.md\n[中文标题]: SKILL.md\n")
        report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertNotIn("ANCHOR_MISSING", self.codes(report))

    def test_explicit_script_missing_and_not_shell_command_or_template(self):
        self.document("`scripts/missing.py`\n`python3 scripts/command.py`\n"
                      "`scripts/<template>.py`\n`scripts/*.py`\n`references/missing.py`\n")
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertEqual([f.code for f in report.findings], ["SCRIPT_MISSING"])
        self.assertEqual(report.findings[0].line, 5)

    def test_script_ellipsis_templates_ignored_but_extensionless_path_checked(self):
        self.document("`scripts/...`\n`scripts/…`\n`scripts/.../tool.py`\n`scripts/tool`\n")
        self.write("scripts/tool", "不得执行\n")
        self.assertEqual(self.check().exit_code, 0)
        (self.skill / "scripts" / "tool").unlink()
        report = self.check()
        self.assertEqual([f.code for f in report.findings], ["SCRIPT_MISSING"])
        self.assertEqual(report.findings[0].line, 8)

    def test_script_file_is_not_executed_or_modified(self):
        marker = self.skill / "executed"
        script = self.write("scripts/tool.py", f'raise RuntimeError("不得执行")\nopen({str(marker)!r}, "w").write("坏")\n')
        self.document("`scripts/tool.py`\n")
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.skill.rglob("*") if path.is_file()}
        with mock.patch.object(VALIDATOR.os, "system", side_effect=AssertionError("不能执行")):
            report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertFalse(marker.exists())
        for path, snapshot in before.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), snapshot)
        self.assertNotIn(str(script), report.scanned)

    def test_reference_style_full_collapsed_shortcut_and_image(self):
        self.document("[指南][Guide]\n[guide][]\n[GUIDE]\n![图](assets/image.svg)\n"
                      "[Guide]: <references/guide.md> \"说明\"\n")
        self.write("references/guide.md", "# 指南\n")
        self.write("assets/image.svg", "<svg/>\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_undefined_reference_style_link(self):
        self.document("[指南][not-defined]\n")
        report = self.check()
        self.assertIn("REFERENCE_UNDEFINED", self.codes(report))
        self.assertEqual(report.exit_code, 1)

    def test_duplicate_reference_warning_and_strict_cli(self):
        self.document("[使用][guide]\n[guide]: SKILL.md\n[guide]: missing.md\n")
        report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertTrue(report.complete)
        self.assertIn("REFERENCE_DUPLICATE", self.codes(report))
        self.assertEqual(self.check(strict=True).exit_code, 1)
        result = self.cli(self.skill, "--strict", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["error"], 0)
        self.assertEqual(payload["warn"], 1)
        self.assertTrue(payload["complete"])

    def test_spaces_balanced_parentheses_and_query_in_local_target(self):
        self.write("references/含 空格(示例).md", "# 内容\n")
        self.document("[尖括号](<references/含 空格(示例).md> '说明')\n"
                      "[编码](references/含%20空格(示例).md?view=1#内容)\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_external_links_ignored_without_network(self):
        self.document("[网页](https://invalid.example.test/x#y)\n[邮件](mailto:test@example.test)\n"
                      "[协议相对](//invalid.example.test/x)\n[其他协议](custom:thing)\n")
        with mock.patch("socket.socket", side_effect=AssertionError("不能联网")):
            self.assertEqual(self.check().exit_code, 0)

    def test_lexical_and_encoded_reference_escape_reported(self):
        (self.base / "outside.md").write_text("# 外部\n", encoding="utf-8")
        self.document("[越界](../outside.md)\n[编码越界](%2e%2e/outside.md)\n")
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertEqual([f.code for f in report.findings], ["PATH_OUTSIDE_SKILL", "PATH_OUTSIDE_SKILL"])
        self.assertNotIn(str(self.base / "outside.md"), report.scanned)

    def test_external_symlink_directory_and_file_never_read_or_walked(self):
        outside = self.base / "external"
        outside.mkdir()
        forbidden = outside / "secret.md"
        forbidden.write_text("[不能读](missing.md)\n", encoding="utf-8")
        (self.skill / "linked-dir").symlink_to(outside, target_is_directory=True)
        (self.skill / "linked.md").symlink_to(forbidden)
        self.document("[越界目录链接](linked-dir/secret.md)\n")
        original = Path.read_text

        def guarded(path, *args, **kwargs):
            if path.resolve().is_relative_to(outside):
                self.fail("不能读取包外符号链接目标")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", guarded):
            report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertIn("PATH_OUTSIDE_SKILL", self.codes(report))
        self.assertNotIn("LINK_MISSING", self.codes(report))
        self.assertEqual(report.scanned, [str(self.skill / "SKILL.md")])

    def test_internal_symlink_allowed_without_recursion_loop(self):
        self.write("references/guide.md", "# 指南\n")
        (self.skill / "alias.md").symlink_to(self.skill / "references" / "guide.md")
        (self.skill / "references" / "loop").symlink_to(self.skill, target_is_directory=True)
        self.document("[别名](alias.md#指南)\n")
        self.assertEqual(self.check().exit_code, 0)

    def test_read_error_is_json_error_exit_two_and_stderr_diagnostic(self):
        path = self.skill / "references" / "bad.md"
        self.write("references/bad.md", "# 内容\n")
        original = Path.read_text

        def denied(candidate, *args, **kwargs):
            if candidate == path:
                raise PermissionError("拒绝读取")
            return original(candidate, *args, **kwargs)

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(Path, "read_text", denied), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = VALIDATOR.main([str(self.skill), "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertFalse(payload["complete"])
        self.assertIn("READ_ERROR", {item["code"] for item in payload["findings"]})
        self.assertIn("拒绝读取", stderr.getvalue())

    def test_invalid_utf8_is_read_error_and_cli_exit_two(self):
        self.write("bad.md").write_bytes(b"\xff\xfe")
        result = self.cli(self.skill, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(payload["complete"])
        self.assertIn("READ_ERROR", {item["code"] for item in payload["findings"]})
        self.assertIn("读取错误", result.stderr)

    def test_single_file_and_missing_directory_are_argument_errors(self):
        for argument in (self.skill / "SKILL.md", self.base / "missing"):
            with self.subTest(argument=argument):
                result = self.cli(argument, "--json")
                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(payload["ok"])
                self.assertFalse(payload["complete"])
                self.assertEqual(payload["findings"][0]["code"], "ARGUMENT_ERROR")
                self.assertIn("参数", result.stderr)

    def test_missing_and_unknown_cli_arguments_exit_two(self):
        for arguments in (("--json",), (str(self.skill), "--json", "--unknown")):
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["complete"])
                self.assertIn("参数", result.stderr)

    def test_complex_markdown_is_recorded_as_unchecked(self):
        self.document('[复杂](<missing.md> "标题" extra)\n[ref]:\n  missing.md\n')
        report = self.check()
        self.assertFalse(report.complete)
        self.assertEqual(report.exit_code, 2)
        self.assertIn("LINK_UNSUPPORTED", self.codes(report))
        self.assertNotIn("LINK_MISSING", self.codes(report))

    def test_non_markdown_anchor_is_unchecked_not_warning(self):
        self.write("assets/page.html", '<h1 id="标题">标题</h1>')
        self.document("[网页锚点](assets/page.html#标题)\n")
        report = self.check()
        self.assertEqual(report.exit_code, 2)
        self.assertEqual(report.to_dict()["warn"], 0)
        self.assertIn("ANCHOR_UNSUPPORTED", self.codes(report))

    def test_only_current_skill_markdown_is_scanned(self):
        sibling = self.base / "another-skill"
        sibling.mkdir()
        (sibling / "SKILL.md").write_text("[断链](missing.md)", encoding="utf-8")
        self.write("assets/template.txt", "[模板](missing.md)")
        self.write("references/unlinked.md", "[仍需检查](missing.md)")
        report = self.check()
        self.assertEqual(report.exit_code, 1)
        self.assertEqual(len(report.scanned), 2)
        self.assertEqual([f.path for f in report.findings], [str(self.skill / "references" / "unlinked.md")])

    def test_unclosed_fence_is_warning_with_complete_scope(self):
        self.document("```markdown\n[模板](missing.md)\n")
        report = self.check()
        self.assertEqual(report.exit_code, 0)
        self.assertTrue(report.complete)
        self.assertEqual([f.code for f in report.findings], ["FENCE_UNCLOSED"])
        self.assertEqual(self.check(strict=True).exit_code, 1)


if __name__ == "__main__":
    unittest.main()
