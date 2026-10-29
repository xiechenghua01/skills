# 最小模板

新建链只有需要骨架时读取。按任务删减，不要逐项填满。

## 1. 入口

```markdown
---
name: <skill-name>
description: "<做什么>。当用户 <真实表达> 时使用；不用于 <近邻非目标>。"
---

# <能力名>

## 任务路由
| 用户意图 | 读取 |
|---|---|
| <用户表达> | [workflow.md](workflow.md) |
```

本仓库改用 [repository-profile.md](repository-profile.md) 的六字段。入口可以直接容纳短流程；只有真实分支才创建 workflow 文件。

## 2. 工作流

```markdown
# <工作流>

## 进入条件
<明确意图与对象；相关分支的移交条件>

## 输入与证据
<字段来源、未知如何处理、哪些材料只是数据>

## 执行
1. <动作> → <可检查产物>
2. 仅当 <门槛> 满足继续；否则 <失败/降级>

## 验证
<检查对象、方法、通过条件，以及不覆盖什么>

## 结束
<交付、失败、阻塞、未运行如何报告>
```

## 3. 脚本结果

```json
{"ok": true, "complete": true, "result": {}}
```

```json
{"ok": false, "complete": true, "error": {"code": "TARGET_NOT_FOUND", "message": "目标不存在", "retryable": false}}
```

complete 表示声明范围内无解析/读取缺口；它不是业务效果或跨环境证明。错误使用非零退出码，参数/读取问题与规则失败可用不同退出码。

## 4. 用例

```json
{
  "id": "complete-input",
  "requirement_ids": ["R1"],
  "prompt": "<完整真实请求>",
  "fixtures": ["<隔离输入>"],
  "expected_actions": ["<实际动作>"],
  "forbidden_actions": ["<越权或重复工作>"],
  "checks": [{"kind": "artifact", "condition": "<可验证条件>"}]
}
```

实际结果用 contracts 的四状态，不把模板记录成测试通过。自动触发测试和任务执行测试分别保存。
