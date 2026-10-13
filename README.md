# 工程技能

日常代码工作中使用的工程技能集合。每个技能都维护在独立目录中，仓库会随实际需求持续扩充。

## 在 ZCode 中安装

本仓库也是名为 `chengze-skills` 的插件市场，每个技能对应一个可独立安装、启用或停用的插件。

1. 打开 ZCode **设置 → 插件管理 → 发现**，点击 **添加市场（+）**。
2. 选择本仓库根目录。本机路径为 `/Users/xiechenghua/Codes/xch/skills`；在其他机器上使用实际克隆路径，不要选择某个技能子目录。
3. 添加成功后，在该市场中分别安装需要的 `git-commit`、`write-openapi-json` 或 `write-knowledge-doc` 插件。仅添加市场不会自动安装技能。
4. 安装并启用后，在技能设置或 `/` 菜单中确认技能可用。

根目录的 `marketplace.json` 登记市场及插件来源，各技能目录中的 `.zcode-plugin/plugin.json` 声明插件信息。插件清单中的 `"skills": "."` 相对于插件根目录解析，直接加载已有的 `SKILL.md`，无需移动技能或附属资源。

## 调用方式

技能按调用策略分为两类：

- **用户调用**：仅在用户明确输入技能名称时使用。
- **模型调用**：模型可根据任务语义主动选择，用户也可以明确调用。

## 用户调用

当前暂无。后续只允许显式调用的技能将在此登记。

## 模型调用

[**git-commit**](./git-commit/SKILL.md) — 检查改动范围、验证暂存内容，并创建范围准确的中文 Conventional Commit。

[**write-openapi-json**](./write-openapi-json/SKILL.md) — 按指定接口或业务范围追踪实际代码，生成、补充或审阅无组件引用的 OpenAPI 3.1 JSON，并完成结构校验。

[**write-knowledge-doc**](./write-knowledge-doc/SKILL.md) — 把指定的一类技术知识整理为条目式知识文档：界定单篇边界，按「问题→解法→例子」骨架成文，frontmatter 标注成熟度与核实状态，交付前完成读者测试与条目自检。

## 扩展约定

新增技能时：

1. 使用 kebab-case 命名独立目录，并在其中提供 `SKILL.md`。
2. 在 `SKILL.md` 的 frontmatter 中填写准确的 `name` 和触发描述 `description`。
3. 按需添加 `agents/openai.yaml`，维护技能在 Codex 中的展示名称、简短说明和默认提示词。
4. 根据调用策略，将技能链接和一句话说明加入上方对应分区。
5. 仅允许用户显式调用的技能，需要在 `agents/openai.yaml` 中设置 `policy.allow_implicit_invocation: false`。
6. 在技能目录下添加 `.zcode-plugin/plugin.json`，填写与目录一致的插件名称、版本、描述及 `"skills": "."`。
7. 在根目录 `marketplace.json` 的 `plugins` 中登记同名插件，`source` 使用相对仓库根目录的路径，例如 `./<skill-name>`。
8. 在同一条目中填写 `displayName` 和 `displayName_i18n`，让插件在中文界面显示中文名，见下方「插件显示名」。
9. 需要展示图标时，把图标放入根目录 `assets/`，并在 `marketplace.json` 该插件的 `icon` 字段填入其 HTTPS 地址。

推荐的最小目录结构：

```text
marketplace.json
assets/
└── <skill-name>.png
<skill-name>/
├── .zcode-plugin/
│   └── plugin.json
├── SKILL.md
└── agents/
    └── openai.yaml
```

## 插件显示名

技能在 ZCode 中展示的名称来自插件的市场条目字段 `displayName` / `displayName_i18n`，而不是 `SKILL.md` 的 `name`。解读顺序：先按语言前缀匹配 `displayName_i18n`（`zh-CN` 会命中 `zh` 开头的键），再回退到 `displayName`，都没有时才把插件名自动标题化（`write-openapi-json` → `Write Openapi Json`）。官方插件正是用这两个字段显示「技能创建器」「飞书 CLI」「电脑控制」等中文名。

- **名称本身保持 ASCII**：插件名、目录名、`SKILL.md` 的 `name` 都必须是 kebab-case ASCII，客户端按 `^[a-z0-9][a-z0-9._-]{0,127}$` 校验。中文名只写在市场条目里，`name` 仍是 `/` 菜单和 `$<skill-name>` 的调用标识。
- **没有技能级显示名**：`SKILL.md` 的 frontmatter 只识别 `name`、`description`、`when_to_use`、`license`、`metadata`，技能行仍显示 ASCII 技能名；中文名作用在插件分组标题上。本仓库一个插件一个技能，分组标题即技能名称。
- **不要写进 `plugin.json`**：安装时客户端只从市场条目读取该字段，`.zcode-plugin/plugin.json` 里的 `displayName` 会被剔除，写了不生效。
- **改动需推送**：与图标相同，市场更新读取 GitHub 上的 `marketplace.json`，修改后需先 `push`，再在 **设置 → 插件管理 → 发现** 中更新市场才能看到新名称。

修改后运行 `python3 scripts/check-display-names.py` 校验：脚本先用官方市场的已知事实校准解析逻辑，再逐项检查本仓库的显示名、名称合法性、`source` 路径和 `SKILL.md` 的 `name` 一致性。

## 插件图标

图标显示在插件市场的卡片、插件详情页，以及技能设置页的分组标题和技能行上。约束如下：

- **只认 HTTPS 绝对地址**：客户端仅在 `icon` 以 `https://` 开头时才加载图片，本地相对路径、`data:` 地址一律回退为通用图标。因此图标必须托管到 HTTPS。
- **本仓库用 jsDelivr**：`assets/<skill-name>.png` 通过 jsDelivr 指向本仓库，形如
  `https://cdn.jsdelivr.net/gh/xiechenghua01/skills@main/assets/<skill-name>.png`。
- **推荐 PNG**：同时保留同名 `.svg` 作为源文件便于修改；用 256×256（或更大）PNG 作为线上图，与官方市场图标规格一致。
- **PNG 由 SVG 渲染，不单独画**：`svg` 是唯一真源，改完 SVG 后执行 `swift scripts/render-icon.swift assets/<skill-name>.svg assets/<skill-name>.png` 重新生成 256×256 PNG。两边各画各的必然形状漂移。
- **不要用 `qlmanage` 渲染 SVG**：它在 48 尺寸下把内容渲染到画布左上角，且在白底上合成会让圆角外变成不透明白色、圆角边缘混出一条白色弧线。仓库自带的 `scripts/render-icon.swift` 支持本仓库用到的 `rect`（含 `rx` 圆角）、`circle` 与 `path`（`M/L/H/V/C/A/Z`，绝对与相对命令均可用，支持 `fill` 与 `stroke`）图元，按文档顺序绘制。
- **改动需推送**：jsDelivr 与市场更新都读取 GitHub 上的内容，修改后需先 `push`，再在 **设置 → 插件管理 → 发现** 中更新市场才能看到新图标。

> 注意：技能设置页的分组由**插件**决定，一个插件一个分组。同组展示多个技能（如 GitHub 插件的 10 个技能）需要把它们放进同一个插件；独立的插件会各占一个分组，即使图标相同。
