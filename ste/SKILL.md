---
name: ste
display_name_zh: 简化技术中文
display_name_en: STE
description: "基于 ASD-STE100 本土化的简化技术中文（STE-ZH）受控写作与审查规范。三条链：生成（按需求下发、代码注释、ADR、汇报四种文体写受控文本）、理解（只诊断出违规清单不改）、编辑（按清单改写并复检）。分 pragmatic 与 strict 两档强度。用户输入触发词 ste、STE，或要求使用简化技术中文、消除需求歧义、规范代码注释与错误断言、写定量 ADR、输出执行与验证解耦的汇报、审阅技术文本时使用。"
description_en: "Controlled writing and review rules for Simplified Technical Chinese (STE-ZH), localized from ASD-STE100. Three chains: generate (write controlled text for requirements, code comments, ADRs, and reports), understand (diagnose violations without editing), and edit (rewrite from the issue list and re-check). Two strength levels: pragmatic and strict. Trigger when the user types ste or STE, or asks for simplified technical Chinese, ambiguity-free requirements, standardized code comments and error assertions, quantified ADR decisions, reports that separate execution from verification, or a review of technical prose."
version: v20261028
---

# 简化技术中文（STE-ZH）

把技术文本编译成受控语言：一词一义、主动语态、一事一句、执行态与验证态分离。目标是消除歧义，不是让文字好看。规则条文见 [references/rules.md](references/rules.md)（R1–R25，编号以该文件为准）。

## 任务路由

| 用户要什么 | 走哪条链 | 读 |
|---|---|---|
| 用 STE 写需求、注释、ADR、汇报 | 生成 | [generate.md](generate.md) |
| 审阅已有文本，只出违规清单 | 理解（只诊断，不改） | [understand.md](understand.md) |
| 按 STE 改写已有文本 | 编辑 | [edit.md](edit.md) |
| 判断不出 | 先问：写新的、只审、还是改写 | — |

## 两档强度

| 档位 | 何时用 | 生效规则 |
|---|---|---|
| pragmatic（默认） | 用户没点名 STE | 结构规则：R3 虚化动词、R7 句长、R10 双重否定、R17 开放式列举 |
| strict | 点名 ste/STE，或要求合规审计 | 全部 R1–R25，含 R11 三个情态词与 R19 十个状态词 |

## 四条不可退让（pragmatic 只守后两条）

1. 情态词只有 `必须` / `不得` / `可以`，其余近义词一律替换。
2. 状态词只有十个，执行态不得代替验证态——代码写完是「已完成 + 未验证」。
3. 去虚化动词：不写「对……进行」「开展……工作」「做好……准备」。
4. 阻断点给编号选项，推荐项放第 1 项并标 `(推荐)`，每项写动作与代价。

## 三条链的门禁

| 链 | 进下一步之前必须有 |
|---|---|
| 生成 | 文体已定 → 档位已定 → 文本类型已定（程序性 / 描述性）→ 脚本零错误 → 语义项已人工核 |
| 理解 | 先分类 → 脚本结果 + 人工核语义规则 → 每条含规则号、位置、原文、改写建议 |
| 编辑 | 有诊断清单 → 只改命中处 → 复检违规数下降 → 给出前后对照 |

## 不许动清单

代码块、行内代码、命令、路径、URL、环境变量、标识符、frontmatter、产品名、引用原文、数字与单位。改写时绕开它们重组句子，**不要改它们本身**。

不适用：文学创作、营销文案、需要修辞与情绪表达的场合——受控语言会把这些写死。
