---
name: git-commit
description: Create or prepare tightly scoped Git commits with Chinese Conventional Commit messages and staged-diff verification. Use when the user asks to commit, stage and commit, submit changes, prepare a commit message, fix an unpushed nonconforming commit, or says phrases such as "提交改动", "提交全部改动", or "commit these changes" in any Git repository.
---

# Git Commit

Create one reviewable commit whose files, message, and verification all match the user's requested change. Treat repository-specific instructions as authoritative and use this workflow only as the fallback where they are silent.

## Preserve authority and intent

1. Read applicable repository instructions before staging. Check files such as `AGENTS.md`, `CONTRIBUTING.md`, commit guidelines, and commitlint configuration when present.
2. Follow the precedence order: explicit user instruction, repository rule, then this skill.
3. Distinguish message preparation from execution. Do not stage, commit, amend, or push when the user only asks for a suggested message.
4. Never push unless the user explicitly asks. Never amend a pushed or pre-existing commit without explicit authorization.
5. Do not bypass hooks with `--no-verify` unless the user explicitly requests it after seeing the failure.

## Inspect before staging

1. Confirm the repository root and current branch.
2. Run `git status --short` before changing the index.
3. Inspect both existing staged changes and unstaged changes:
   - `git diff --cached --name-only`
   - `git diff --cached --stat`
   - `git diff --stat`
   - Read the relevant diffs and inspect relevant untracked files before including them.
4. Map every candidate file to the user's request. Preserve unrelated user changes and existing staged state.
5. Stop and ask for the intended file set when multiple unrelated themes exist and the request does not resolve the boundary.
6. Stop without committing when there are no in-scope changes.

Do not expose secrets while inspecting files. Exclude credentials, private keys, tokens, local databases, logs, generated artifacts, environment files, and other repository-prohibited content unless the repository explicitly treats a specific file as safe and tracked.

## Build the staged set

1. Stage only explicit in-scope paths. Avoid `git add .` and `git add -A` unless the user explicitly requests all changes and every candidate file has been inspected.
2. Do not unstage or replace unrelated pre-staged changes without user approval.
3. Re-run:
   - `git diff --cached --name-only`
   - `git diff --cached --stat`
   - `git diff --cached`
4. Confirm that every staged line traces to the requested change. Split unrelated themes into separate commits or ask the user to choose the boundary.

## Verify the staged content

1. Run `git diff --check --cached` for every commit.
2. Run the smallest relevant repository checks for the staged behavior, such as targeted tests, lint, type checks, builds, or documentation validation. Reuse valid results from the current task when the checked content has not changed.
3. Do not claim a check passed unless it ran successfully. Report skipped or blocked checks with the reason.
4. Reinspect the staged file list after formatters or hooks change files.

## Write the commit message

Use this structure unless the repository requires a stricter one:

```text
type(scope): 简短中文描述

- 动词开头的主要变更
- 动词开头的主要变更
```

Choose `type` from the actual change:

- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 不改变外部行为的重构
- `perf`: 性能优化
- `docs`: 文档更新
- `test`: 测试变更
- `chore`: 配置或杂项维护
- `ci`: CI/CD 变更
- `build`: 构建系统或依赖变更

Choose `scope` from the repository's real module or domain names. Prefer the dominant affected module for a cohesive cross-file change and use `docs` for pure documentation changes. Do not invent a project-specific scope list.

Follow these message rules:

1. Keep the title in Chinese and limit the description after the colon to about 20 Chinese characters.
2. Use 1-2 body bullets for a simple change and usually 3-6 for a regular change.
3. Start each bullet with a concrete verb such as `新增`, `修复`, `优化`, `重构`, `更新`, `调整`, or `删除`.
4. Describe business behavior, technical effect, tests, documentation, or configuration impact. Do not invent value that the diff does not demonstrate.
5. Do not mechanically list files unless the files themselves are the deliverable.
6. Do not pad the body to reach three bullets or merge distinct important changes merely to keep it short.
7. Reconsider the commit boundary when the body needs more than 8-10 bullets or covers unrelated themes.
8. Reject vague messages such as `Update code`, `Fix bug`, `misc changes`, `wip`, or `test`.
9. Pass all bullets as one contiguous multiline body argument so Git does not insert blank lines between bullets.

Example:

```text
fix(auth): 修复登录状态失效

- 修复过期凭据未及时清理的问题
- 补充登录状态刷新测试
- 更新认证异常处理说明
```

## Commit and verify

1. Create the commit only after the staged scope, checks, `type`, `scope`, title, and bullets agree.
2. If a commit hook fails, fix the underlying in-scope issue or report the blocker. Recheck the index before retrying.
3. After success, verify:
   - `git log -1 --pretty=format:%H%n%B`
   - `git diff-tree --no-commit-id --name-only -r HEAD`
   - `git status --short`
4. Confirm the final hash, committed files, exact message shape, and any intentional leftover changes.
5. If the commit created during the current task is malformed and has not been pushed, amend it before handoff. Do not use amend to absorb unrelated changes.

Report the outcome concisely: commit hash and title, committed scope, checks run, leftovers, and whether a push was intentionally not performed.

## Completion checklist

- Repository rules and user scope were honored.
- Only inspected, in-scope files were staged.
- `git diff --check --cached` passed before commit.
- Relevant checks passed or verification gaps were stated.
- The title matches `type(scope): 简短中文描述`.
- The body is non-empty, verb-led, factual, and contiguous.
- The committed file set matches the intended staged set.
- Remaining worktree changes are preserved and explained.
- No push or history rewrite occurred without authorization.
