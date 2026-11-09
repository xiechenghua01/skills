# 本项目规范

## Skill 版本在提交时递增（硬性要求）

以下规则**仅适用于当前仓库的提交**。日常编辑、测试、改稿和生成图标时不递增包版本；准备执行 commit 时才处理。即使技能中的说明要求编辑时升版，在本仓库也以本节为准。

1. **逐个检查技能**：先确定本次提交范围，再比较 `HEAD` 与拟提交内容（暂存区），核对各技能是否包含实际改动。技能目录、所属图标、插件及市场的非版本配置变更均归到对应技能；未纳入本次提交的工作区改动不作为依据。
2. **有改动才递增**：已有技能以 `HEAD` 中已提交的 `x.y.z` 为基准，只增加最后一位 z，例如 `0.1.3` → `0.1.4`，x、y 保持不变。未改动的技能不升版；只改根文档或项目规则不连带升级所有技能。
3. **一次提交只递增一次**：多轮编辑、多次暂存、检查重试或提交失败重试，都使用同一已提交基准计算目标版本，不在工作区当前版本上反复 +1。仅版本或日期字段变化不算新的实际技能改动。
4. **新技能使用初始版本**：没有已提交版本基准的新技能，首次提交使用初始包版本 `0.1.0`；提交前的反复修改不累计升版。
5. **两处同步且同次提交**：该技能的 `.zcode-plugin/plugin.json` 与根 `marketplace.json` 同名条目的版本必须一致，关联版本字段随实际改动一起提交。撤出某技能全部实际改动时，也撤出对应升版；精确暂存，不能夹带其他技能的未提交改动。
6. **不自动提交**：只有用户明确要求执行 commit 时才准备版本和暂存。只修改文件、只写提交信息或修改这份项目规则时，不升版、不动 index、不执行 commit。只改已有提交的信息也不升版；补内容 amend 使用原提交父提交为基准，避免同一提交重复递增。

`marketplace.json` 是 ZCode 更新检测的依据（或使用 source 中的 sha/commit）；延后到提交时升版不取消两处版本同步要求。

提交前复核：有实际改动的技能恰好升版一次，未改动技能版本不变，版本与提交范围一致。下方头部校验脚本只检查格式和一致性，不能代替逐技能的改动与递增幅度核对。

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

- **`version` 用 `v` + 内容定稿日期**（如 `v20261028`），在提交包含实际技能改动时更新为提交日期；日常未提交编辑保留原值，新技能可先填创建日期。
- **包版本用 `x.y.z`**，写在 `.zcode-plugin/plugin.json` 与根 `marketplace.json`，按上一节在提交时对有实际改动的技能只增加 z 位，供宿主识别更新。
- 两种版本同时维护，不合并成一个；不因每轮编辑重复升版。
- 两个 description 都必须单行、用双引号包裹。原因：不加引号时，值里出现半角冒号加空格（`: `）会解析失败，出现空格加井号（` #`）会被静默当成注释截断。
- 双引号包裹后，内部不得再出现未转义的 ASCII 双引号；英文引用词改用 `“ ”` 或 `' '`，避免 YAML 提前结束字符串。
- 不要用块标量 `|`：朴素解析器会把 `|` 当成字面值，整段描述丢失。
- description_en 重写而非直译，覆盖英文用户的实际说法。

提交前跑 `python3 scripts/check-skill-headers.py --strict` 校验头部与两处包版本；再按本节核对每个技能是否需要升版。未获提交授权时不得执行 commit。

## DSH 技能市场索引（硬性要求）

根目录 `index.json` 是 DeepSeek Harness（DSH）技能市场索引（Skill Market Index Format 1），让同一批技能既能在 ZCode 插件市场安装，也能在 DSH 的「技能 → 市场」中安装。它由脚本生成，不是手写文件。

1. **只由脚本生成**：运行 `python3 scripts/build-skill-market-index.py` 生成或更新；不要手改 `index.json`。需要校验时运行 `--check`，它会回查索引里每个文件 URL 指向的 commit 与 sha256。
2. **索引输入必须已提交**：生成前，`marketplace.json` 与各技能目录不能有未提交改动（脚本会拒绝）。根文档（`README.md`、`AGENTS.md`）与 `scripts/` 的未提交改动不影响索引，可以先生成索引再一起提交。
3. **不参与包版本递增**：`index.json` 是生成产物。重新生成索引本身不是技能改动，不因此递增任何技能的 `x.y.z`；只有技能内容实际变化才按上一节升版。
4. **技能与索引分两次提交**：索引要固定自己的 commit sha，无法与技能改动放进同一个 commit。先提交技能改动并推送，再生成索引、单独提交。
   ```bash
   # 1. 技能改动（按上一节升版）并推送
   python3 scripts/check-skill-headers.py --strict
   git add -A && git commit -m "feat(...): ..." && git push

   # 2. 索引固定到刚提交的 commit，单独提交
   python3 scripts/build-skill-market-index.py
   python3 scripts/build-skill-market-index.py --check
   git add index.json && git commit -m "chore(index): rebuild skill market index" && git push
   ```
5. **已发布内容冻结**：索引里的文件 URL 固定到 40 位 commit。已推送的 commit 不要再 amend / rebase / force-push，否则已安装用户校验失败；内容有变就必须升版本并重新生成索引（脚本会拒绝同版本内容变化）。
6. **隐藏目录不进索引**：`.zcode-plugin/`、`node_modules`、以 `.` 开头的文件不会进入索引，也不影响 ZCode 安装。技能里的附属文件（`references/`、`scripts/`、`tests/`、`agents/`）会一起进索引，所以技能必须自包含：相对链接不要指向技能目录之外。
