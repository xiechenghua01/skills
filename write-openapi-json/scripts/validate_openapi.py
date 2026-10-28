#!/usr/bin/env python3
"""校验 OpenAPI JSON 的结构契约：顶层形状、操作字段、禁止项、媒体类型。

用法:
    python3 validate_openapi.py [--json] <file.openapi.json> [更多文件...]

传多个文件时会额外比对跨文件重复路径（规则码 DUP-001）——同一接口只能在一份契约里定义。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from _openapi_common import (
    HTTP_METHODS,
    Issue,
    find_binary_field,
    has_chinese,
    load_document,
    run_cli,
    schema_type_is,
)

FILENAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.openapi\.json$")
TOP_LEVEL_KEYS = {"openapi", "info", "tags", "paths", "webhooks", "servers"}
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


def walk(value: Any, location: str = "$"):
    """产出每个嵌套值与它的 JSON 位置。"""
    yield location, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{location}[{index}]")


def check_binary_type(schema: Any, location: str) -> list[Issue]:
    if (
        isinstance(schema, dict)
        and schema.get("format") == "binary"
        and not schema_type_is(schema, "string")
    ):
        return [Issue("MP-005", f"{location} 的 binary 字段 type 必须是 string")]
    return []


def validate_multipart_media(media: dict[str, Any], operation_location: str) -> list[Issue]:
    """multipart/form-data 请求体的结构检查。"""
    issues: list[Issue] = []
    media_location = f"{operation_location}.requestBody.content.multipart/form-data"
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return [Issue("MP-001", f"{operation_location}.requestBody 必须内联 multipart/form-data schema")]
    if not schema_type_is(schema, "object"):
        return [Issue("MP-002", f"{media_location}.schema 必须是 object")]
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return [Issue("MP-003", f"{media_location}.schema.properties 不能为空")]

    required = schema.get("required")
    if isinstance(required, list):
        unknown = [name for name in required if name not in properties]
        if unknown:
            issues.append(
                Issue(
                    "MP-004",
                    f"{media_location}.schema.required 包含未定义字段: {', '.join(str(n) for n in unknown)}",
                )
            )
    if not find_binary_field(schema):
        issues.append(Issue("MP-006", f"{media_location}.schema 必须至少声明一个 format: binary 文件字段"))

    for name, child in properties.items():
        child_location = f"{media_location}.schema.properties.{name}"
        if not isinstance(child, dict):
            issues.append(Issue("MP-007", f"{child_location} 必须是对象"))
            continue
        issues.extend(check_binary_type(child, child_location))
        if not has_chinese(child.get("description")):
            issues.append(Issue("MP-008", f"{child_location} 缺少中文 description"))
        example = child.get("example")
        if example is None or example == "" or example == [] or example == {}:
            issues.append(Issue("MP-009", f"{child_location} 缺少非空 example"))

    if not isinstance(media.get("example"), dict):
        issues.append(Issue("MP-010", f"{media_location} 缺少媒体类型级 example"))
    return issues


def validate(path: Path) -> list[Issue]:
    issues: list[Issue] = []

    if not FILENAME_PATTERN.fullmatch(path.name):
        issues.append(
            Issue("NAME-001", "文件名必须是表达业务范围的 kebab-case，并以 .openapi.json 结尾")
        )

    document, load_issues = load_document(path)
    if document is None:
        return issues + load_issues

    actual_keys = set(document)
    missing_keys = TOP_LEVEL_KEYS - actual_keys
    extra_keys = actual_keys - TOP_LEVEL_KEYS
    if missing_keys:
        issues.append(Issue("TOP-001", f"缺少顶层字段: {', '.join(sorted(missing_keys))}"))
    if extra_keys:
        issues.append(
            Issue("TOP-002", f"存在不符合固定格式的顶层字段: {', '.join(sorted(extra_keys))}")
        )

    if document.get("openapi") != "3.1.0":
        issues.append(Issue("VER-001", 'openapi 必须为 "3.1.0"'))
    if document.get("webhooks") != {}:
        issues.append(Issue("HOOK-001", "webhooks 必须为空对象"))
    if document.get("servers") != []:
        issues.append(Issue("SRV-001", "servers 必须为空数组"))

    info = document.get("info")
    if not isinstance(info, dict):
        issues.append(Issue("INFO-001", "info 必须是对象"))
    else:
        for key in ("title", "description", "version"):
            if not isinstance(info.get(key), str) or not info[key].strip():
                issues.append(Issue("INFO-002", f"info.{key} 必须是非空字符串"))

    tags = document.get("tags")
    if not isinstance(tags, list) or not tags:
        issues.append(Issue("TAG-001", "tags 必须是非空数组"))

    for location, value in walk(document):
        if isinstance(value, dict):
            for key in sorted(FORBIDDEN_KEYS.intersection(value)):
                issues.append(Issue("FORBID-001", f"{location} 禁止包含字段 {key}"))

            if value.get("in") in {"header", "query", "cookie"}:
                normalized = re.sub(r"[^a-z0-9]", "", str(value.get("name", "")).strip().lower())
                if normalized in AUTH_FIELD_NAMES:
                    issues.append(Issue("AUTH-001", f"{location} 禁止包含鉴权参数 {value.get('name')}"))

            properties = value.get("properties")
            if isinstance(properties, dict):
                for property_name in properties:
                    normalized = re.sub(r"[^a-z0-9]", "", str(property_name).strip().lower())
                    if normalized in AUTH_FIELD_NAMES:
                        issues.append(
                            Issue("AUTH-002", f"{location}.properties 禁止包含鉴权字段 {property_name}")
                        )

    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        issues.append(Issue("PATH-001", "paths 必须是非空对象"))
        return issues

    operation_count = 0
    for route, path_item in paths.items():
        if not isinstance(route, str) or not route.startswith("/"):
            issues.append(Issue("PATH-002", f"无效接口路径: {route}"))
            continue
        if not isinstance(path_item, dict) or not path_item:
            issues.append(Issue("PATH-003", f"paths.{route} 必须包含 HTTP 操作"))
            continue

        for method, operation in path_item.items():
            operation_location = f"paths.{route}.{method}"
            if method not in HTTP_METHODS:
                issues.append(Issue("METHOD-001", f"{operation_location} 不是支持的 HTTP 操作"))
                continue
            operation_count += 1
            if not isinstance(operation, dict):
                issues.append(Issue("OP-000", f"{operation_location} 必须是对象"))
                continue

            operation_keys = set(operation)
            missing = REQUIRED_OPERATION_KEYS - operation_keys
            extra = operation_keys - OPERATION_KEYS
            if missing:
                issues.append(
                    Issue("OP-001", f"{operation_location} 缺少字段: {', '.join(sorted(missing))}")
                )
            if extra:
                issues.append(
                    Issue("OP-002", f"{operation_location} 存在不符合固定格式的字段: {', '.join(sorted(extra))}")
                )

            if not isinstance(operation.get("summary"), str) or not operation["summary"].strip():
                issues.append(Issue("OP-003", f"{operation_location}.summary 必须是非空字符串"))
            if not isinstance(operation.get("description"), str) or not operation["description"].strip():
                issues.append(Issue("OP-004", f"{operation_location}.description 必须是非空字符串"))
            if operation.get("deprecated") is not False:
                issues.append(Issue("OP-005", f"{operation_location}.deprecated 必须为 false"))
            if not isinstance(operation.get("tags"), list) or not operation["tags"]:
                issues.append(Issue("OP-006", f"{operation_location}.tags 必须是非空数组"))
            if not isinstance(operation.get("parameters"), list):
                issues.append(Issue("OP-007", f"{operation_location}.parameters 必须是数组"))

            responses = operation.get("responses")
            if not isinstance(responses, dict) or set(responses) != {"200"}:
                issues.append(Issue("RESP-001", f"{operation_location}.responses 只能包含 200"))
            else:
                response = responses["200"]
                content = response.get("content") if isinstance(response, dict) else None
                media = content.get("application/json") if isinstance(content, dict) else None
                if not isinstance(media, dict) or not ({"schema", "example"} & set(media)):
                    issues.append(
                        Issue(
                            "RESP-002",
                            f"{operation_location}.responses.200 必须内联 application/json schema 或 example",
                        )
                    )

            request_body = operation.get("requestBody")
            if request_body is None:
                continue
            content = request_body.get("content") if isinstance(request_body, dict) else None
            content = content if isinstance(content, dict) else {}
            json_media = content.get("application/json")
            multipart_media = content.get("multipart/form-data")
            if not isinstance(request_body, dict) or request_body.get("required") is not True:
                issues.append(Issue("BODY-001", f"{operation_location}.requestBody.required 必须为 true"))
            if json_media is not None and not isinstance(json_media, dict):
                issues.append(
                    Issue("BODY-002", f"{operation_location}.requestBody 必须内联 application/json schema")
                )
            if isinstance(json_media, dict):
                if not isinstance(json_media.get("schema"), dict):
                    issues.append(
                        Issue("BODY-002", f"{operation_location}.requestBody 必须内联 application/json schema")
                    )
                if isinstance(multipart_media, dict):
                    issues.append(
                        Issue(
                            "BODY-005",
                            f"{operation_location} 同时声明了 application/json 与 multipart/form-data，"
                            "请核对接口是否真实支持两种请求形态，只支持一种时按真实情况删除另一种",
                            severity="hint",
                        )
                    )
            elif isinstance(multipart_media, dict):
                issues.extend(validate_multipart_media(multipart_media, operation_location))
            elif multipart_media is not None:
                issues.append(
                    Issue("BODY-003", f"{operation_location}.requestBody 必须内联 multipart/form-data schema")
                )
            elif json_media is None and multipart_media is None:
                issues.append(
                    Issue(
                        "BODY-004",
                        f"{operation_location}.requestBody 必须内联 application/json 或 multipart/form-data schema",
                    )
                )

    if operation_count == 0:
        issues.append(Issue("OPS-001", "paths 中没有可用的 HTTP 操作"))

    return issues


def main() -> int:
    return run_cli("OpenAPI 结构", sys.argv, validate, cross_file=True)


if __name__ == "__main__":
    raise SystemExit(main())
