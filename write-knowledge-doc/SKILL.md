---
name: write-knowledge-doc
display_name_zh: 写知识文档
display_name_en: Knowledge Doc Writer
description: "把技术知识沉淀成可检索的知识文档，并负责读懂与修订已有文档。三条链：生成（一篇一个概念，按「1. 它解决什么问题 → 2. 它怎么解决的 → 3. 一个具体场景 → 4. 边界与例外 → 5. 相关概念」骨架成文，frontmatter 用 kind 定模式、status 定成熟度、verified 定核实状态、applies_to 定适用版本与环境）、理解（只凭文档回答读者问题，同时充当生成链的验收）、编辑（改事实、补章节、拆分合并、更新状态与链接）。当用户要求整理知识、整理笔记、写知识文档、消化陌生概念、把资料或链接沉淀进知识库，或要求「这篇讲了什么」「能不能照着做」「改一下这篇条目」「拆成两篇」时使用——即使没明说「文档」，只要意图是把一类知识沉淀成可检索文档、读懂它或修订它，就应触发。"
description_en: "Turn technical knowledge into searchable knowledge documents, and read or revise existing ones. Three chains: generate (one concept per entry, written on a fixed five-section skeleton — problem, solution, concrete scenario, boundaries, related concepts — with frontmatter for kind, status, verified, and applies_to), understand (answer reader questions from the document alone; also serves as acceptance for the generate chain), and edit (revise facts, add sections, split or merge entries, update status and links). Use when the user asks to organize knowledge or notes, write a knowledge doc, digest an unfamiliar concept, or file materials and links into a knowledge base; also when they ask what a given entry says, whether they can follow it, or to revise or split an existing entry. Trigger even if the word “document” never appears, as long as the intent is to turn a class of knowledge into a searchable document, understand it, or revise it."
version: v20261028
---

# 写知识文档

把技术知识沉淀成一篇文档，让它同时服务两个人：人（快速理解陌生概念）和 AI（检索时拿到准确、自包含的答案）。唯一判据是**自包含性**——读者只读这一篇，能否独立理解这个概念。

## 任务路由

| 用户要什么 | 走哪条链 | 读 |
|---|---|---|
| 整理知识、写条目、把资料或链接沉淀进库 | 生成 | [generate.md](generate.md) |
| 「这篇讲了什么」「这个点是什么」「能不能照着做」「帮我验一下能不能看懂」 | 理解 | [understand.md](understand.md) |
| 「改一下」「补一节」「拆成两篇」「合并」「更新状态或链接」 | 编辑 | [edit.md](edit.md) |
| 判断不出是哪条 | 先问一句：要新写、要读懂、还是要改 | — |

三条链只共享三样东西：本文的判据、[references/skeleton.md](references/skeleton.md) 的骨架契约、`scripts/` 的校验。

## 两种模式

模式写在 frontmatter 的 `kind` 字段里，不靠「有没有 frontmatter」推断：

| kind | 用途 | 编号体系 |
|---|---|---|
| `entry`（默认） | 一篇一个概念，多篇积累、彼此无顺序 | H2 阿拉伯 `1.`~`5.`，H3 `x.y` |
| `system` | 调研报告、领域综述、多主题成体系文档 | H2 中文数字 `一、二、`，H3 `x.y` |

`kind: system` 只在用户明确要求调研报告或成体系文档时使用。判断标准：知识点是**一个概念**，还是一个**多主题领域**。横跨两者时（「把调研结果整理成一篇能查的文档」）先说明差别再确认。

## 三条链的门禁

| 链 | 进下一步之前必须有 |
|---|---|
| 生成 | 知识点与篇边界经用户确认 → 骨架经用户确认 → 校验 error 清零 → 理解链验收通过 |
| 理解 | 只凭文档作答，不用文档外知识补全 |
| 编辑 | 改动类型已判定 → slug 不动 → `updated`、`status`、`verified`、`applies_to` 与改动一致 → 校验 error 清零 |

任一门禁不满足就停下说明缺什么。不要边做边补，也不要用下一阶段的产物倒推上一阶段的判断。

## 不适用

教程、操作手册、API 参考这类「照着做」的文档，以及带目录树的产品文档体系——它们的目标读者是执行者，不是检索者。这类需求走文档写作或 office 相关能力，不要套本骨架。
