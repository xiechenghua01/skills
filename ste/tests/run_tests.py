#!/usr/bin/env python3
"""STE-ZH 校验器的回归测试。

覆盖四件事：
- 合规样例不误报；
- 违规样例按档位命中预期规则（pragmatic 只抓结构，strict 追加情态词与状态词）；
- 行内代码与代码块豁免；
- 步骤句与描述句用不同句长上限；--json 输出形状稳定。

用法：
    python3 ste/tests/run_tests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_ste import validate_text  # noqa: E402

SCRIPT = SCRIPTS_DIR / "validate_ste.py"


def errors_of(diagnostics):
    return [d for d in diagnostics if d.level == "ERROR"]


def test_valid_report():
    content = (TESTS_DIR / "fixtures" / "valid_report.md").read_text(encoding="utf-8")
    for mode in ("pragmatic", "strict"):
        found = errors_of(validate_text(content, mode))
        assert not found, f"{mode} 档对合规文件误报: {[d.message for d in found]}"
    print("✓ valid_report.md 两档均无误报")


def test_invalid_sample_pragmatic():
    content = (TESTS_DIR / "fixtures" / "invalid_sample.md").read_text(encoding="utf-8")
    hit = {d.rule_id for d in errors_of(validate_text(content, "pragmatic"))}
    assert {"R3", "R10", "R17"} <= hit, f"pragmatic 应命中 R3/R10/R17，实际 {sorted(hit)}"
    assert "R11" not in hit, "pragmatic 不应检查受控情态词"
    print(f"✓ invalid_sample.md pragmatic 档命中 {sorted(hit)}")


def test_invalid_sample_strict():
    content = (TESTS_DIR / "fixtures" / "invalid_sample.md").read_text(encoding="utf-8")
    hit = {d.rule_id for d in errors_of(validate_text(content, "strict"))}
    assert "R11" in hit, f"strict 应命中 R11 非法情态词，实际 {sorted(hit)}"
    print(f"✓ invalid_sample.md strict 档命中 {sorted(hit)}")


def test_vague_status_only_in_strict():
    text = "这次改动已经搞定，理论上没问题。"
    loose = {d.rule_id for d in errors_of(validate_text(text, "pragmatic"))}
    tight = {d.rule_id for d in errors_of(validate_text(text, "strict"))}
    assert "R19" not in loose, "pragmatic 不应检查生造状态词"
    assert "R19" in tight, f"strict 应命中 R19，实际 {sorted(tight)}"
    print("✓ 生造状态词仅在 strict 档被拦")


def test_inline_code_immunity():
    text = "执行命令 `git commit -m '对配置进行修改，不应该报错'` 提交代码。"
    found = errors_of(validate_text(text, "strict"))
    assert not found, f"行内代码豁免失效: {[d.message for d in found]}"
    print("✓ 行内代码内容正确豁免")


def test_step_and_desc_limits():
    step = "1. 在分布式系统架构设计中当多个微服务节点同时向注册中心发送心跳并且网络抖动出现丢包时触发降级重试直到耗尽配额。"
    desc = "在分布式系统架构设计中当多个微服务节点同时向注册中心发送心跳并且网络抖动出现丢包时触发降级重试直到耗尽配额。"
    step_r7 = [d for d in validate_text(step) if d.rule_id == "R7"]
    desc_r7 = [d for d in validate_text(desc) if d.rule_id == "R7"]
    assert step_r7 and "步骤句" in step_r7[0].message, "编号行应按步骤句 30 字判"
    assert desc_r7 and "描述句" in desc_r7[0].message, "普通行应按描述句 40 字判"
    print("✓ 步骤句与描述句使用不同句长上限")


def test_json_output():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(TESTS_DIR / "fixtures" / "invalid_sample.md"),
         "--mode", "strict", "--json"],
        capture_output=True, text=True,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError("--json 输出不是合法 JSON")
    assert payload["ok"] is False and payload["errors"] > 0, "strict 档应判为不通过"
    assert payload["mode"] == "strict"
    for item in payload["diagnostics"]:
        assert {"line", "rule", "level", "message", "matched", "suggestion"} <= set(item)
    assert proc.returncode == 1, f"有错误时退出码应为 1，实际 {proc.returncode}"
    print("✓ --json 输出结构完整，退出码正确")


def main() -> int:
    cases = [
        test_valid_report,
        test_invalid_sample_pragmatic,
        test_invalid_sample_strict,
        test_vague_status_only_in_strict,
        test_inline_code_immunity,
        test_step_and_desc_limits,
        test_json_output,
    ]
    print("== STE 校验器测试 ==")
    try:
        for case in cases:
            case()
    except AssertionError as exc:
        print(f"\n失败: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n运行时异常: {exc}")
        return 1
    print(f"\n全部通过 ({len(cases)}/{len(cases)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
