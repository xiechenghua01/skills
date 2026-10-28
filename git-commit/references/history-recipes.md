# 历史改写配方

> 编辑链 Step 3 用。**全部非交互**：交互式命令（`rebase -i`、`add -p`）在无终端环境里会卡死。
> 每条执行后立刻 `git log --oneline -n 8` 确认形态，再走下一步。

---

## 0 通用前提

```bash
git status --short                      # 必须为空
git branch backup/$(date +%Y%m%d-%H%M%S) # 建安全网，记下名字
```

工作区不干净先 `git stash`。所有配方只对**未推送**的提交使用。

---

## 1 补内容（漏了文件）

```bash
git add <文件>
git commit --amend --no-edit
```

message 不动。如果补进来的文件改变了行为范围，回头重写 message。

---

## 2 改信息（只动 message）

```bash
git commit --amend -F -
```

把完整的新 message 从标准输入传进去，标题和正文一起重写，避免半新半旧。

---

## 3 拆分 HEAD

思路：软重置到父提交，变更退回暂存区，再按主题分批提交。

```bash
git reset --soft HEAD^
git restore --staged .          # 全部退回未暂存
git add <第一批>
git commit -F -                 # 第一条信息
git add <第二批>
git commit -F -                 # 第二条信息
```

- 中间态没有提交，做错只能回滚：`git reset --hard backup/<ts>`。
- 拆完必须跑编辑链 Step 4 的等价校验。
- 拆**非 HEAD** 的提交风险高一档：先跟用户确认范围，必要时用本文件第 6 节的 cherry-pick 方式重建。

---

## 4 合并最近 N 个

```bash
git reset --soft HEAD~N
git commit -F -
```

- N 必须精确：`git log --oneline -n <N+1>` 先数清楚。
- 合并后的 message **要重写**，不能把原 N 条标题拼起来。

---

## 5 定点合并（含 fixup）

```bash
git commit --fixup=<目标提交>
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <目标提交>^
```

`GIT_SEQUENCE_EDITOR=true` 让 rebase 接受自动排好的 todo，不打开编辑器。冲突时 `git rebase --abort` 回原状。

---

## 6 重排（不连续提交）

交互式 rebase 不可用时，用 cherry-pick 重建最可控：

```bash
git checkout -b tmp <基准提交>
git cherry-pick <按目标顺序列出 hash>
git checkout <原分支>
git reset --hard tmp
git branch -D tmp
```

冲突时 `git cherry-pick --abort`，不会留下半成品。

---

## 7 回滚

```bash
git reset --hard backup/<ts>    # 回到改写前
git branch -D backup/<ts>       # 用户确认后再删
```

找不到备份分支时用 `git reflog` 翻出改写前的 hash，但 reflog 会过期，不能当唯一依赖。

---

## 8 常见坑

| 坑 | 后果 | 避免方式 |
|---|---|---|
| 工作区不干净就 `reset` | 未提交改动被吞 | 先 `stash` 或先提交 |
| 用 `-i` 系列命令 | 卡在编辑器 | 一律 `GIT_SEQUENCE_EDITOR=true`，或走 cherry-pick |
| 合并后 message 是拼接 | 信息重复、无法读 | 合并必重写 message |
| 忘了等价校验 | 内容悄悄丢失或多出 | `git diff backup/<ts>..HEAD` 必须为空 |
| 对已推送提交 rebase | 需要 force push，改写他人历史 | 先查 `git branch -r --contains` |
| 拆分时凭记忆重写 | 内容与原提交不一致 | 从原提交内容出发，用 reset 而不是手打 |
