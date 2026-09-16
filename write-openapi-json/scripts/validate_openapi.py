#!/usr/bin/env python3
"""Validate the repository-style OpenAPI JSON contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


FILENAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.openapi\.json$")
TOP_LEVEL_KEYS = {"openapi", "info", "tags", "paths", "webhooks", "servers"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
OPERATION_KEYS = {
    "summary",
    "deprecated",
    "description",
    "tags",
    "parameters",
    "requestBody",
    "responses",
}
REQUIRED_OPERATION_KEYS = OPERATION_KEYS - {"requestBody"}
FORBIDDEN_KEYS = {"components", "schemas", "security", "securitySchemes", "$ref"}
AUTH_FIELD_NAMES = {
    "authorization",
    "token",
    "accesstoken",
    "xaccesstoken",
    "apikey",
    "xapikey",
    "appid",
    "appkey",
    "sign",
    "signature",
}
CHINESE = re.compile(r"[\u3400-\u9fff]")


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


def check_binary_type(schema: Any, location: str, errors: list[str]) -> None:
    if (
        isinstance(schema, dict)
        and schema.get("format") == "binary"
        and not schema_type_is(schema, "string")
    ):
        errors.append(f"{location} 的 binary 字段 type 必须是 string")


def validate_multipart_media(
    media: dict[str, Any],
    operation_location: str,
    errors: list[str],
) -> None:
    """Apply JSON-equivalent structural checks to a multipart/form-data request body."""
    media_location = f"{operation_location}.requestBody.content.multipart/form-data"
    schema = media.get("schema")
    if not isinstance(schema, dict):
        errors.append(f"{operation_location}.requestBody 必须内联 multipart/form-data schema")
        return
    if not schema_type_is(schema, "object"):
        errors.append(f"{media_location}.schema 必须是 object")
        return
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        errors.append(f"{media_location}.schema.properties 不能为空")
        return
    required = schema.get("required")
    if isinstance(required, list):
        unknown_required = [name for name in required if name not in properties]
        if unknown_required:
            names = ", ".join(str(name) for name in unknown_required)
            errors.append(f"{media_location}.schema.required 包含未定义字段: {names}")
    if not find_binary_field(schema):
        errors.append(
            f"{media_location}.schema 必须至少声明一个 format: binary 文件字段"
        )
    for name, child in properties.items():
        child_location = f"{media_location}.schema.properties.{name}"
        if not isinstance(child, dict):
            errors.append(f"{child_location} 必须是对象")
            continue
        check_binary_type(child, child_location, errors)
        if not has_chinese(child.get("description")):
            errors.append(f"{child_location} 缺少中文 description")
        example = child.get("example")
        if example is None or example == "" or example == [] or example == {}:
            errors.append(f"{child_location} 缺少非空 example")
    if not isinstance(media.get("example"), dict):
        errors.append(f"{media_location} 缺少媒体类型级 example")


def walk(value: Any, location: str = "$"):
    """Yield every nested value with its JSON location."""
    yield location, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{location}[{index}]")


def validate(path: Path) -> tuple[list[str], list[str]]:
    """Return all validation errors and media-type hints for an OpenAPI JSON file."""
    errors: list[str] = []
    hints: list[str] = []

    if not FILENAME_PATTERN.fullmatch(path.name):
        errors.append("文件名必须是表达业务范围的 kebab-case，并以 .openapi.json 结尾")

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"文件不存在: {path}"], []
    except json.JSONDecodeError as exc:
        return [f"JSON 无效: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}"], []

    if not isinstance(document, dict):
        return ["OpenAPI 文档顶层必须是对象"], []

    actual_top_level_keys = set(document)
    missing_top_level_keys = TOP_LEVEL_KEYS - actual_top_level_keys
    unexpected_top_level_keys = actual_top_level_keys - TOP_LEVEL_KEYS
    if missing_top_level_keys:
        errors.append(f"缺少顶层字段: {', '.join(sorted(missing_top_level_keys))}")
    if unexpected_top_level_keys:
        errors.append(f"存在不符合固定格式的顶层字段: {', '.join(sorted(unexpected_top_level_keys))}")

    if document.get("openapi") != "3.1.0":
        errors.append('openapi 必须为 "3.1.0"')
    if document.get("webhooks") != {}:
        errors.append("webhooks 必须为空对象")
    if document.get("servers") != []:
        errors.append("servers 必须为空数组")

    info = document.get("info")
    if not isinstance(info, dict):
        errors.append("info 必须是对象")
    else:
        for key in ("title", "description", "version"):
            if not isinstance(info.get(key), str) or not info[key].strip():
                errors.append(f"info.{key} 必须是非空字符串")

    tags = document.get("tags")
    if not isinstance(tags, list) or not tags:
        errors.append("tags 必须是非空数组")

    for location, value in walk(document):
        if isinstance(value, dict):
            forbidden = FORBIDDEN_KEYS.intersection(value)
            for key in sorted(forbidden):
                errors.append(f"{location} 禁止包含字段 {key}")

            if value.get("in") in {"header", "query", "cookie"}:
                parameter_name = re.sub(
                    r"[^a-z0-9]",
                    "",
                    str(value.get("name", "")).strip().lower(),
                )
                if parameter_name in AUTH_FIELD_NAMES:
                    errors.append(f"{location} 禁止包含鉴权参数 {value.get('name')}")

            properties = value.get("properties")
            if isinstance(properties, dict):
                for property_name in properties:
                    normalized_property_name = re.sub(
                        r"[^a-z0-9]",
                        "",
                        str(property_name).strip().lower(),
                    )
                    if normalized_property_name in AUTH_FIELD_NAMES:
                        errors.append(f"{location}.properties 禁止包含鉴权字段 {property_name}")

    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append("paths 必须是非空对象")
        return errors, []

    operation_count = 0
    for route, path_item in paths.items():
        if not isinstance(route, str) or not route.startswith("/"):
            errors.append(f"无效接口路径: {route}")
            continue
        if not isinstance(path_item, dict) or not path_item:
            errors.append(f"paths.{route} 必须包含 HTTP 操作")
            continue

        for method, operation in path_item.items():
            operation_location = f"paths.{route}.{method}"
            if method not in HTTP_METHODS:
                errors.append(f"{operation_location} 不是支持的 HTTP 操作")
                continue
            operation_count += 1
            if not isinstance(operation, dict):
                errors.append(f"{operation_location} 必须是对象")
                continue

            operation_keys = set(operation)
            missing_operation_keys = REQUIRED_OPERATION_KEYS - operation_keys
            unexpected_operation_keys = operation_keys - OPERATION_KEYS
            if missing_operation_keys:
                errors.append(
                    f"{operation_location} 缺少字段: "
                    f"{', '.join(sorted(missing_operation_keys))}"
                )
            if unexpected_operation_keys:
                errors.append(
                    f"{operation_location} 存在不符合固定格式的字段: "
                    f"{', '.join(sorted(unexpected_operation_keys))}"
                )

            if not isinstance(operation.get("summary"), str) or not operation["summary"].strip():
                errors.append(f"{operation_location}.summary 必须是非空字符串")
            if not isinstance(operation.get("description"), str) or not operation["description"].strip():
                errors.append(f"{operation_location}.description 必须是非空字符串")
            if operation.get("deprecated") is not False:
                errors.append(f"{operation_location}.deprecated 必须为 false")
            if not isinstance(operation.get("tags"), list) or not operation["tags"]:
                errors.append(f"{operation_location}.tags 必须是非空数组")
            if not isinstance(operation.get("parameters"), list):
                errors.append(f"{operation_location}.parameters 必须是数组")

            responses = operation.get("responses")
            if not isinstance(responses, dict) or set(responses) != {"200"}:
                errors.append(f"{operation_location}.responses 只能包含 200")
            else:
                response = responses["200"]
                response_content = response.get("content") if isinstance(response, dict) else None
                media = response_content.get("application/json") if isinstance(response_content, dict) else None
                if not isinstance(media, dict) or not ({"schema", "example"} & set(media)):
                    errors.append(
                        f"{operation_location}.responses.200 必须内联 application/json schema 或 example"
                    )

            request_body = operation.get("requestBody")
            if request_body is not None:
                request_content = request_body.get("content") if isinstance(request_body, dict) else None
                request_content = request_content if isinstance(request_content, dict) else {}
                json_media = request_content.get("application/json")
                multipart_media = request_content.get("multipart/form-data")
                if not isinstance(request_body, dict) or request_body.get("required") is not True:
                    errors.append(f"{operation_location}.requestBody.required 必须为 true")
                if json_media is not None and not isinstance(json_media, dict):
                    errors.append(f"{operation_location}.requestBody 必须内联 application/json schema")
                if isinstance(json_media, dict):
                    if not isinstance(json_media.get("schema"), dict):
                        errors.append(f"{operation_location}.requestBody 必须内联 application/json schema")
                    if isinstance(multipart_media, dict):
                        hints.append(
                            f"{operation_location} 同时声明了 application/json 与 multipart/form-data，"
                            "请核对接口是否真实支持两种请求形态，只支持一种时按真实情况删除另一种"
                        )
                elif isinstance(multipart_media, dict):
                    validate_multipart_media(multipart_media, operation_location, errors)
                elif multipart_media is not None:
                    errors.append(f"{operation_location}.requestBody 必须内联 multipart/form-data schema")
                elif json_media is None and multipart_media is None:
                    errors.append(
                        f"{operation_location}.requestBody 必须内联 application/json 或 multipart/form-data schema"
                    )

    if operation_count == 0:
        errors.append("paths 中没有可用的 HTTP 操作")

    return errors, hints


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: validate_openapi.py <file.openapi.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).resolve()
    errors, hints = validate(path)
    if errors:
        print(f"OpenAPI 校验失败: {path}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    document = json.loads(path.read_text(encoding="utf-8"))
    operation_count = sum(len(path_item) for path_item in document["paths"].values())
    print(f"OpenAPI 校验通过: {path}")
    print(f"接口数量: {operation_count}")
    for hint in hints:
        print(f"提示: {hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
