---
name: multi-agent-development
display_name_zh: 多智能体协作开发
display_name_en: Multi-Agent Development
description: "多智能体协作开发：用户说按确认方案开始，或直接要求开发、修复、迭代 DSH 插件时使用。主控统筹，快模型实现，独立审查与按风险深审，主控实机验收；区分本轮结束、外部子任务终止与交付完成。不用于仅讨论方案、能力分析、普通非插件编码或明确暂缓实施。"
description_en: "Use when the user asks to build, fix, or iterate on a DSH plugin, including go ahead after an agreed plan. Coordinate fast implementers, independent review, risk-based deep review, and main-agent UI acceptance without confusing a paused turn with finished background work. Exclude planning-only discussion, capability questions, non-plugin coding, and explicitly deferred implementation."
version: v20261112
---

# 多智能体协作开发

面向 DeepSeek Harness（DSH）插件的开发、修复与迭代。本技能只组织交付：确认入口与范围、拆分角色、选择执行器、推进异步任务、整合、验收与如实报告。DSH 插件 API 与加载/安装实现由 cordis-plugin-development 负责，浏览器验收由 ego-browser 负责；本技能不复述它们的教程。

## 进入条件

满足任一条件即进入实施；已授权且范围清楚时直接做，不再让用户重复分工：
- 方案已确认，用户明确要求实施。
- 用户直接给出清晰的 DSH 插件开发、修复或迭代请求。

不进入写入流程：
- 只讨论方案、比较做法、评估可行性或分析能力。
- 普通非插件编码，或对象不是 DSH 插件。
- 赞同但明确暂不实施。
- 方案未确认且关键对象或授权不明：只问会改变动作的缺口，不暂停无关的读取与准备。

## 必载技能与边界

| 遇到 | 先加载 | 本技能怎么做 |
|---|---|---|
| DSH 插件 API、插件加载或安装实现 | cordis-plugin-development | 按其规则实现；本技能只安排谁做、何时验收 |
| 浏览器实机验收 | ego-browser | 遵循其指南操作；不伪造页面或结果 |

不自动部署或发布。用户明确授权的目标插件安装由主控按上述技能与宿主权限执行；负责写代码的子任务不改用户 profile、配置或全局安装。

## 主流程

1. 定范围：明确目标插件、改动路径、非目标与验收方式；已给出的信息不再追问。
2. 拆分：小改动可以单 agent 完成；通常最多 2 个写任务并行；范围或接口有依赖时先定接口再派，紧耦合串行。
3. 派发：先给目标、输入、写入范围、依赖、验收与模型/执行器，工具返回后再登记实际 ID；不写长篇交接文档，也不另建平行状态 JSON。
4. 等待：遵守[异步运行与后台可见性](references/async-runs.md)；只剩等待时按宿主规则结束本轮，不让主控空转。
5. 整合：先读回各子任务的实际改动与终止结果，再按依赖顺序合并；冲突回到接口或拆分解决。
6. 验收：按[验收、审查与交付说明](references/acceptance.md)执行适用的必需构建、类型、测试、独立审查与 DSH 实机验收；单独说明可选未验项和不适用项。
7. 汇报：说明做了什么、验证了什么、未验或阻塞什么、还有哪些后台任务在运行；证据不足不宣称完成。

拆分和选择执行器前读[角色与模型路由](references/model-routing.md)；发生模型不可用、接管或降级时按该文件处理。

## 不可退让

- 主控保留当前实际模型，技能不改变主会话模型；角色固定、模型可换，不强制四模型全开。模型建议是配置建议，不是实测排名。
- 宿主模型动态发现，不认为 magpie 或某个 group 别名永远存在；用户明确的模型偏好优先于默认建议。
- 外部子任务尚未结束时，主控暂停本轮前必须发出阶段状态：任务名、实际 ID、仍在后台运行、尚未完成交付。这是静态告知，不冒充实时徽标，也不编造百分比、用量或工具进度。
- 必需子任务或适用的必需检查仍未通过时，不写全部完成；如实区分 running、pending、failed、unknown、blocked 与 not_run。零运行数不等于成功；非必需或不适用的检查按验收协议单独说明。
- 父 agent 停止不证明外部子任务已取消；没有停止接口时，不谎称已停止，也不让替补同时写同一路径。
- 审查只读不等同权限隔离；模型意见不照单全收，改后必须复验受影响范围。
- 没有浏览器或接口时标 blocked 或 not_run，不把静态代码阅读称为实机验收。

完成汇报后停止无关操作，不自动提交、推送、部署或发布。