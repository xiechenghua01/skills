---
name: write-openapi-json
display_name_zh: 编写接口契约
display_name_en: Write OpenAPI JSON
description: "按用户指定范围，从真实代码生成、修订或审阅可导入 Apifox 的 OpenAPI 3.1 JSON：字段全部内联、不写 components 与 $ref、只写 200 响应、每个字段带中文说明与示例；修订链支持单文件内改字段与跨文件迁移合并，审阅模式只出问题清单不改文件。用户要求编写 OpenAPI、Apifox 导入文件、接口契约 JSON、补充接口返回字段、按代码整理接口文档或审阅已有契约时使用。"
description_en: "Generate, revise, or review Apifox-importable OpenAPI 3.1 JSON from real code within the scope the user names: everything inlined, no components or $ref, 200 responses only, and Chinese descriptions plus examples on every field. The edit chain covers single-file field changes and cross-file moves or merges; review mode reports issues without touching files. Use when the user asks to write OpenAPI, build an Apifox import file, author an API contract JSON, add missing response fields, document endpoints from code, or review an existing contract."
version: v20261028
---

# 编写接口契约

按用户指定范围，把代码的真实行为写成可导入 Apifox 的 OpenAPI 3.1 JSON。**契约以代码为准，不以旧文档或印象为准。**

## 任务路由

| 用户要什么 | 走哪条链 | 读 |
|---|---|---|
| 新建契约文件、补一批接口、按代码整理接口文档 | 生成 | [generate.md](generate.md) |
| 改已有契约的字段/描述/schema/路径，或挪到别的文件、合并拆分 | 编辑 | [edit.md](edit.md) |
| 只审阅、先出问题清单、别动文件 | 编辑 · 诊断 | [edit.md](edit.md) |
| 判断不出 | 先问一句：新建文件，还是在已有文件上改 | — |

## 硬约束

唯一真相源是 [references/format-guide.md](references/format-guide.md)（约束理由见其中《为什么这样约束》）；踩过的坑见 [references/pitfalls.md](references/pitfalls.md)。最容易违反的六条：

1. 只写 `200` 响应；不写 `components`、`$ref`、`security`、鉴权头；字段全部内联，不抽公共模型。
2. 每个字段都要有中文 `description` 和一个 `example`；枚举写全值含义。
3. 完整请求示例在媒体类型级 `example`，不是 `requestBody.example`，也不是 `schema.example`。
4. 请求体媒体类型按代码真实读取方式判定，不为了过校验补 JSON 镜像。
5. 响应字段必须与从 Model、Resource、分页器反推的字段清单逐条对账。
6. 描述要写业务含义、单位、枚举、条件必填，不能只重复字段英文名。

## 两条链的门禁

| 链 | 进下一步之前必须有 |
|---|---|
| 生成 | 范围清单已锁定（文件 + 方法 + 路径）→ 调用链已追踪到响应构造处 → 三个脚本全过 → 交付说明写明缺口 |
| 编辑 | 改前基线已记录 → 只改命中范围 → 改后报错不多于基线 → 迁移后旧文件无残留路径 |

## 三条不可退让

1. **不确定就问**：代码与需求冲突、动态字段无法确认时，指出差异并询问，不猜字段、不猜状态。
2. **校验不过不许改契约迎合脚本**：先分清是契约写错，还是接口本来就不是脚本假定的形态。
3. **没实际导入过 Apifox，就不说「导入成功」**。

## 不适用

接口实现、鉴权方案、Mock 数据、压测脚本、SDK 生成——不归本技能。
