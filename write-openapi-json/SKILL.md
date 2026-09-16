---
name: write-openapi-json
description: 根据用户指定的接口或业务范围，从实际代码和现有文档生成、补充或审阅 OpenAPI 3.1 JSON；遵循内联字段格式，自动按范围命名 *.openapi.json，完整描述真实请求和响应字段，且不写 components、鉴权、独立数据模型、$ref 或非 200 响应。用户要求编写 OpenAPI、Apifox 导入文件、接口契约 JSON、补充接口返回字段或按代码整理接口文档时使用。
---

# Write OpenAPI JSON

按用户指定范围生成可导入 Apifox 的 OpenAPI JSON，并以代码实际行为作为契约依据。

## 0. 先锁定文件归属和接口清单（硬性）

在读代码和写文件前，先形成一张接口清单，至少包含：业务域、目标 OpenAPI 文件、HTTP 方法、路径、Controller 方法、Request 场景、请求参数来源、最终响应构造位置。

- 用户指定“单独文件”时，目标接口只能写入该文件，不能追加到已有总文件或 `regulatory-approval.openapi.json`。
- 用户指定“合并到一个文件”时，相关业务域只能合并到这一份文件，不得为每个业务域另建重复文件。
- 将接口从旧文件迁移到新文件时，必须同时从旧文件删除，并检查旧文件和新文件不存在重复路径。
- 写入前后都要打印并核对路径清单；文件数量、路径数量、HTTP 方法必须与清单一致。
- 结构校验通过不代表范围正确；写入了错误文件属于失败，必须在交付前单独检查。

## 必读资源

1. 写文件前完整阅读 [references/format-guide.md](references/format-guide.md)。
2. 需要骨架时复制 [references/minimal-example.openapi.json](references/minimal-example.openapi.json) 的结构，只替换业务内容，不复制示例业务字段。
3. 写完后必须运行 `python3 scripts/validate_openapi.py <输出文件>`。
4. 写接口范围包含 JSON Body 或 multipart/form-data 请求体时，必须再运行 `python3 scripts/validate_openapi_request_contract.py <输出文件>`，检查字段中文说明、完整请求示例和嵌套结构。
5. 写完后必须运行 `python3 scripts/validate_openapi_response_contract.py <输出文件>`，审计 200 响应的字段中文说明、业务含义、const 示例一致性和响应 schema 完整性。

## 工作流

### 1. 锁定范围和事实来源

- 将用户指定的接口、模块、变更范围列成清单，只写清单内的接口。
- 范围包含互不相关的业务域或边界不明确时，先询问用户是否拆分文件。
- 先读仓库规范和已有 OpenAPI，再沿真实调用链检查路由、Controller、Request、Service、Model、资源转换器和响应封装。
- 对“当前有改动的接口”同时检查 Git diff 和当前完整代码，不能只看 diff。
- 列表和详情响应必须追踪最终返回值，完整展开实际字段、嵌套对象、分页字段和可空字段，禁止用简单占位结构代替。
- 代码和需求冲突或动态返回字段无法确认时，指出差异并询问；不要猜测不存在的字段、状态或业务规则。
- POST、PUT、PATCH、DELETE 的 JSON 参数必须追踪 `Request` 对应的 `scene`、`validated()` 和 Controller 传入 Service 的字段，不能只看 Controller 方法名。
- 新增接口时必须检查完整调用链：路由属性、Controller、Request 场景和规则、Service、Model/Resource/格式化方法、响应封装。

### 2. 按业务范围命名

- 用户明确指定文件名时保留其业务含义，并规范化为小写英文 kebab-case，确保以 `.openapi.json` 结尾；只有用户明确要求原样保留时才不规范化。
- 未指定时，将业务范围归纳为简短英文 kebab-case，生成 `<business-scope>.openapi.json`。
- 优先使用“系统或领域 + 资源或能力 + 操作集合”，例如：
  - 航空器制造系统的航空器操作：`aero-manufacture-drone-operations.openapi.json`
  - 飞行计划统计：`flight-plan-statistics.openapi.json`
  - 用户权限管理：`user-permission-management.openapi.json`
- 不使用 `openapi.json`、`api.openapi.json`、`new.openapi.json` 等无法表达范围的名称。
- 用户未指定目录时，仓库存在 `doc/` 则写入 `doc/`，否则写入当前文档目录。
- 文件名必须能表达合并后的全部业务范围，不能沿用只覆盖其中一个资源的旧文件名。

### 3. 按固定格式编写

- 使用 OpenAPI `3.1.0` 和两空格 JSON 缩进，文件末尾保留换行。
- 顶层按 `openapi`、`info`、`tags`、`paths`、`webhooks`、`servers` 排列；固定写入空的 `webhooks: {}` 和 `servers: []`。
- 每个操作按 `summary`、`deprecated`、`description`、`tags`、`parameters`、`requestBody`、`responses` 排列；没有参数也写 `parameters: []`。
- 查询和路径参数直接内联到 `parameters`；JSON 请求体直接内联到 `requestBody.content.application/json.schema`；multipart 文件/表单请求体内联到 `requestBody.content["multipart/form-data"].schema`。媒体类型按接口真实读取参数的方式判定（见 3.2），不按脚本假定的形态声明。
- 只写 `200` 响应。每个 `200` 响应都必须完整内联 schema；仅返回空 `data` 的操作接口也必须写 schema，可同时保留完整响应 example。
- 准确声明 `type`、`required`、`enum`、`minimum`、`maxLength`、`pattern`、`example` 和条件校验。可空字段使用 OpenAPI 3.1 的类型数组，例如 `"type": ["string", "null"]`。
- 状态字段必须写清字段名称和全部值含义；必要时同时写 `title`。例如描述应为“UOM实名登记状态：0-正常……”，不能只写“0-正常……”。
- 时间字段写清 Unix 秒或毫秒、UTC 或本地时间；单位字段写清单位。
- 保留接口真实字段名和现有拼写，即使代码字段拼写不标准，也只能在描述中说明，不能擅自改名。

### 3.1 请求参数、中文说明和示例（硬性）

- 查询参数和路径参数写入 `parameters`；每个参数必须有中文 `description`、`schema` 和可直接使用的 `example`。没有查询/路径参数的操作才写 `parameters: []`。
- JSON 请求体字段只能写入 `requestBody.content.application/json.schema.properties`，不能为了让 UI 显示而把 Body 字段伪装成 `parameters`。
- 每个 JSON Body 操作必须同时具备：`requestBody.required: true`、内联 `schema.type: object`、完整 `properties` 和 `required`、媒体类型级 `example`，以及每个 Body 字段自己的 `example` 和中文 `description`。
- 完整请求示例必须放在 `requestBody.content.application/json.example`；禁止只写 `requestBody.example`，也不能只写 `schema.example` 代替媒体类型级示例。
- `requestBody.content.application/json.example` 必须是完整请求对象，字段集合与 `schema.properties` 一致，包括可选字段；可选字段使用真实值或 `null`。
- 中文 `description` 不能只写字段英文名或类型；必须说明业务含义、单位、格式、枚举、长度、是否可为空及条件必填规则。条件必填要说明触发条件，并在 OpenAPI 允许时用 `if`/`then` 补充。
- 校验相关的描述必须从 Request、Service 实际代码提炼，写清真实校验条件与失败提示（如文件类型、大小上限、路径前缀和超限时的提示文案），不能凭印象编写校验规则。
- 可空字段和数组字段要写清 `null`、空数组、缺省三种情况在新增与编辑场景下的差别（如“新增时不传按 0 处理，编辑时传 null 表示清空”）。
- 嵌套对象和数组项同样必须有中文说明。附件必须展开路径、大小、上传时间等字段；等级选项必须展开 `value`、`label`；不得只写 `items: {}` 或只描述数组本身。
- 示例值必须通过代码规则：身份证号符合校验码、日期范围合法、执照编号符合正则、附件扩展名和大小上限符合规则、路径前缀符合约定、数值满足最小值和单位。示例不得使用加密值、摘要、Token 或真实敏感数据。
- 参考已有接口时只复用字段说明风格和响应封装，不复制与当前接口不一致的字段、空参数或旧业务模型。

### 3.2 媒体类型判定与冲突处理（硬性）

- 写 `requestBody` 前先沿路由、Controller、Request、Service 确认接口真实读取参数的方式：JSON body、multipart 文件、表单，还是没有请求体，再决定声明的媒体类型；判定依据不明确时，在交付说明中写清判断过程和代码出处。
- 接口真实同时支持多种媒体类型时才同时声明多种，并在 `description` 中说明各形态的差异（如字段集合、解析方式的区别）；只支持一种时按真实情况声明。仅为通过校验补写的 `application/json` 镜像会让契约与实现不一致——接口并不接受 JSON 请求体，调用方按镜像传参会直接失败——确需补写时必须先自行判断副作用并在交付说明中说明原因。
- 校验脚本对 `requestBody` 报错时，先区分两种情况再动手：一是契约确实写漏或写错，按常规流程修复；二是接口本身不属于脚本假定的形态（例如纯 multipart 文件上传、表单、纯二进制请求体）。属于后者时，保留与代码一致的真实契约，在交付说明中写清未通过项、原因和结论，不要为了通过校验引入与真实行为不符的结构。
- multipart/form-data 请求体已被两个校验脚本直接支持，按真实形态声明即可，不需要镜像 JSON；文件字段使用 `type: "string"` + `format: "binary"`，完整写法参考 [references/format-guide.md](references/format-guide.md) 的「multipart 上传请求体」。其他非 JSON 请求体（表单、纯二进制等）脚本仍会报缺少 `application/json`，按上一条的冲突流程处置。

### 3.3 响应字段清单与对账（硬性）

- 写文件前，为每个接口建立"响应字段清单"，来源至少包括：Model 的 `$fillable`、`$appends`、`$hidden`、`$casts`，关联关系方法的 select 列，格式化/Resource/序列化方法附加的字段，以及分页器元数据（`current_page`、`per_page`、`total` 等）。
- `$hidden` 字段、格式化方法重命名的字段、按场景裁剪的字段都要在清单中登记，不能凭印象跳过。
- 写文件后逐接口把 JSON `properties` 字段集合与清单对账：清单中的每个字段要么出现在 JSON 中，要么逐条解释差异（如 `$hidden` 不输出、字段拆分到其他接口按需查询）。
- 不允许静默缺失：对不上账的字段必须补写，或在交付说明中逐条说明原因；关联对象禁止用空对象占位代替真实字段。

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

2. 运行请求契约审计：

   ```bash
   python3 <skill-dir>/scripts/validate_openapi_request_contract.py <输出文件>
   ```

   该审计会检查每个 JSON Body 或 multipart/form-data 操作的 `requestBody`、`schema.properties`、`required`、媒体类型级 `example`、字段级 `example`、中文 `description`、参数示例和嵌套数组结构；multipart 请求体还要求至少一个 `format: binary` 文件字段且其 `type` 为 string。
   它还会检查所有 HTTP 操作的 query/path 参数、`required` 中的未知或重复字段，以及 Body 字段是否被重复放入 `parameters`；同一操作同时声明 application/json 与 multipart/form-data 时会提示核对接口是否真实支持两种形态。

3. 运行响应契约审计：

   ```bash
   python3 <skill-dir>/scripts/validate_openapi_response_contract.py <输出文件>
   ```

   该审计会递归检查每个操作 `200` 响应 schema：properties 成员、items、oneOf/anyOf/allOf 分支的中文 description 和业务含义，`const` 字段 example 的类型与值一致性，以及媒体类型只有 example 没有 schema 的问题。

   结构校验、请求契约审计、响应契约审计三步全部通过才算交付；任何一步失败，修复后必须重跑全部三步。

4. 对每个写操作做人工请求契约复核，不能只看结构校验：
   - POST、PUT、PATCH、DELETE 若有 JSON Body 或 multipart/form-data 请求体，确认 `requestBody`、`schema.properties`、`required` 和媒体类型级 `example` 同时存在；multipart 的文件字段必须是 `type: "string"` + `format: "binary"`。
   - 确认媒体类型级 `example` 的字段集合与 `schema.properties` 一致，每个字段都有 `example` 和包含中文字符的 `description`。
   - 递归检查数组和嵌套对象：字段有结构时不得出现空 `items`，每个嵌套字段都有中文说明。
   - 确认所有 `parameters` 都有中文 `description` 和示例值；无参数的操作必须是代码真实无参数，而不是漏写。
   - 对照 Request 场景逐个核对字段、条件必填、可空、枚举、格式和示例值。
5. 对照范围清单和响应字段清单（见 3.3）逐个确认路径、方法、请求字段、响应字段、枚举、必填和可空定义。
6. 搜索并确认不存在 `components`、`security`、`securitySchemes`、`$ref` 和非 `200` 响应。
7. 检查文件名能准确表达用户指定范围，并确认旧文件没有残留或重复路径。
8. 最终说明输出路径、覆盖接口、请求体示例位置、验证结果和仍无法从代码确认的缺口。

### 常见失败复盘

- 响应字段漏写：接口实际返回 22 个顶层字段，文档只写了 10 个，关联对象只留空对象占位。根因：没有先从 Model 与格式化代码反推响应字段清单并与 JSON 对账，只凭旧文档和印象写字段。
- 响应字段缺中文说明：156 处响应字段、数组项和 oneOf 分支没有中文 description，7 处 code 的 example 是与 const 类型不一致的字符串，还有响应只写 example 不写 schema。根因：请求侧有自动审计而响应侧只靠人工自觉，缺失长期无人发现。
- 只把字段放入 `schema.properties`，没有 `application/json.example`：结构校验可能通过，但 Apifox 的请求示例仍为空。
- 只写英文类型、没有中文 `description`：字段“存在”不等于接口文档可用，必须逐字段说明。
- 把 JSON Body 字段写进 `parameters`：这不符合 OpenAPI 语义；Body 应放 `requestBody`，但必须补媒体类型级完整示例。
- 复用旧总文档并把新接口追加进去：会造成业务域归属错误或重复路径；先确定目标文件，再迁移并清理旧文件。
- 文件上传接口为通过校验补写 `application/json` 镜像：接口真实只接受 multipart/form-data，镜像与实现不符，调用方按 JSON 传参会直接失败。根因：没先按 3.2 判定接口真实读取参数的方式，顺着脚本报错改契约。现在两个脚本都直接支持 multipart 请求体，按真实媒体类型声明即可通过。
- 用 `items: {}` 省略关联对象：会让响应看似完整但实际无法导入字段，只有代码无法确定结构时才允许。

不要声称 Apifox 导入成功，除非实际执行过导入验证。
