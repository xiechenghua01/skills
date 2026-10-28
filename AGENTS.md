# 本项目规范

## Skill 版本号自增（硬性要求）

skill 内容一旦更新（`SKILL.md`、`references/`、`scripts/`、`tests/`、`agents/openai.yaml`、图标等任何改动），必须在同一次改动中把该 skill 的 `.zcode-plugin/plugin.json` 的 `version` 的 z 位自增 +1，例如 `0.1.0` → `0.1.1`。

- **只动 z 位**：`x.y.z` 中 x、y 保持不变，z 每次更新 +1。
- **不能停在 0.1.0**：不要长期复用同一版本号；不升版会导致后续更新无法被识别，出问题。
- **根目录 `marketplace.json` 每个插件的 `version` 必须同步**为同一个值：ZCode 的更新检测只认 marketplace 条目的 `version`（或 `source` 里的 sha/commit），条目不写版本且 `source` 是相对路径字符串时，永远判定为「无更新」，插件页不会出现更新按钮。升版时两处一起改。`agents/openai.yaml` 不含版本字段。
- 改动与升版应尽量放在同一次提交中，便于按版本回溯技能内容的变化。

## SKILL.md 头部与内容版本（硬性要求）

`SKILL.md` 的 frontmatter 固定六个字段，顺序如下：

```yaml
name: <kebab-case，与目录同名>
display_name_zh: <中文短名>
display_name_en: <英文短名>
description: <中文触发描述，一行写完>
description_en: <英文触发描述，一行写完>
version: v<YYYYMMDD>
```

- **`version` 用 `v` + 内容定稿日期**（如 `v20261028`），内容一改就改成当天；它表达「这一版内容是哪天的」，供人判断时效。
- **包版本仍用 `x.y.z`**，写在 `.zcode-plugin/plugin.json` 与根目录 `marketplace.json`，按上一节规则 z 位自增；它表达「有没有更新」，供宿主比对。
- 两个版本号**同时维护**，不要合并成一个。
- 两个 `description` 都必须**单行、用双引号包裹**。原因：不加引号时，值里出现半角冒号加空格（`: `）会解析失败，出现空格加井号（` #`）会被静默当成注释截断；而外层双引号能兜住这两类。
- 双引号包裹后，**内部不得再出现 ASCII 双引号**（英文引用词改用 `“ ”` 或 `' '`）——`"word "x" word"` 会让 YAML 提前结束字符串，整份头部解析失败。
- 不要用块标量 `|`：朴素解析器会把 `|` 当成字面值，整段描述丢失。
- `description_en` 重写而非直译，覆盖英文用户的实际说法。

提交前跑 `python3 scripts/check-skill-headers.py` 校验头部与两处包版本；加 `--strict` 可把未迁移的历史 skill 的 WARN 也当失败。
