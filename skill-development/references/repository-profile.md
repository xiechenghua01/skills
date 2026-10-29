# 仓库与宿主

仅在目标位于当前 `chengze-skills` 仓库或用户明确采用同一分发格式时读取。
通用 Agent Skill、其他项目和其他宿主先读目标自己的规范，不复制本文件字段。

## 1. 当前仓库文件

每个技能使用独立 kebab-case 目录，至少有 SKILL.md；作为独立插件分发时还需：

```text
<skill-name>/
├── .zcode-plugin/plugin.json
├── SKILL.md
└── agents/openai.yaml        # 按需
marketplace.json              # 根市场登记
README.md                     # 模型/用户调用分区
```

参考、脚本、测试和资产按真实职责添加，不为齐全造空目录。一个插件一个技能是当前仓库选择，不是所有宿主通则。

## 2. 头部与版本

当前根 AGENTS.md 要求 SKILL.md 六字段固定顺序：
`name`、`display_name_zh`、`display_name_en`、`description`、`description_en`、`version`。
两个 description 单行双引号，内部不用未转义 ASCII 双引号；英文按用户真实表达重写。
内容版本为 `vYYYYMMDD`，内容改动更新为当天。

插件 `.zcode-plugin/plugin.json` 与根 marketplace 同名条目的 `x.y.z` 必须一致。
已有技能任意内容变更只增加 z 位；新技能从当前项目约定的初始版本开始。市场更新实际读取 marketplace 版本。
显示名和图标的宿主行为以根 README 与脚本为准，不自行猜字段会生效。

## 3. 新建登记

新建技能时：
1. 建目录和 SKILL.md，按需加入 agents/openai.yaml、reference、script、test。
2. 建 `.zcode-plugin/plugin.json`，name 与目录/skill 一致，skills 为 `.`。
3. 根 marketplace 添加相对 source、相同包版本、displayName 与 i18n；图标没有合格 HTTPS 资源时不伪造 URL。
4. 根 README 按用户调用/模型调用登记一句话，描述实际三链与边界。
5. 执行仓库检查：

```bash
python3 scripts/check-skill-headers.py <skill-name> --strict
python3 scripts/check-display-names.py
```

本技能的通用校验器额外检查常见本地链接与有限头部；不取代以上项目检查。

## 4. 编辑登记

修改现有技能内容，同次更新 SKILL.md 内容日期、plugin 与 marketplace 的 z 版本。
同步 README 只在能力、触发或调用策略改变时；不要为代码内部修复改写无关介绍。
新建还没有前一包版本可“自增”，初始版本按仓库当前规则设置；后续修改才递增。

agents/openai.yaml 控制 Codex 展示与默认提示词；`policy.allow_implicit_invocation` 是否需要取决于调用策略。
不要把插件市场显示名误认为 SKILL.md 自动触发信号。

## 5. 授权和完成

写仓库文件不包含 git commit、push、安装、刷新市场或外部托管图标的授权。
修改后先报告本地验证。没有实际安装和目标宿主调用时，只能说源文件及注册完成，不能说自动触发已验证。
