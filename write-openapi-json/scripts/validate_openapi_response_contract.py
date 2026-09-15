#!/usr/bin/env python3
"""Validate 200-response field metadata for repository OpenAPI files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


CHINESE = re.compile(r"[\u3400-\u9fff]")
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
COMBINATOR_KEYS = ("oneOf", "anyOf", "allOf")
GENERIC_WORDS = (
    "字段",
    "参数",
    "名称",
    "类型",
    "数据",
    "返回",
    "响应",
    "信息",
    "内容",
    "对象",
    "数组",
    "列表",
    "字符串",
    "整数",
    "数字",
    "数值",
    "枚举",
    "布尔",
)


def has_chinese(value: Any) -> bool:
    return isinstance(value, str) and bool(CHINESE.search(value))


def description_has_business_meaning(description: str) -> bool:
    """Reject descriptions that only echo the field name plus generic words."""
    remaining = re.sub(r"[^\u3400-\u9fff]", "", description)
    for word in GENERIC_WORDS:
        remaining = remaining.replace(word, "")
    return len(remaining) >= 2


def check_description(schema: dict[str, Any], location: str, errors: list[str]) -> None:
    description = schema.get("description")
    if not has_chinese(description):
        errors.append(f"{location} 缺少中文 description")
    elif not description_has_business_meaning(description):
        errors.append(
            f"{location} 的 description 缺少业务含义，不能只重复字段名或通用词，"
            f"应说明单位、枚举、可空等信息"
        )


def check_const_example(schema: dict[str, Any], location: str, errors: list[str]) -> None:
    if "const" not in schema or "example" not in schema:
        return
    const_value = schema["const"]
    example_value = schema["example"]
    if type(const_value) is not type(example_value) or const_value != example_value:
        errors.append(
            f"{location} 的 example 与 const 不一致"
            f"（const: {const_value!r}，example: {example_value!r}），"
            f"类型和值必须完全一致"
        )


def check_response_schema(schema: Any, location: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        errors.append(f"{location} 必须是 schema 对象")
        return

    check_const_example(schema, location, errors)

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            child_location = f"{location}.properties.{name}"
            if not isinstance(child, dict):
                errors.append(f"{child_location} 必须是对象")
                continue
            check_description(child, child_location, errors)
            check_response_schema(child, child_location, errors)

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            errors.append(
                f"{location}.items 不能是空结构，必须展开元素字段或说明动态结构"
            )
        else:
            check_description(items, f"{location}.items", errors)
            check_response_schema(items, f"{location}.items", errors)

    for key in COMBINATOR_KEYS:
        variants = schema.get(key, [])
        if not isinstance(variants, list):
            errors.append(f"{location}.{key} 必须是数组")
            continue
        for index, child in enumerate(variants):
            branch_location = f"{location}.{key}[{index}]"
            if not isinstance(child, dict):
                errors.append(f"{branch_location} 必须是对象")
                continue
            check_description(child, branch_location, errors)
            check_response_schema(child, branch_location, errors)


def check_media_type(media: Any, location: str, errors: list[str]) -> None:
    if not isinstance(media, dict):
        errors.append(f"{location} 必须是对象")
        return
    schema = media.get("schema")
    if schema is None:
        errors.append(f"{location} 缺少内联 schema，不能只写 example 代替结构定义")
        return
    if not isinstance(schema, dict):
        errors.append(f"{location}.schema 必须是对象")
        return
    check_response_schema(schema, f"{location}.schema", errors)


def validate(path: Path) -> list[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"文件不存在: {path}"]
    except json.JSONDecodeError as exc:
        return [f"JSON 无效: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}"]

    if not isinstance(document, dict):
        return ["OpenAPI 文档根节点必须是对象"]

    errors: list[str] = []
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return ["paths 必须是对象"]

    response_count = 0
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            response = responses.get("200") if isinstance(responses, dict) else None
            if not isinstance(response, dict):
                continue

            response_count += 1
            content = response.get("content")
            if not isinstance(content, dict) or not content:
                errors.append(
                    f"paths.{route}.{method}.responses.200 缺少 content"
                )
                continue
            for media_type, media in content.items():
                check_media_type(
                    media,
                    f"paths.{route}.{method}.responses.200.content.{media_type}",
                    errors,
                )

    if response_count == 0:
        errors.append("paths 中没有可审计的 200 响应")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "用法: validate_openapi_response_contract.py <file.openapi.json>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1]).resolve()
    errors = validate(path)
    if errors:
        print(f"OpenAPI 响应契约校验失败: {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(f"问题总数: {len(errors)}", file=sys.stderr)
        return 1

    print(f"OpenAPI 响应契约校验通过: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
