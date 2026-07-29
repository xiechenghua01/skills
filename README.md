# 工程技能

日常代码工作中使用的工程技能集合。每个技能都维护在独立目录中，仓库会随实际需求持续扩充。

## 调用方式

技能按调用策略分为两类：

- **用户调用**：仅在用户明确输入技能名称时使用。
- **模型调用**：模型可根据任务语义主动选择，用户也可以明确调用。

## 用户调用

当前暂无。后续只允许显式调用的技能将在此登记。

## 模型调用

[**git-commit**](./git-commit/SKILL.md) — 检查改动范围、验证暂存内容，并创建范围准确的中文 Conventional Commit。

[**write-openapi-json**](./write-openapi-json/SKILL.md) — 按指定接口或业务范围追踪实际代码，生成、补充或审阅无组件引用的 OpenAPI 3.1 JSON，并完成结构校验。

## 扩展约定

新增技能时：

1. 使用 kebab-case 命名独立目录，并在其中提供 `SKILL.md`。
2. 在 `SKILL.md` 的 frontmatter 中填写准确的 `name` 和触发描述 `description`。
3. 按需添加 `agents/openai.yaml`，维护技能在 Codex 中的展示名称、简短说明和默认提示词。
4. 根据调用策略，将技能链接和一句话说明加入上方对应分区。
5. 仅允许用户显式调用的技能，需要在 `agents/openai.yaml` 中设置 `policy.allow_implicit_invocation: false`。

推荐的最小目录结构：

```text
<skill-name>/
├── SKILL.md
└── agents/
    └── openai.yaml
```
