#!/usr/bin/env python3
"""Validate request parameters and JSON-body metadata for repository OpenAPI files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


CHINESE = re.compile(r"[\u3400-\u9fff]")
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
BODY_METHODS = {"post", "put", "patch", "delete"}


def has_chinese(value: Any) -> bool:
    return isinstance(value, str) and bool(CHINESE.search(value))


def schema_type_is(schema: dict[str, Any], expected: str) -> bool:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return expected in schema_type
    return schema_type == expected


def find_binary_field(schema: Any) -> bool:
    """Return True when the schema tree declares at least one binary file field."""
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
        if isinstance(variants, list) and any(
            find_binary_field(child) for child in variants
        ):
            return True
    return False


def check_example_shape(
    schema: Any,
    example: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(schema, dict):
        return

    properties = schema.get("properties")
    if isinstance(properties, dict):
        if not isinstance(example, dict):
            errors.append(f"{location} 的 example 必须是对象")
            return

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
            errors.append(f"{location} 的 example 字段不完整（{'；'.join(details)}）")

        for name, child in properties.items():
            if name in example:
                check_example_shape(child, example[name], f"{location}.{name}", errors)

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            errors.append(f"{location}.items 不能是空结构")
        elif isinstance(example, list):
            for index, item in enumerate(example):
                check_example_shape(items, item, f"{location}.items[{index}]", errors)


def check_schema_metadata(
    schema: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(schema, dict):
        errors.append(f"{location} 必须是 schema 对象")
        return

    if schema.get("format") == "binary" and not schema_type_is(schema, "string"):
        errors.append(f"{location} 的 binary 字段 type 必须是 string")

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            child_location = f"{location}.properties.{name}"
            if not isinstance(child, dict):
                errors.append(f"{child_location} 必须是对象")
                continue
            if not has_chinese(child.get("description")):
                errors.append(f"{child_location} 缺少中文 description")
            if "example" not in child:
                errors.append(f"{child_location} 缺少字段级 example")
            check_schema_metadata(child, child_location, errors)

    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict) or not items:
            errors.append(f"{location}.items 不能是空结构")
        else:
            check_schema_metadata(items, f"{location}.items", errors)

    for key in ("allOf", "anyOf", "oneOf"):
        variants = schema.get(key, [])
        if not isinstance(variants, list):
            errors.append(f"{location}.{key} 必须是数组")
            continue
        for index, child in enumerate(variants):
            check_schema_metadata(child, f"{location}.{key}[{index}]", errors)


def validate(path: Path) -> tuple[list[str], list[str]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"文件不存在: {path}"], []
    except json.JSONDecodeError as exc:
        return [f"JSON 无效: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}"], []

    if not isinstance(document, dict):
        return ["OpenAPI 文档根节点必须是对象"], []

    errors: list[str] = []
    hints: list[str] = []
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return ["paths 必须是对象"]

    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operation_location = f"paths.{route}.{method}"
            parameters = operation.get("parameters", [])
            if not isinstance(parameters, list):
                errors.append(f"{operation_location}.parameters 必须是数组")
                parameters = []

            for index, parameter in enumerate(parameters):
                parameter_location = f"{operation_location}.parameters[{index}]"
                if not isinstance(parameter, dict):
                    errors.append(f"{parameter_location} 必须是对象")
                    continue
                if not has_chinese(parameter.get("description")):
                    errors.append(f"{parameter_location} 缺少中文 description")
                schema = parameter.get("schema", {})
                if not isinstance(schema, dict):
                    errors.append(f"{parameter_location}.schema 必须是对象")
                    continue
                if "example" not in parameter and "example" not in schema:
                    errors.append(f"{parameter_location} 缺少 example")

            if method not in BODY_METHODS:
                continue

            request_body = operation.get("requestBody")
            if request_body is None:
                continue
            if not isinstance(request_body, dict):
                errors.append(f"{operation_location}.requestBody 必须是对象")
                continue
            if request_body.get("required") is not True:
                errors.append(f"{operation_location}.requestBody.required 必须为 true")

            content = request_body.get("content", {})
            if not isinstance(content, dict):
                errors.append(f"{operation_location}.requestBody.content 必须是对象")
                continue
            json_media = content.get("application/json")
            multipart_media = content.get("multipart/form-data")
            if isinstance(json_media, dict):
                media = json_media
                media_key = "application/json"
                if isinstance(multipart_media, dict):
                    hints.append(
                        f"{operation_location} 同时声明了 application/json 与 multipart/form-data，"
                        "请核对接口是否真实支持两种请求形态，只支持一种时按真实情况删除另一种"
                    )
            elif isinstance(multipart_media, dict):
                media = multipart_media
                media_key = "multipart/form-data"
            else:
                errors.append(
                    f"{operation_location}.requestBody 缺少 application/json 或 multipart/form-data"
                )
                continue

            schema = media.get("schema")
            if not isinstance(schema, dict) or not schema_type_is(schema, "object"):
                errors.append(f"{operation_location}.requestBody schema 必须是 object")
                continue
            properties = schema.get("properties")
            if not isinstance(properties, dict) or not properties:
                errors.append(f"{operation_location}.requestBody schema.properties 不能为空")
                continue
            if media_key == "multipart/form-data" and not find_binary_field(schema):
                errors.append(
                    f"{operation_location}.requestBody.content.multipart/form-data"
                    " 必须至少声明一个 format: binary 文件字段"
                )
            required = schema.get("required")
            if not isinstance(required, list):
                errors.append(f"{operation_location}.requestBody 缺少 required 数组")
            else:
                required_names = [name for name in required if isinstance(name, str)]
                if len(required_names) != len(required):
                    errors.append(f"{operation_location}.requestBody.required 必须只包含字符串字段名")
                if len(required_names) != len(set(required_names)):
                    errors.append(f"{operation_location}.requestBody.required 不能包含重复字段")
                unknown_required = set(required_names) - set(properties)
                if unknown_required:
                    names = ", ".join(sorted(unknown_required))
                    errors.append(
                        f"{operation_location}.requestBody.required 包含未定义字段: {names}"
                    )

            parameter_names = {
                parameter.get("name")
                for parameter in parameters
                if isinstance(parameter, dict) and isinstance(parameter.get("name"), str)
            }
            duplicated = parameter_names & set(properties)
            if duplicated:
                names = ", ".join(sorted(duplicated))
                errors.append(
                    f"{operation_location} 的 Body 字段不能重复放入 parameters: {names}"
                )

            if not isinstance(media.get("example"), dict):
                errors.append(
                    f"{operation_location}.requestBody.content.{media_key} 缺少完整 example"
                )
            else:
                check_example_shape(
                    schema,
                    media["example"],
                    f"{operation_location}.requestBody.example",
                    errors,
                )

            check_schema_metadata(
                schema,
                f"{operation_location}.requestBody.schema",
                errors,
            )

    return errors, hints


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: validate_openapi_request_contract.py <file.openapi.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).resolve()
    errors, hints = validate(path)
    if errors:
        print(f"OpenAPI 请求契约校验失败: {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"OpenAPI 请求契约校验通过: {path}")
    for hint in hints:
        print(f"提示: {hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
