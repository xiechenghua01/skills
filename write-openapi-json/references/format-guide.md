# OpenAPI JSON 格式规范

本规范提炼自 `aero-manufacture-drone-operations.openapi.json`，用于保持后续接口文档结构一致。

## 顶层结构

固定使用以下结构和顺序：

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "业务范围标题",
    "description": "说明文档用途及包含范围",
    "version": "1.0.0"
  },
  "tags": [
    {
      "name": "业务模块"
    }
  ],
  "paths": {},
  "webhooks": {},
  "servers": []
}
```

- 不增加 `components`。
- 不增加鉴权、安全方案、公共参数、公共响应或公共模型。
- `info.description` 明确文档只包含用户指定范围。

## 操作结构

每个接口使用以下字段顺序：

```json
{
  "summary": "简短接口名称",
  "deprecated": false,
  "description": "说明业务行为、限制和必要权限，但不定义鉴权头",
  "tags": [
    "业务模块"
  ],
  "parameters": [],
  "requestBody": {},
  "responses": {
    "200": {}
  }
}
```

- GET 参数内联到 `parameters`。
- POST、PUT、PATCH、DELETE 的 JSON Body 内联到 `requestBody`。
- 没有请求体时省略 `requestBody`，没有查询或路径参数时仍保留空的 `parameters`。
- 不写 `operationId`、公共参数引用或公共响应引用。

## 参数格式

```json
{
  "name": "status",
  "in": "query",
  "description": "航空器启用状态：0-禁用，1-启用",
  "required": false,
  "example": 1,
  "schema": {
    "type": "integer",
    "enum": [
      0,
      1
    ]
  }
}
```

- 参数类型、边界、默认值、数组序列化方式必须来自 Request 或实际解析代码。
- 状态描述包含字段业务名称和完整枚举含义。

## 请求体格式

```json
{
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "type": "object",
        "properties": {
          "id": {
            "type": "integer",
            "minimum": 1,
            "description": "资源ID",
            "example": 1
          }
        },
        "required": [
          "id"
        ]
      },
      "example": {
        "id": 1
      }
    }
  }
}
```

- 使用内联 schema，不使用 `$ref`。
- 条件必填可以使用 OpenAPI 3.1 的 `if`、`then`、`allOf`。
- 多个典型请求场景使用 `examples`，否则使用一个 `example`。
- `schema.properties` 中的每个请求字段必须有中文 `description` 和字段级 `example`；媒体类型级 `example` 必须覆盖全部字段，包括可选字段。
- 媒体类型级 `example` 用于 Apifox/Swagger UI 直接展示完整传参；不能只写字段结构而省略完整请求示例。
- 完整示例必须位于 `content.application/json.example`，不能放在 `requestBody.example`，也不能用 `schema.example` 替代。
- `parameters` 只放 query/path 参数；不要把 JSON Body 字段复制到 `parameters`。`parameters: []` 只表示接口确实没有 query/path 参数，不能表示遗漏了 `requestBody`。

## 响应格式

只保留 `200`。返回业务数据的接口必须完整描述响应封装和 `data`：

```json
{
  "200": {
    "description": "成功",
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "properties": {
            "code": {
              "type": "integer",
              "const": 200,
              "description": "HTTP业务响应码"
            },
            "trace_id": {
              "type": "string",
              "description": "请求链路ID"
            },
            "message": {
              "type": "string",
              "description": "响应消息"
            },
            "data": {
              "type": "object",
              "description": "接口真实返回数据",
              "properties": {}
            }
          },
          "required": [
            "code",
            "trace_id",
            "message",
            "data"
          ]
        }
      }
    }
  }
}
```

只返回空数据的操作接口可以使用完整响应示例：

```json
{
  "200": {
    "description": "成功",
    "content": {
      "application/json": {
        "example": {
          "code": 200,
          "trace_id": "01J00000000000000000000000",
          "message": "成功",
          "data": []
        }
      }
    }
  }
}
```

## 字段完整性

- 从最终响应构造处开始反向追踪，不能只看 Controller 的表面返回。
- 展开分页元数据、列表元素、详情对象、关联对象和最新记录等嵌套数据。
- `required` 表示响应对象一定出现该字段；字段值可为 `null` 时仍可列入 `required`，并把类型声明为可空。
- 动态数组确实无固定结构时才使用空的 `items: {}`；能从代码确定结构时必须展开。
- 只要代码、Model、Resource 或 Request 能确定数组项结构，就禁止使用空 `items: {}`；例如附件要展开路径、大小、上传时间，等级选项要展开 `value`、`label`。
- 请求和响应对象的每个实际字段都要有中文 `description`；字段说明应包含业务含义、单位、格式、枚举、长度、可空和条件必填信息。
- 示例值必须符合代码校验规则，不能使用加密值、摘要、Token 或真实敏感数据。
- 状态、类型、来源、操作原因等枚举必须完整，不得遗漏 `null`、未知或历史兼容值。
- 时间戳写清秒或毫秒；金额、距离、时长等写清单位。

## 文件命名

使用业务语义明确的英文 kebab-case：

```text
<system-or-domain>-<resource-or-capability>-<operation-set>.openapi.json
```

规则：

- 合并同一业务域的相关接口，使用能覆盖全部接口的最小上位概念。
- 只有一个接口时可用“领域 + 动作”，例如 `drone-detail.openapi.json`。
- 不把 HTTP 方法、日期、开发者姓名或 `new`、`final` 写入文件名。
- 范围跨多个无关业务域时先请求拆分，不制造含糊的大文件名。

## 禁止项

- `components`
- `schemas` 独立模型区
- `$ref`
- `security`、`securitySchemes`
- Authorization、Token、AppId、AppKey、sign 等鉴权参数
- 除 `200` 外的任何响应状态
- 用户未指定范围内的接口
