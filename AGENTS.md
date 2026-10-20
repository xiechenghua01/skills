# 本项目规范

## Skill 版本号自增（硬性要求）

skill 内容一旦更新（`SKILL.md`、`references/`、`scripts/`、`tests/`、`agents/openai.yaml`、图标等任何改动），必须在同一次改动中把该 skill 的 `.zcode-plugin/plugin.json` 的 `version` 的 z 位自增 +1，例如 `0.1.0` → `0.1.1`。

- **只动 z 位**：`x.y.z` 中 x、y 保持不变，z 每次更新 +1。
- **不能停在 0.1.0**：不要长期复用同一版本号；不升版会导致后续更新无法被识别，出问题。
- **根目录 `marketplace.json` 每个插件的 `version` 必须同步**为同一个值：ZCode 的更新检测只认 marketplace 条目的 `version`（或 `source` 里的 sha/commit），条目不写版本且 `source` 是相对路径字符串时，永远判定为「无更新」，插件页不会出现更新按钮。升版时两处一起改。`agents/openai.yaml` 不含版本字段。
- 改动与升版应尽量放在同一次提交中，便于按版本回溯技能内容的变化。
