#!/usr/bin/env python3
"""STE 规则校验器的单元测试套件。

用法：
    python3 ste/tests/run_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 将 ste/scripts 加入模块路径
TESTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_ste import validate_text  # noqa: E402


def test_valid_report():
    fixture_path = TESTS_DIR / "fixtures" / "valid_report.md"
    content = fixture_path.read_text(encoding="utf-8")
    diagnostics = validate_text(content)
    errors = [d for d in diagnostics if d.level == "ERROR"]
    assert not errors, f"合规文件预期零错误，实际发现: {[d.message for d in errors]}"
    print("✓ 测试通过: valid_report.md 符合 STE 规范无误报")


def test_invalid_sample():
    fixture_path = TESTS_DIR / "fixtures" / "invalid_sample.md"
    content = fixture_path.read_text(encoding="utf-8")
    diagnostics = validate_text(content)
    errors = [d for d in diagnostics if d.level == "ERROR"]
    rules_hit = {d.rule_id for d in errors}

    assert "R11" in rules_hit, "预期命中 R11 非法情态词"
    assert "R3" in rules_hit, "预期命中 R3 虚化动词"
    assert "R10" in rules_hit, "预期命中 R10 双重否定"
    assert "R17" in rules_hit, "预期命中 R17 开放式结尾"
    print(f"✓ 测试通过: invalid_sample.md 成功捕获预期违规项 (命中规则: {sorted(rules_hit)})")


def test_inline_code_immunity():
    # 反引号中的代码包含非法情态词或虚化词时不应误报
    text = "执行命令 `git commit -m '对配置进行修改，不应该报错'` 提交代码。"
    diagnostics = validate_text(text)
    errors = [d for d in diagnostics if d.level == "ERROR"]
    assert not errors, f"行内代码反引号保护失效: {[d.message for d in errors]}"
    print("✓ 测试通过: 行内代码反引号内容正确豁免检查")


def test_long_sentence_warning():
    long_desc = "在分布式系统架构设计中当多个微服务节点同时尝试向中心化注册中心发送心跳上报数据包并且由于机房网络物理抖动出现短暂丢包时系统会自动触发降级重试机制直到耗尽全部重试配额。"
    diagnostics = validate_text(long_desc)
    warnings = [d for d in diagnostics if d.rule_id == "R7"]
    assert warnings, "超长描述句预期产生 R7 告警"
    print("✓ 测试通过: 超长描述句成功触发 R7 告警")


def main() -> int:
    print("== 开始执行 STE 规则校验器测试 ==")
    try:
        test_valid_report()
        test_invalid_sample()
        test_inline_code_immunity()
        test_long_sentence_warning()
        print("\n全部测试用例通过 (4/4 PASS)")
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试断言失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 运行时异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
