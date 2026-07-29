---
name: write-openapi-json
description: 根据用户指定的接口或业务范围，从实际代码和现有文档生成、补充或审阅 OpenAPI 3.1 JSON；遵循内联字段格式，自动按范围命名 *.openapi.json，完整描述真实请求和响应字段，且不写 components、鉴权、独立数据模型、$ref 或非 200 响应。用户要求编写 OpenAPI、Apifox 导入文件、接口契约 JSON、补充接口返回字段或按代码整理接口文档时使用。
---

# Write OpenAPI JSON

按用户指定范围生成可导入 Apifox 的 OpenAPI JSON，并以代码实际行为作为契约依据。

## 必读资源

1. 写文件前完整阅读 [references/format-guide.md](references/format-guide.md)。
2. 需要骨架时复制 [references/minimal-example.openapi.json](references/minimal-example.openapi.json) 的结构，只替换业务内容，不复制示例业务字段。
3. 写完后必须运行 `python3 scripts/validate_openapi.py <输出文件>`。

## 工作流

### 1. 锁定范围和事实来源

- 将用户指定的接口、模块、变更范围列成清单，只写清单内的接口。
- 范围包含互不相关的业务域或边界不明确时，先询问用户是否拆分文件。
- 先读仓库规范和已有 OpenAPI，再沿真实调用链检查路由、Controller、Request、Service、Model、资源转换器和响应封装。
- 对“当前有改动的接口”同时检查 Git diff 和当前完整代码，不能只看 diff。
- 列表和详情响应必须追踪最终返回值，完整展开实际字段、嵌套对象、分页字段和可空字段，禁止用简单占位结构代替。
- 代码和需求冲突或动态返回字段无法确认时，指出差异并询问；不要猜测不存在的字段、状态或业务规则。

### 2. 按业务范围命名

- 用户明确指定文件名时保留其业务含义，并规范化为小写英文 kebab-case，确保以 `.openapi.json` 结尾；只有用户明确要求原样保留时才不规范化。
- 未指定时，将业务范围归纳为简短英文 kebab-case，生成 `<business-scope>.openapi.json`。
- 优先使用“系统或领域 + 资源或能力 + 操作集合”，例如：
  - 航空器制造系统的航空器操作：`aero-manufacture-drone-operations.openapi.json`
  - 飞行计划统计：`flight-plan-statistics.openapi.json`
  - 用户权限管理：`user-permission-management.openapi.json`
- 不使用 `openapi.json`、`api.openapi.json`、`new.openapi.json` 等无法表达范围的名称。
- 用户未指定目录时，仓库存在 `doc/` 则写入 `doc/`，否则写入当前文档目录。

### 3. 按固定格式编写

- 使用 OpenAPI `3.1.0` 和两空格 JSON 缩进，文件末尾保留换行。
- 顶层按 `openapi`、`info`、`tags`、`paths`、`webhooks`、`servers` 排列；固定写入空的 `webhooks: {}` 和 `servers: []`。
- 每个操作按 `summary`、`deprecated`、`description`、`tags`、`parameters`、`requestBody`、`responses` 排列；没有参数也写 `parameters: []`。
- 查询和路径参数直接内联到 `parameters`；JSON 请求体直接内联到 `requestBody.content.application/json.schema`。
- 只写 `200` 响应。返回业务数据时完整内联响应 schema；仅返回空 `data` 的操作接口可使用完整响应 example。
- 准确声明 `type`、`required`、`enum`、`minimum`、`maxLength`、`pattern`、`example` 和条件校验。可空字段使用 OpenAPI 3.1 的类型数组，例如 `"type": ["string", "null"]`。
- 状态字段必须写清字段名称和全部值含义；必要时同时写 `title`。例如描述应为“UOM实名登记状态：0-正常……”，不能只写“0-正常……”。
- 时间字段写清 Unix 秒或毫秒、UTC 或本地时间；单位字段写清单位。
- 保留接口真实字段名和现有拼写，即使代码字段拼写不标准，也只能在描述中说明，不能擅自改名。

### 4. 严格排除非目标内容

- 不写 `components`、`components.schemas`、`components.responses` 或任何独立数据模型区块。
- 不写 `$ref`；请求和响应字段全部放在对应操作内。
- 不写 `security`、`securitySchemes`、Authorization、Token、AppId、签名等鉴权声明或请求头。
- 不写 `401`、`403`、`404`、`422`、`500`、`default` 等响应，只保留 `200`。
- 不因“完整”而加入用户范围外的接口、公共组件或推测字段。

### 5. 校验和交付

1. 运行结构校验：

   ```bash
   python3 <skill-dir>/scripts/validate_openapi.py <输出文件>
   ```

2. 对照范围清单逐个确认路径、方法、请求字段、响应字段、枚举、必填和可空定义。
3. 搜索并确认不存在 `components`、`security`、`securitySchemes`、`$ref` 和非 `200` 响应。
4. 检查文件名能准确表达用户指定范围。
5. 最终说明输出路径、覆盖接口、验证结果和仍无法从代码确认的缺口。

不要声称 Apifox 导入成功，除非实际执行过导入验证。
