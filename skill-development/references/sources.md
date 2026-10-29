# 来源与适用边界

只有用户要求经验依据、企业样本比较或解释设计来源时读取。日常新建、编辑、理解不需要加载本文件。

本技能合并两类输入：
1. 仓库原经验文档 `docs/skill-development-playbook.md`：路由、分层、渐进披露、规则写法、需求门禁、交叉引用和版本维护。
2. 2026-10-29 静态调研：腾讯 CloudBase、阿里云百炼/CADT、字节 DeerFlow 公开技能，以及 Anthropic skill-creator 的评估实现。

可迁移机制：
- CloudBase：按场景读参考、信息足够后停止、操作后回读；代码审查分确定性规则与语义判断。
- 阿里云：清晰任务当轮交付、不重复同一确认；schema 校验、doctor、预览/live 隔离、真实模块测试和本次资源 ledger。
- DeerFlow：稳定数据处理进入脚本；名称冲突、参数绑定、缓存和导出约束在实现中处理。
- Anthropic：有/无技能或旧/新版对照，自动触发和任务质量分开；同时暴露基础设施错误误算、不完整指标、选优集冒充最终集的风险。

不能直接照搬：无条件重复确认、规则清单与实现脱节、上下文不足就跳过产物复核、脚本存在即宣称离线或测试通过、缺指标填零、将格式打包当宿主兼容。
企业归属不等于质量保证；本次仅静态阅读，未安装或运行云技能。

关键修正：六字段/双版本是本仓库规范，不是通用标准；入口短是渐进披露策略，不是固定 40 行；质量规则不必全部数字化；完成即止不代表对象变化后禁止必要验证；布局诊断不能证明视觉质量。

原文入口（只作依据，不默认安装或执行）：
- [腾讯 CloudBase 官方来源](https://docs.cloudbase.net/ai/cloudbase-ai-toolkit/prompts/how-to-use)，仓库 TencentCloudBase/skills，调研提交 `930c3e4f75d3f3ae5ffd49fbd7ec216f344b6b66`。
- [阿里云官方来源](https://help.aliyun.com/zh/skillsportal/quickly-use-alibaba-cloud-skills)，仓库 aliyun/alibabacloud-aiops-skills，读取 ref=master；百炼 SKILL blob `e66de7aa4e456c665977b5002d6a4623114b037a`，CADT SKILL blob `84d5b3bc941b4caaa17fd416190a9384e41950c3`。blob 只固定文件，不等于目录提交。
- [字节 DeerFlow](https://github.com/bytedance/deer-flow)，调研提交 `b537d9c16c84e432ee609da57f042d4926c94f8c`。
- [Anthropic skill-creator](https://github.com/anthropics/skills)，评估源码提交 `ca45fc496a3436251f191354091d557da31c15b5`，不计国内企业样本。

完整原始调研保存在任务工作区的 `skill-development-experience/`，不复制进运行 skill，避免常规任务加载大量历史材料。若该外部目录不存在，本技能工作流仍应自包含。
