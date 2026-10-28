#!/usr/bin/env python3
"""校验响应侧契约：200 响应的中文说明、业务含义、const 与示例一致性、schema 完整性。

用法:
    python3 validate_openapi_response_contract.py [--json] <file.openapi.json> [更多文件...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from _openapi_common import Issue, has_chinese, iter_operations, load_document, run_cli

COMBINATOR_KEYS = ("oneOf", "anyOf", "allOf")
# 只重复字段名或这些通用词的说明，等于没写业务含义。
GENERIC_WORDS = (
    "字段", "参数", "名称", "类型", "数据", "返回", "响应", "信息",
    "内容", "对象", "数组", "列表", "字符串", "整数", "数字", "数值", "枚举", "布尔",
)


def description_has_business_meaning(description: str) -> bool:
    """去掉通用词后仍剩至少两个字，才算说明了业务含义。"""
    remaining = re.sub(r"[^\u3400-\u9fff]", "", description)
    for word in GENERIC_WORDS:
        remaining = remaining.replace(word, "")
    return len(remaining) >= 2


def check_description(schema: dict[str, Any], location: str) -> list[Issue]:
    description = schema.get("description")
    if not has_chinese(description):
        return [Issue("RES-003", f"{location} 缺少中文 description")]
    if not description_has_business_meaning(description):
        return [
            Issue(
                "RES-004",
                f"{location} 的 description 缺少业务含义，不能只重复字段名或通用词，"
                "应说明单位、枚举、可空等信息",
            )
        ]
    return []


def check_const_example(schema: dict[str, Any], location: str) -> list[Issue]:
    if "const" not in schema or "example" not in schema:
        return []
    const_value = schema["const"]
    example_value = schema["example"]
    if type(const_value) is not type(example_value) or const_value != example_value:
        return [
            Issue(
                "RES-005",
                f"{location} 的 example 与 const 不一致（const: {const_value!r}，"
                f"example: {example_value!r}），类型和值必须完全一致",
            )
        ]
    return []


def check_response_schema(schema: Any, location: str) -> list[Issue]:
    if not isinstance(schema, dict):
        return [Issue("RES-007", f"{location} 必须是 schema 对象")]

    issues = check_const_example(schema, location)

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            child_location = f"{location}.properties.{name}"
            if not isinstance(child, dict):
                issues.append(Issue("RES-007", f"{child_location} 必须是对象"))
                continue
            issues.extend(check_description(child, child_location))
            issues.extend(check_response_schema(child, child_location))

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            issues.append(
                Issue("RES-006", f"{location}.items 不能是空结构，必须展开元素字段或说明动态结构")
            )
        else:
            issues.extend(check_description(items, f"{location}.items"))
            issues.extend(check_response_schema(items, f"{location}.items"))

    for key in COMBINATOR_KEYS:
        variants = schema.get(key, [])
        if not isinstance(variants, list):
            issues.append(Issue("RES-008", f"{location}.{key} 必须是数组"))
            continue
        for index, child in enumerate(variants):
            branch_location = f"{location}.{key}[{index}]"
            if not isinstance(child, dict):
                issues.append(Issue("RES-007", f"{branch_location} 必须是对象"))
                continue
            issues.extend(check_description(child, branch_location))
            issues.extend(check_response_schema(child, branch_location))

    return issues


def check_media_type(media: Any, location: str) -> list[Issue]:
    if not isinstance(media, dict):
        return [Issue("RES-007", f"{location} 必须是对象")]
    schema = media.get("schema")
    if schema is None:
        return [Issue("RES-002", f"{location} 缺少内联 schema，不能只写 example 代替结构定义")]
    if not isinstance(schema, dict):
        return [Issue("RES-007", f"{location}.schema 必须是对象")]
    return check_response_schema(schema, f"{location}.schema")


def validate(path: Path) -> list[Issue]:
    document, load_issues = load_document(path)
    if document is None:
        return load_issues

    issues: list[Issue] = []
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return [Issue("PATH-001", "paths 必须是对象")]

    response_count = 0
    for _, _, operation, operation_location in iter_operations(document):
        responses = operation.get("responses")
        response = responses.get("200") if isinstance(responses, dict) else None
        if not isinstance(response, dict):
            continue

        response_count += 1
        content = response.get("content")
        if not isinstance(content, dict) or not content:
            issues.append(Issue("RES-001", f"{operation_location}.responses.200 缺少 content"))
            continue
        for media_type, media in content.items():
            issues.extend(
                check_media_type(media, f"{operation_location}.responses.200.content.{media_type}")
            )

    if response_count == 0:
        issues.append(Issue("RES-009", "paths 中没有可审计的 200 响应"))

    return issues


def main() -> int:
    return run_cli("OpenAPI 响应契约", sys.argv, validate)


if __name__ == "__main__":
    raise SystemExit(main())
