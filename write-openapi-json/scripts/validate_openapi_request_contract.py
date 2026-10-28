#!/usr/bin/env python3
"""校验请求侧契约：参数说明与示例、请求体结构、示例完整性、嵌套字段元数据。

用法:
    python3 validate_openapi_request_contract.py [--json] <file.openapi.json> [更多文件...]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from _openapi_common import (
    Issue,
    find_binary_field,
    has_chinese,
    iter_operations,
    load_document,
    run_cli,
    schema_type_is,
)

BODY_METHODS = {"post", "put", "patch", "delete"}


def check_example_shape(schema: Any, example: Any, location: str) -> list[Issue]:
    """媒体类型级 example 的字段集合必须与 schema.properties 一致，并递归到嵌套结构。"""
    issues: list[Issue] = []
    if not isinstance(schema, dict):
        return issues

    properties = schema.get("properties")
    if isinstance(properties, dict):
        if not isinstance(example, dict):
            return [Issue("REQ-013", f"{location} 的 example 必须是对象")]

        expected = set(properties)
        actual = set(example)
        if actual != expected:
            missing = ", ".join(sorted(expected - actual))
            extra = ", ".join(sorted(actual - expected))
            details = []
            if missing:
                details.append(f"缺少字段: {missing}")
            if extra:
                details.append(f"多余字段: {extra}")
            issues.append(
                Issue("REQ-014", f"{location} 的 example 字段不完整（{'；'.join(details)}）")
            )

        for name, child in properties.items():
            if name in example:
                issues.extend(check_example_shape(child, example[name], f"{location}.{name}"))

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            issues.append(Issue("REQ-015", f"{location}.items 不能是空结构"))
        elif isinstance(example, list):
            for index, item in enumerate(example):
                issues.extend(
                    check_example_shape(items, item, f"{location}.items[{index}]")
                )
    return issues


def check_schema_metadata(schema: Any, location: str) -> list[Issue]:
    """请求字段的中文说明、字段级 example、嵌套与联合结构。"""
    issues: list[Issue] = []
    if not isinstance(schema, dict):
        return [Issue("REQ-016", f"{location} 必须是 schema 对象")]

    if schema.get("format") == "binary" and not schema_type_is(schema, "string"):
        issues.append(Issue("REQ-019", f"{location} 的 binary 字段 type 必须是 string"))

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            child_location = f"{location}.properties.{name}"
            if not isinstance(child, dict):
                issues.append(Issue("REQ-016", f"{child_location} 必须是对象"))
                continue
            if not has_chinese(child.get("description")):
                issues.append(Issue("REQ-018", f"{child_location} 缺少中文 description"))
            if "example" not in child:
                issues.append(Issue("REQ-017", f"{child_location} 缺少字段级 example"))
            issues.extend(check_schema_metadata(child, child_location))

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            issues.append(Issue("REQ-015", f"{location}.items 不能是空结构"))
        else:
            issues.extend(check_schema_metadata(items, f"{location}.items"))

    for key in ("allOf", "anyOf", "oneOf"):
        variants = schema.get(key, [])
        if not isinstance(variants, list):
            issues.append(Issue("REQ-020", f"{location}.{key} 必须是数组"))
            continue
        for index, child in enumerate(variants):
            issues.extend(check_schema_metadata(child, f"{location}.{key}[{index}]"))

    return issues


def validate(path: Path) -> list[Issue]:
    document, load_issues = load_document(path)
    if document is None:
        return load_issues

    issues: list[Issue] = []
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return [Issue("PATH-001", "paths 必须是对象")]

    for route, method, operation, operation_location in iter_operations(document):
        parameters = operation.get("parameters", [])
        if not isinstance(parameters, list):
            issues.append(Issue("PARAM-001", f"{operation_location}.parameters 必须是数组"))
            parameters = []

        for index, parameter in enumerate(parameters):
            parameter_location = f"{operation_location}.parameters[{index}]"
            if not isinstance(parameter, dict):
                issues.append(Issue("PARAM-002", f"{parameter_location} 必须是对象"))
                continue
            if not has_chinese(parameter.get("description")):
                issues.append(Issue("PARAM-003", f"{parameter_location} 缺少中文 description"))
            schema = parameter.get("schema", {})
            if not isinstance(schema, dict):
                issues.append(Issue("PARAM-004", f"{parameter_location}.schema 必须是对象"))
                continue
            if "example" not in parameter and "example" not in schema:
                issues.append(Issue("PARAM-005", f"{parameter_location} 缺少 example"))

        if method not in BODY_METHODS:
            continue

        request_body = operation.get("requestBody")
        if request_body is None:
            continue
        if not isinstance(request_body, dict):
            issues.append(Issue("REQ-001", f"{operation_location}.requestBody 必须是对象"))
            continue
        if request_body.get("required") is not True:
            issues.append(Issue("REQ-002", f"{operation_location}.requestBody.required 必须为 true"))

        content = request_body.get("content", {})
        if not isinstance(content, dict):
            issues.append(Issue("REQ-003", f"{operation_location}.requestBody.content 必须是对象"))
            continue
        json_media = content.get("application/json")
        multipart_media = content.get("multipart/form-data")
        if isinstance(json_media, dict):
            media, media_key = json_media, "application/json"
            if isinstance(multipart_media, dict):
                issues.append(
                    Issue(
                        "REQ-021",
                        f"{operation_location} 同时声明了 application/json 与 multipart/form-data，"
                        "请核对接口是否真实支持两种请求形态，只支持一种时按真实情况删除另一种",
                        severity="hint",
                    )
                )
        elif isinstance(multipart_media, dict):
            media, media_key = multipart_media, "multipart/form-data"
        else:
            issues.append(
                Issue("REQ-004", f"{operation_location}.requestBody 缺少 application/json 或 multipart/form-data")
            )
            continue

        schema = media.get("schema")
        if not isinstance(schema, dict) or not schema_type_is(schema, "object"):
            issues.append(Issue("REQ-005", f"{operation_location}.requestBody schema 必须是 object"))
            continue
        properties = schema.get("properties")
        if not isinstance(properties, dict) or not properties:
            issues.append(Issue("REQ-006", f"{operation_location}.requestBody schema.properties 不能为空"))
            continue
        if media_key == "multipart/form-data" and not find_binary_field(schema):
            issues.append(
                Issue(
                    "REQ-007",
                    f"{operation_location}.requestBody.content.multipart/form-data 必须至少声明一个 format: binary 文件字段",
                )
            )

        required = schema.get("required")
        if not isinstance(required, list):
            issues.append(Issue("REQ-008", f"{operation_location}.requestBody 缺少 required 数组"))
        else:
            names = [name for name in required if isinstance(name, str)]
            if len(names) != len(required):
                issues.append(
                    Issue("REQ-009", f"{operation_location}.requestBody.required 必须只包含字符串字段名")
                )
            if len(names) != len(set(names)):
                issues.append(Issue("REQ-010", f"{operation_location}.requestBody.required 不能包含重复字段"))
            unknown = set(names) - set(properties)
            if unknown:
                issues.append(
                    Issue(
                        "REQ-011",
                        f"{operation_location}.requestBody.required 包含未定义字段: {', '.join(sorted(unknown))}",
                    )
                )

        parameter_names = {
            parameter.get("name")
            for parameter in parameters
            if isinstance(parameter, dict) and isinstance(parameter.get("name"), str)
        }
        duplicated = parameter_names & set(properties)
        if duplicated:
            issues.append(
                Issue(
                    "REQ-012",
                    f"{operation_location} 的 Body 字段不能重复放入 parameters: {', '.join(sorted(duplicated))}",
                )
            )

        example = media.get("example")
        if not isinstance(example, dict):
            issues.append(
                Issue("REQ-022", f"{operation_location}.requestBody.content.{media_key} 缺少完整 example")
            )
        else:
            issues.extend(
                check_example_shape(schema, example, f"{operation_location}.requestBody.example")
            )

        issues.extend(check_schema_metadata(schema, f"{operation_location}.requestBody.schema"))

    return issues


def main() -> int:
    return run_cli("OpenAPI 请求契约", sys.argv, validate)


if __name__ == "__main__":
    raise SystemExit(main())
