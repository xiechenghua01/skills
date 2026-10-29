---
name: skill-development
display_name_zh: 技能开发
display_name_en: Skill Development
description: "新建、编辑与理解 Agent Skill。用户要求把流程整理成 skill、编写 SKILL.md、完善技能的触发条件/工作流/脚本/测试，或分析已有技能的用途、实现与缺陷时使用。清晰需求直接推进，理解默认只读；普通业务开发、一般文档写作、执行其他技能的业务任务不触发。"
description_en: "Create, edit, and understand Agent Skills. Use for turning a workflow into a skill, writing SKILL.md, improving skill triggers, workflows, scripts or tests, and explaining or reviewing existing skills. Proceed on clear requirements; inspection is read-only by default. Not for ordinary application development, general documentation, or performing another skill's business task."
version: v20261029
---

# 技能开发

## 任务路由

| 用户意图 | 读取 |
|---|---|
| 新建 skill、将流程整理成技能、先出创建方案 | [create.md](create.md) |
| 修改或完善已有 skill、修触发或脚本、补测试 | [edit.md](edit.md) |
| 解释 skill、追踪实现、审阅问题、不要求改动 | [understand.md](understand.md) |

已有目标、范围和交付物直接使用，不重复访谈。明确只要方案时不写实现；理解不自动转编辑。
先解释再修改的复合任务，完成只读判断后按已有授权进入编辑；不强求一句请求只能包含一个意图。
共享字段和证据状态以 [contracts.md](references/contracts.md) 为准；细节按各链条件读取，不预读全部参考。
安装、提交、推送、外部发布与生产操作不包含在开发授权中；不得自动执行。
