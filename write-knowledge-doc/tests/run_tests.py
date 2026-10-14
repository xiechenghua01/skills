#!/usr/bin/env python3
"""校验脚本的夹具测试。

每个夹具声明两类断言：
- must_match：实际输出必须包含的错误关键词（证明问题被抓到）；
- must_not_match：实际输出不得包含的关键词（证明不误报其他问题）。

valid-entry.md 由流程实测生成；文件缺失时该项记 SKIP，不算失败。

用法：python3 tests/run_tests.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
VALIDATE = TESTS_DIR.parent / "scripts" / "validate_knowledge_entry.py"

CASES = [
    {
        "fixture": "valid-entry.md",
        "exit": 0,
        "must_match": [],
        "must_not_match": ["[ERROR]"],
    },
    {
        "fixture": "invalid-frontmatter.md",
        "exit": 1,
        "must_match": ["status 取值非法", "缺少必填字段 verified", "created 应为 YYYY-MM-DD"],
        "must_not_match": ["缺少核心章节", "H1"],
    },
    {
        "fixture": "source-oriented-title.md",
        "exit": 1,
        "must_match": ["来源导向"],
        "must_not_match": ["缺少核心章节", "status", "verified"],
    },
    {
        "fixture": "missing-sections.md",
        "exit": 1,
        "must_match": ["缺少核心章节「边界与例外」", "缺少导语"],
        "must_not_match": ["来源导向", "status"],
    },
    {
        "fixture": "dead-end.md",
        "exit": 1,
        "must_match": ["Dead End"],
        "must_not_match": ["缺少核心章节", "缺少导语"],
    },
    {
        "fixture": "problem-leak.md",
        "exit": 0,
        "must_match": ["概念名", "无理由链接"],
        "must_not_match": ["Dead End", "[ERROR]"],
    },
    {
        "fixture": "h1-mismatch.md",
        "exit": 1,
        "must_match": ["H1"],
        "must_not_match": ["缺少核心章节", "来源导向"],
    },
    {
        "fixture": "bad-section-number.md",
        "exit": 1,
        "must_match": ["缺少阿拉伯数字编号"],
        "must_not_match": ["缺少核心章节", "来源导向"],
    },
    {
        "fixture": "bad-h3-number.md",
        "exit": 1,
        "must_match": ["H3", "缺少 x.y 编号"],
        "must_not_match": ["缺少核心章节", "来源导向"],
    },
    {
        "fixture": "systematic-doc.md",
        "exit": 0,
        "must_match": [],
        "must_not_match": ["[ERROR]"],
    },
    {
        "fixture": "bad-systematic.md",
        "exit": 1,
        "must_match": ["缺少中文数字编号", "编号不连续"],
        "must_not_match": ["frontmatter"],
    },
]


def run_case(case: dict) -> tuple[str, str]:
    fixture = FIXTURES_DIR / case["fixture"]
    if not fixture.is_file():
        return "SKIP", f"{case['fixture']} 尚未生成（流程实测后补齐）"
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), str(fixture)],
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    problems: list[str] = []
    if proc.returncode != case["exit"]:
        problems.append(f"退出码 {proc.returncode}，期望 {case['exit']}")
    for keyword in case["must_match"]:
        if keyword not in output:
            problems.append(f"未命中预期错误「{keyword}」")
    for keyword in case["must_not_match"]:
        if keyword in output:
            problems.append(f"误报了不应出现的内容「{keyword}」")
    if problems:
        return "FAIL", "；".join(problems)
    return "PASS", f"退出码 {proc.returncode}，断言 {len(case['must_match'])} 条全部命中"


def main() -> int:
    results = [(case["fixture"], *run_case(case)) for case in CASES]
    width = max(len(name) for name, _, _ in results)
    for name, status, detail in results:
        print(f"  {status:<5} {name:<{width}}  {detail}")
    failed = [r for r in results if r[1] == "FAIL"]
    skipped = [r for r in results if r[1] == "SKIP"]
    print(f"\n{len(results) - len(failed) - len(skipped)} 项通过，{len(failed)} 项失败，{len(skipped)} 项跳过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
