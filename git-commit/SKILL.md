---
name: git-commit
display_name_zh: 提交改动
display_name_en: Git Commit
description: "在 Git 仓库里生成或改写提交：生成链判断改动边界、精确暂存、写中文 Conventional Commit 并复核；编辑链负责补漏、改信息、拆分、合并与调整未推送提交的顺序。用户说「提交」「commit 一下」「写个提交信息」「补一下刚才那次提交」「拆成两个提交」「合并成一次」时使用——即使没提 Conventional Commit，只要意图是创建一次提交或改写已有提交，就应触发。"
description_en: "Create or rewrite Git commits: the create chain scopes the change, stages precisely, writes a Chinese Conventional Commit message, and verifies the result; the edit chain fixes omissions, rewrites messages, splits, squashes, and reorders unpushed commits. Use when the user says 提交, commit, write a commit message, amend the last commit, split into two commits, or squash these commits — even without mentioning Conventional Commits, as long as the intent is to create or rewrite a commit."
version: v20261028
---

# 提交改动

一次提交 = 一个可独立回滚的意图。本技能负责把这个意图从工作区改动物化成一条**范围准确、信息准确**的中文 Conventional Commit。

## 任务路由

| 用户要什么 | 走哪条链 | 读 |
|---|---|---|
| 提交改动、commit 一下、把这批改动提上去 | 生成 | [generate.md](generate.md) |
| 只写提交信息、先别提交、提交信息怎么写 | 生成链 Step 1 之后停 | [generate.md](generate.md) |
| 补漏了文件、刚才信息写错、拆成两个、合并成一次、调顺序 | 编辑 | [edit.md](edit.md) |
| 判断不出是哪条 | 先问一句：新建提交，还是改已有提交 | — |

两条链共用一份信息规范：[references/message-spec.md](references/message-spec.md)。编辑链的历史改写配方与回滚方式在 [references/history-recipes.md](references/history-recipes.md)。

## 两条链的门禁

| 链 | 进下一步之前必须有 |
|---|---|
| 生成 | 措辞已判定（执行 / 只出信息）→ 提交边界已定 → 暂存可逐行追溯 → `diff --check` 通过 → 提交后复核完成 |
| 编辑 | 目标提交未推送（或已获明确授权）→ 工作区干净 → 已建备份 → 改写前后内容等价 |

任一门禁不满足就停下说明缺什么，不要边做边补。

## 共用铁律

1. **不推送**。用户没明说就不 push，报告里注明「未推送」。
2. **不改已推送的提交**。被 `git branch -r --contains <hash>` 命中时，说明后果并要授权；共享分支默认拒绝。
3. **不用 `--no-verify` 绕过钩子**。钩子失败先修根因，修不了就如实报错。
4. **不提交不该进仓库的东西**：密钥、token、私钥、日志、本地数据库、构建产物、`.env`。
5. **说「只写信息」就不动 index**。措辞区分见生成链 Step 1。

## 不适用

解决合并冲突、写 PR 描述、生成变更日志、操作远端分支——这些不归本技能。
