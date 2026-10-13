# 反面模式清单

写之前先看这个。前六条来自 developer-docs-framework 的反模式集，后四条来自知识管理实践、专门针对零散条目。

## 通用文档反模式

| 反模式 | 症状 | 修正 |
|---|---|---|
| Kitchen Sink Page | 一篇里混教程、参考、解释、排错 | 一篇只答一个目的 |
| The Abstract Description | 四段描述一个概念却不给一个例子 | 每个概念配代码、响应、图或日志 |
| Dead End | 没有前置条件、没有下一步、没有相关链接 | 底部给相关条目链接，每条写明理由 |
| Thesaurus Trap | 一段叫 workspace，一段叫 project | 一个概念一个名字，进术语表 |
| Admonition Avalanche | 每隔两段一个警告框 | 每篇最多 1-2 个 |
| The UI Narrator | 「要部署，点部署按钮」 | 不写显而易见的操作 |

## 零散条目特有反模式

| 反模式 | 症状 | 修正 |
|---|---|---|
| 来源导向标题 | 「Redis 集群某次故障复盘」「某文章读书笔记」 | 标题必须是概念本身。笔记类型分概念导向和来源导向，只有概念导向能进知识网络 |
| 等完美才入库 | 一篇改十遍还不保存 | 半成品也入库，用 `status` 区分成熟度 |
| 一开始建主题树 | 先花两天设计目录结构 | 只写条目和链接，让结构自己浮现 |
| 无理由链接 | 文末堆一串相关链接 | 每条链接写明「为什么这篇相关」。不写理由的链接只是养成浅薄的习惯，也给不了 AI 检索时唯一的关系信号 |

## 自检脚本能自动抓到的部分

`scripts/validate_knowledge_entry.py` 会检测：来源导向标题（error）、缺例子（warning）、Dead End（error）、缺核实状态与成熟度字段（error）、「问题」章节泄漏概念名（warning）。其余条目（Thesaurus Trap、Admonition Avalanche、Kitchen Sink）需要人工对照本清单过一遍。
