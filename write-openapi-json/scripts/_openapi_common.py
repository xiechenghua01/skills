#!/usr/bin/env python3
"""三个 OpenAPI 校验脚本共用的解析、判定与命令行输出。

只放「多个脚本都要用」的东西，不放业务规则：
- 文档读取与顶层形状校验
- 中文字符、类型数组、binary 字段等通用判定
- 统一的 Issue 结构、文本 / JSON 输出、退出码

退出码约定：0 通过 / 1 有问题 / 2 用法或文件错误。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

CHINESE = re.compile(r"[\u3400-\u9fff]")
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


class Issue:
    """一条校验结果。code 稳定可引用，message 里已包含 JSON 位置。"""

    __slots__ = ("code", "message", "severity")

    def __init__(self, code: str, message: str, severity: str = "error") -> None:
        self.code = code
        self.message = message
        self.severity = severity

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


def has_chinese(value: Any) -> bool:
    return isinstance(value, str) and bool(CHINESE.search(value))


def schema_type_is(schema: dict[str, Any], expected: str) -> bool:
    """OpenAPI 3.1 的类型可以是字符串或数组（如 ["string", "null"]）。"""
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return expected in schema_type
    return schema_type == expected


def find_binary_field(schema: Any) -> bool:
    """schema 树里是否至少声明了一个 format: binary 的文件字段。"""
    if not isinstance(schema, dict):
        return False
    if schema.get("format") == "binary":
        return True
    properties = schema.get("properties")
    if isinstance(properties, dict) and any(
        find_binary_field(child) for child in properties.values()
    ):
        return True
    if find_binary_field(schema.get("items")):
        return True
    for key in ("allOf", "anyOf", "oneOf"):
        variants = schema.get(key, [])
        if isinstance(variants, list) and any(find_binary_field(child) for child in variants):
            return True
    return False


def load_document(path: Path) -> tuple[dict[str, Any] | None, list[Issue]]:
    """读取并确认根节点是对象。失败时返回 (None, issues)。"""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [Issue("FILE-001", f"文件不存在: {path}")]
    except UnicodeDecodeError:
        return None, [Issue("FILE-002", "文件不是 UTF-8 编码，或带有 BOM")]
    except json.JSONDecodeError as exc:
        return None, [
            Issue("JSON-001", f"JSON 无效: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}")
        ]
    if not isinstance(document, dict):
        return None, [Issue("ROOT-001", "OpenAPI 文档根节点必须是对象")]
    return document, []


def iter_operations(
    document: dict[str, Any],
) -> Iterable[tuple[str, str, dict[str, Any], str]]:
    """遍历所有 HTTP 操作，产出 (路径, 方法, 操作对象, 位置描述)。"""
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            yield route, method, operation, f"paths.{route}.{method}"


def route_keys(document: dict[str, Any]) -> set[str]:
    """用于跨文件重复路径检查：返回 {"GET /a/b"} 形式的集合。"""
    return {f"{method.upper()} {route}" for route, method, _, _ in iter_operations(document)}


def run_cli(
    check_name: str,
    argv: list[str],
    validate_one: Callable[[Path], list[Issue]],
    cross_file: bool = False,
) -> int:
    """统一处理参数、输出格式与退出码。

    用法: <script> [--json] <file> [more files...]
    cross_file=True 时，多文件会额外比对路径冲突。
    """
    args = list(argv[1:])
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    if not args:
        print(f"用法: {Path(argv[0]).name} [--json] <file.openapi.json> [更多文件...]", file=sys.stderr)
        return 2

    files = [Path(a).expanduser().resolve() for a in args]
    results: list[dict[str, Any]] = []
    seen: dict[str, str] = {}

    for path in files:
        issues = validate_one(path)

        if cross_file:
            document, _ = load_document(path)
            if document is not None:
                for key in sorted(route_keys(document)):
                    if key in seen and seen[key] != str(path):
                        issues.append(
                            Issue(
                                "DUP-001",
                                f"路径冲突：{key} 同时出现在 {seen[key]} 与 {path}，"
                                f"同一接口只能在一份契约里定义",
                            )
                        )
                    else:
                        seen[key] = str(path)

        results.append(
            {
                "file": str(path),
                "ok": not any(i.severity == "error" for i in issues),
                "issues": [i.as_dict() for i in issues],
            }
        )

    ok = all(r["ok"] for r in results)

    if as_json:
        print(
            json.dumps(
                {"check": check_name, "ok": ok, "files": results},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for result in results:
            errors = [i for i in result["issues"] if i["severity"] == "error"]
            hints = [i for i in result["issues"] if i["severity"] == "hint"]
            if errors:
                # 失败信息必须落在 stdout：多数 Agent 只采集 stdout，写 stderr 等于没报错。
                print(f"{check_name} 校验失败: {result['file']}")
                for item in errors:
                    print(f"- [{item['code']}] {item['message']}")
                print(f"问题总数: {len(errors)}")
            else:
                print(f"{check_name} 校验通过: {result['file']}")
            for item in hints:
                print(f"提示: [{item['code']}] {item['message']}")

    return 0 if ok else 1
