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
- `summary` 会成为 Apifox 里的接口名（优先级 `summary` > `operationId` > 路径），所以它必须是人能读的业务名，不能是 Controller 方法名或英文动词短语。

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
- 先按接口真实读取参数的方式确定媒体类型：JSON body 用 `application/json`，文件/表单上传用 `multipart/form-data`（见下节）。不为了通过校验声明接口不接受的媒体类型；判定方法与冲突处理见本文《媒体类型判定》。
- 校验相关的描述从 Request、Service 实际代码提炼，写清真实校验条件与失败提示；可空字段、数组字段写清 `null`、空数组、缺省在新增与编辑场景下的差别。
- 条件必填可以使用 OpenAPI 3.1 的 `if`、`then`、`allOf`。
- 多个典型请求场景时，媒体类型级可以用 `examples` 命名多组；字段级一律用单值 `example`，不要写成数组形式（理由见《为什么这样约束》）。
- `schema.properties` 中的每个请求字段必须有中文 `description` 和字段级 `example`；媒体类型级 `example` 必须覆盖全部字段，包括可选字段。
- 媒体类型级 `example` 用于 Apifox/Swagger UI 直接展示完整传参；不能只写字段结构而省略完整请求示例。
- 完整示例必须位于 `content.application/json.example`，不能放在 `requestBody.example`，也不能用 `schema.example` 替代。
- `parameters` 只放 query/path 参数；不要把 JSON Body 字段复制到 `parameters`。`parameters: []` 只表示接口确实没有 query/path 参数，不能表示遗漏了 `requestBody`。

## 媒体类型判定

写 `requestBody` 之前，先沿路由 → Controller → Request → Service 确认接口**真实怎么接收参数**，再决定声明哪种媒体类型。

| 代码里的迹象 | 应声明的媒体类型 |
|---|---|
| Request 定义了 `rules()`/`scene()` 的字段规则，Controller 用 `$request->input()` / `validated()` | `application/json` |
| Controller 用 `$request->file()` / `$request->hasFile()`，Request 没有 JSON body 规则 | `multipart/form-data` |
| 只读 `$request->all()` 且是表单提交 | 表单形态，按真实情况声明 |
| 直接读 `php://input` 原始流 | 纯二进制，按真实情况声明 |

三条纪律：

1. **接口真实同时支持多种形态时才同时声明多种**，并在 `description` 里说明各形态的字段差异；只支持一种就只写一种。
2. **不为了通过校验补 `application/json` 镜像**。接口不接受 JSON 请求体时，镜像会让调用方按错误方式传参并直接失败。这是已发生过的事故，见 pitfalls 第 7 条。
3. **脚本报错时先分类再动手**：是契约写漏/写错，就修契约；是接口本来不属于脚本假定的形态（纯 multipart、表单、纯二进制），就保留与代码一致的真实契约，在交付说明里写清未通过项、原因与结论。

判定依据不明确时，在交付说明里写出判断过程和代码出处，不要凭接口名猜。

---

## multipart 上传请求体

Controller 通过 `$request->file(...)`、`$request->hasFile()` 等读取文件、Request 未定义 JSON body 规则时，接口属于 multipart 上传，请求体声明为 `multipart/form-data`。这类接口通常按下面的结构写：

```json
{
  "required": true,
  "content": {
    "multipart/form-data": {
      "schema": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "format": "binary",
            "description": "上传的 PDF 资格证明文件，必填，仅接受 PDF 格式，单个不超过 10MB，超出时提示 文件大小超出限制",
            "example": "qualification-certificate.pdf"
          },
          "remark": {
            "type": [
              "string",
              "null"
            ],
            "description": "文件备注，说明文件用途或有效期等附加信息，可选，不传或传 null 时不记录备注",
            "example": "2026 年度资质审核用"
          }
        },
        "required": [
          "file"
        ]
      },
      "example": {
        "file": "qualification-certificate.pdf",
        "remark": "2026 年度资质审核用"
      }
    }
  }
}
```

这是这类接口的常见写法参考，不是唯一强制模板；字段集合、校验规则以代码实际读取为准：

- `requestBody.required: true`，`schema.type: object`；`schema.required` 与 Request 校验规则对应：Request 中声明必填的字段（如文件字段的 `required` 规则）列入 `required`，条件必填在字段 `description` 写清触发条件。
- 文件字段使用 `type: "string"` + `format: "binary"`；多文件上传使用 `type: "array"`，并在 `items` 内声明 `type: "string"` + `format: "binary"`。
- 文件字段的中文 `description` 写清字段业务名称、允许的文件类型、大小上限、是否必填，以及超限或类型不符时的真实失败提示；从 Request、Service 代码提炼，不凭印象编写校验条件。
- 文件字段的字段级 `example` 使用符合规则的文件名（含扩展名），不使用二进制内容、加密值或真实敏感文件。
- 除文件外的普通表单字段（如备注、场景标识、关联 ID）一并写入 `properties` 并给出中文说明和字段级 `example`，`required` 按真实规则。
- 媒体类型级 `example` 是完整表单对象，放在 `content["multipart/form-data"].example`，字段集合与 `schema.properties` 一致，包括可选字段；文件字段的示例值用文件名。
- 这类接口通常只声明 `multipart/form-data`；接口真实不接受 JSON 请求体时不补 `application/json` 镜像，理由见本文《媒体类型判定》与 pitfalls 第 7 条。

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

只返回空数据的操作接口也必须内联 schema，可以同时保留完整响应 example：

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
              "example": 200,
              "description": "HTTP业务响应码，成功固定为 200"
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
              "type": "array",
              "description": "操作接口无业务数据，固定返回空数组"
            }
          },
          "required": [
            "code",
            "trace_id",
            "message",
            "data"
          ]
        },
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
- 写响应 schema 前，先建立响应字段清单：Model 的 `$fillable`、`$appends`、`$hidden`、`$casts`，关联关系 select 列，格式化/Resource 方法附加字段，分页器元数据。写完后逐接口把 `properties` 字段集合与清单对账；`$hidden` 不输出、字段拆分到其他接口等差异必须逐条解释，不允许静默缺失。
- `200` 响应的每个字段、数组项和 oneOf/anyOf/allOf 分支都必须有包含业务含义的中文 `description`，说明单位、枚举、可空等信息；不能只重复字段英文名，也不能只写"字段"等通用词。
- 有 `const` 的字段必须带 `example`，且 `example` 的类型和值与 `const` 完全一致；例如 `const: 200` 时 `example` 必须是整数 `200`，不能是字符串 `"200"`。
- `200` 响应必须内联 `schema`；只写媒体类型级 `example` 而不写 `schema` 属于缺失，无法导入字段结构。

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

## 可空、必填、缺省是三件事

| 概念 | 由谁表达 | 回答的问题 |
|---|---|---|
| 是否必填 | `required` 数组 | 这个字段必须出现吗 |
| 是否可为 null | 类型数组，如 `["string", "null"]` | 出现时值可以是 null 吗 |
| 缺省行为 | `description`（必要时加 `default`） | 不传时按什么处理 |

三者混用是最常见的描述错误：把「可以不传」写成「可空」，或把「可空」写成「非必填」。三者都要分别声明，并写清新增与编辑场景的差别——例如「新增时不传按 0 处理，编辑时传 null 表示清空，编辑时不传表示不修改」。

---

## 文件与编码

- UTF-8，**不带 BOM**：带 BOM 会让 JSON 解析器直接抛 `Unexpected UTF-8 BOM`。
- 两空格缩进，**文件末尾保留一个换行**。
- 不允许尾随逗号，不允许 Tab 缩进——严格解析会直接拒绝，报错信息通常不指向根因。

---

## 为什么这样约束

三条冻结决策，被质疑过多次，结论已定：

| 约束 | 理由 |
|---|---|
| 不写 `components` / `$ref`，字段全部内联 | 每份契约按业务域独立维护、独立导入；抽公共模型会让单文件失去自解释性，也让「哪份文件覆盖哪些接口」变模糊 |
| 只写 `200` 响应 | 契约的用途是导入 Apifox 生成接口条目，错误码由实现侧业务约定表达；写进契约只会与真实行为脱节 |
| 字段级示例用单值 `example`，不用 `examples` 数组 | 3.1 把 `schema.example` 标为 deprecated、推荐 `examples` 数组，但现行契约已按 `example` 全量导入验证；换数组的导入效果未验证，收益为零、风险非零 |

要动这三条，先做一次真实导入验证，再同步修改本文件与 pitfalls 的冻结决策，不要只改一处。

---

## 禁止项

- `components`
- `schemas` 独立模型区
- `$ref`
- `security`、`securitySchemes`
- Authorization、Token、AppId、AppKey、sign 等鉴权参数
- 除 `200` 外的任何响应状态
- 用户未指定范围内的接口
