# 本项目规范

## Skill 版本号自增（硬性要求）

skill 内容一旦更新（`SKILL.md`、`references/`、`scripts/`、`tests/`、`agents/openai.yaml`、图标等任何改动），必须在同一次改动中把该 skill 的 `.zcode-plugin/plugin.json` 的 `version` 的 z 位自增 +1，例如 `0.1.0` → `0.1.1`。

- **只动 z 位**：`x.y.z` 中 x、y 保持不变，z 每次更新 +1。
- **不能停在 0.1.0**：不要长期复用同一版本号；不升版会导致后续更新无法被识别，出问题。
- **根目录 `marketplace.json` 不声明版本**，无需改动；`agents/openai.yaml` 也不含版本字段。
- 改动与升版应尽量放在同一次提交中，便于按版本回溯技能内容的变化。
