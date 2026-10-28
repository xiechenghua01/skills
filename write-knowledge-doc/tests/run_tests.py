#!/usr/bin/env python3
"""校验脚本的夹具测试。

每个夹具声明四类断言：
- exit：进程退出码（0 通过 / 1 未通过 / 2 参数或文件错误）；
- must_match：输出里必须出现的关键词（证明问题被抓到）；
- must_not_match：输出里不得出现的关键词（证明没有误报其他问题）；
- args：附加命令行参数（如 --stage skeleton）。

另外每次都跑一遍 --json，校验结构化输出的字段形状，防止改动破坏下游消费。

用法：python3 tests/run_tests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
VALIDATE = TESTS_DIR.parent / "scripts" / "validate_knowledge_doc.py"

CASES = [
    {
        "fixture": "valid-entry.md",
        "exit": 0,
        "must_match": ["通过"],
        "must_not_match": ["[ERROR]", "[WARN]"],
    },
    {
        "fixture": "first-entry-exempt.md",
        "exit": 0,
        "must_match": ["通过"],
        "must_not_match": ["[ERROR]", "Dead End"],
        "note": "首条目豁免句应被识别，不报 Dead End",
    },
    {
        "fixture": "missing-kind.md",
        "exit": 1,
        "must_match": ["缺少必填字段 kind"],
        "must_not_match": ["SEC-", "LEAD-", "H1-"],
        "note": "缺 kind 时仍按 entry 继续查结构，但不误报其他规则",
    },
    {
        "fixture": "appended-gap.md",
        "exit": 1,
        "must_match": ["追加章节编号不连续"],
        "must_not_match": ["SEC-MISSING", "TITLE-SOURCE"],
        "note": "五章后从 6 直接跳到 8",
    },
    {
        "fixture": "date-order.md",
        "exit": 1,
        "must_match": ["早于 created"],
        "must_not_match": ["SEC-", "H1-"],
    },
    {
        "fixture": "vague-scope.md",
        "exit": 0,
        "must_match": ["无法比对的范围词"],
        "must_not_match": ["[ERROR]"],
        "note": "applies_to 写「最新版」是 WARN：无法比对的范围等于没写",
    },
    {
        "fixture": "invalid-frontmatter.md",
        "exit": 1,
        "must_match": ["status 取值非法", "缺少必填字段 verified", "created 应为 YYYY-MM-DD"],
        "must_not_match": ["SEC-MISSING", "H1-"],
    },
    {
        "fixture": "source-oriented-title.md",
        "exit": 1,
        "must_match": ["来源导向"],
        "must_not_match": ["SEC-MISSING", "status"],
    },
    {
        "fixture": "missing-sections.md",
        "exit": 1,
        "must_match": ["缺少核心章节「边界与例外」"],
        "must_not_match": ["TITLE-SOURCE"],
    },
    {
        "fixture": "dead-end.md",
        "exit": 1,
        "must_match": ["既没有链接也没有列表项"],
        "must_not_match": ["SEC-MISSING", "H1-"],
    },
    {
        "fixture": "h1-mismatch.md",
        "exit": 1,
        "must_match": ["与 frontmatter title", "不一致"],
        "must_not_match": ["SEC-MISSING"],
    },
    {
        "fixture": "bad-section-number.md",
        "exit": 1,
        "must_match": ["核心章节「它解决什么问题」缺少阿拉伯数字编号"],
        "must_not_match": ["H3-"],
    },
    {
        "fixture": "bad-h3-number.md",
        "exit": 1,
        "must_match": ["H3", "缺少 x.y 编号"],
        "must_not_match": ["SEC-MISSING"],
    },
    {
        "fixture": "problem-leak.md",
        "exit": 0,
        "must_match": ["出现了概念名"],
        "must_not_match": ["[ERROR]"],
        "note": "概念名泄漏是 WARN，不阻断",
    },
    {
        "fixture": "systematic-doc.md",
        "exit": 0,
        "must_match": ["通过"],
        "must_not_match": ["[ERROR]"],
    },
    {
        "fixture": "bad-systematic.md",
        "exit": 1,
        "must_match": ["缺少中文数字编号", "H2 编号不连续"],
        "must_not_match": ["SEC-MISSING"],
    },
    {
        "fixture": "skeleton-stage.md",
        "exit": 1,
        "must_match": ["既没有链接也没有列表项"],
        "must_not_match": ["TITLE-SOURCE"],
        "note": "骨架稿在 draft 阶段应报内容缺口",
    },
    {
        "fixture": "skeleton-stage.md",
        "exit": 0,
        "args": ["--stage", "skeleton"],
        "must_match": ["通过"],
        "must_not_match": ["[ERROR]", "[WARN]"],
        "note": "同一份骨架稿在 skeleton 阶段只查结构契约",
    },
]


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True,
        text=True,
    )


def check_json_shape(args: list[str]) -> list[str]:
    proc = run([*args, "--json"])
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ["--json 输出不是合法 JSON"]

    problems: list[str] = []
    for key in ("stage", "files"):
        if key not in payload:
            problems.append(f"--json 缺少顶层字段 {key}")
    files = payload.get("files") or [{}]
    entry = files[0]
    for key in ("file", "ok", "errors", "warnings", "findings"):
        if key not in entry:
            problems.append(f"--json 缺少字段 {key}")
    for finding in entry.get("findings", []):
        missing = [k for k in ("level", "code", "line", "message", "fix") if k not in finding]
        if missing:
            problems.append(f"--json finding 缺少字段 {'/'.join(missing)}")
            break
    return problems


def check_case(case: dict) -> list[str]:
    fixture = FIXTURES_DIR / case["fixture"]
    if not fixture.is_file():
        return [f"夹具不存在：{fixture}"]

    args = [str(fixture), *case.get("args", [])]
    proc = run(args)
    out = proc.stdout + proc.stderr
    failures: list[str] = []

    if proc.returncode != case["exit"]:
        failures.append(f"退出码 {proc.returncode}，期望 {case['exit']}")
    for needle in case.get("must_match", []):
        if needle not in out:
            failures.append(f"输出缺少 {needle!r}")
    for needle in case.get("must_not_match", []):
        if needle in out:
            failures.append(f"输出不应包含 {needle!r}")
    failures.extend(check_json_shape(args))
    return failures


def main() -> int:
    if not VALIDATE.is_file():
        print(f"校验脚本不存在：{VALIDATE}")
        return 2

    failed = 0
    for i, case in enumerate(CASES, start=1):
        label = case["fixture"]
        if case.get("args"):
            label += " " + " ".join(case["args"])
        failures = check_case(case)
        if failures:
            failed += 1
            print(f"[FAIL] {i:02d} {label}")
            for f in failures:
                print(f"       - {f}")
        else:
            print(f"[ OK ] {i:02d} {label}")

    print(f"\n{len(CASES) - failed}/{len(CASES)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
