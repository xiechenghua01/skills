#!/usr/bin/env python3
"""三个校验脚本的回归测试。

夹具说明：
- response-contract-good.openapi.json 结构、请求、响应三侧都应通过。
- response-contract-bad.openapi.json 响应侧埋了三类缺陷：字段说明缺失、const 与 example
  类型不一致、只有 example 没有 schema；结构与请求侧仍应通过。

每个用例断言退出码、必须出现的规则码、以及不得出现的干扰项。

用法：python3 tests/run_tests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS = SKILL_DIR / "scripts"
FIXTURES = TESTS_DIR / "fixtures"
GOOD = FIXTURES / "response-contract-good.openapi.json"
BAD = FIXTURES / "response-contract-bad.openapi.json"

CASES = [
    {
        "name": "good 通过结构校验",
        "script": "validate_openapi.py",
        "files": [GOOD],
        "exit": 0,
        "must_match": ["校验通过"],
        "must_not_match": ["校验失败"],
    },
    {
        "name": "good 通过请求契约",
        "script": "validate_openapi_request_contract.py",
        "files": [GOOD],
        "exit": 0,
        "must_match": ["校验通过"],
        "must_not_match": ["校验失败"],
    },
    {
        "name": "good 通过响应契约",
        "script": "validate_openapi_response_contract.py",
        "files": [GOOD],
        "exit": 0,
        "must_match": ["校验通过"],
        "must_not_match": ["校验失败"],
    },
    {
        "name": "bad 结构与请求侧仍应通过",
        "script": "validate_openapi.py",
        "files": [BAD],
        "exit": 0,
        "must_match": ["校验通过"],
        "must_not_match": ["校验失败"],
    },
    {
        "name": "bad 命中响应侧四类缺陷",
        "script": "validate_openapi_response_contract.py",
        "files": [BAD],
        "exit": 1,
        "must_match": ["校验失败", "RES-003", "RES-004", "RES-005", "RES-002", "问题总数: 11"],
        "must_not_match": ["RES-001"],
    },
    {
        "name": "跨文件重复路径被抓到",
        "script": "validate_openapi.py",
        "files": [GOOD, BAD],
        "exit": 1,
        "must_match": ["DUP-001", "GET /accounts/index", "POST /accounts/create"],
        "must_not_match": [],
    },
    {
        "name": "单文件不报重复路径",
        "script": "validate_openapi.py",
        "files": [GOOD],
        "exit": 0,
        "must_match": ["校验通过"],
        "must_not_match": ["DUP-001"],
    },
    {
        "name": "缺参数退出码为 2",
        "script": "validate_openapi.py",
        "files": [],
        "exit": 2,
        "must_match": ["用法"],
        "must_not_match": [],
    },
]


def run(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
    )


def check_case(case: dict) -> list[str]:
    proc = run(case["script"], [str(f) for f in case["files"]])
    out = proc.stdout + proc.stderr
    failures: list[str] = []

    if proc.returncode != case["exit"]:
        failures.append(f"退出码 {proc.returncode}，期望 {case['exit']}")
    for needle in case["must_match"]:
        if needle not in out:
            failures.append(f"输出缺少 {needle!r}")
    for needle in case["must_not_match"]:
        if needle in out:
            failures.append(f"输出不应包含 {needle!r}")
    return failures


def check_json_shape() -> list[str]:
    """--json 的字段形状一旦变化，下游的机械对比就会静默失效，所以单独守一条。"""
    failures: list[str] = []
    proc = run("validate_openapi_response_contract.py", ["--json", str(BAD)])
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ["--json 输出不是合法 JSON"]

    if payload.get("ok") is not False:
        failures.append("--json 顶层 ok 应为 false")
    files = payload.get("files") or []
    if len(files) != 1:
        failures.append("--json files 应只有一项")
    for key in ("file", "ok", "issues"):
        if key not in (files[0] if files else {}):
            failures.append(f"--json 缺少字段 {key}")
    issues = (files[0] if files else {}).get("issues", [])
    if len(issues) != 11:
        failures.append(f"--json issues 应为 11 条，实际 {len(issues)}")
    for issue in issues[:1]:
        for key in ("code", "message", "severity"):
            if key not in issue:
                failures.append(f"--json issue 缺少字段 {key}")
    if proc.returncode != 1:
        failures.append(f"--json 退出码应为 1，实际 {proc.returncode}")
    return failures


def main() -> int:
    failures = 0
    for index, case in enumerate(CASES, start=1):
        problems = check_case(case)
        label = f"{index:02d} {case['name']}"
        if problems:
            failures += 1
            print(f"[FAIL] {label}")
            for problem in problems:
                print(f"       - {problem}")
        else:
            print(f"[ OK ] {label}")

    extra = check_json_shape()
    if extra:
        failures += 1
        print("[FAIL] --json 输出结构")
        for problem in extra:
            print(f"       - {problem}")
    else:
        print("[ OK ] --json 输出结构")

    total = len(CASES) + 1
    print(f"\n{total - failures}/{total} 通过")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
