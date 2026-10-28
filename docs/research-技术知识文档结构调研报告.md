# 技术知识文档结构调研报告

## 一、调研结论先行

网络上**没有**一个现成 skill 能完整满足你的需求（整理技术知识、Mermaid 流程图为主、文字为辅、同时服务人与 AI）。但有 4 个 skill 高度相关，可组合使用；另外有一批被广泛采用的文档结构范式与认知心理学依据，可以支撑自建一份文档规范。

**四个最相关的 skill：**

| Skill | 星标 | 核心贡献 | 对你的适配度 |
|---|---|---|---|
| [dbreunig/scaffold-docs-skill](https://github.com/dbreunig/scaffold-docs-skill) | 95 | 自底向上迭代式文档法（结构→标题→段落），主文件只做心智模型 | 高。它的「读者心智模型优先」和渐进披露正是你要的 |
| [anivar/developer-docs-framework](https://github.com/anivar/developer-docs-framework) | 17 | Diataxis 四象限 + 27 条规则 + 6 种风格 + 反模式清单 | 最高。四象限直接回答「一篇知识文档该有哪些部分」 |
| [luoling8192/technical-writing](https://github.com/luoling8192/technical-writing) | 216 | 中文技术写作的语气、句法、黑话清单 | 高。你要写中文文档 |
| [Fenng/Tech-Doc-Style-Chinese](https://github.com/Fenng/Tech-Doc-Style-Chinese) | 1489 | 中文技术文档规范体系（事实保真、术语一致、受控中文） | 高。星标最高、体系最完整的国产规范 |

**关键判断：** 你的场景（「我不懂一类知识，AI 整理成内容，我要存进知识库」）在工业界的最接近范式是 **Claude Code 的 doc-coauthoring skill 流程 + Diataxis 的内容分类**。前者管「怎么把脑子里的东西变成文档」，后者管「文档该长什么样」。

---

## 二、网络 skill 调研详情

### 2.1 四个 skill 的实测内容

**scaffold-docs-skill**（自底向上迭代法）最有价值的发现是它的三遍写作法：

- Pass A：标题 + 学习要点 + 代码块
- Pass B：小标题 + 段落主题句（≤20 词，单主谓宾）
- Pass C：完整段落

它要求**每一遍之间都停下来给用户审阅**。对你的场景来说，这意味着让 AI 先生成骨架给你确认，再逐节填充，而不是一次性吐出全文。

**developer-docs-framework** 的骨架是 Diataxis。它明确指出一个常见错误：不要一上来建四个空目录（Tutorials/How-to/Reference/Explanation），那是「Empty Scaffold」反模式——Diataxis 改变的是文档内部结构，不是先去建空壳。

**technical-writing** 提供中文技术写作的语气规则，核心是「先接住读者，再往下解释」，并给出了大量 bad case 改写（例如把「这样的组合很顺」改成「这种组合能把日志写入链路和告警判定链路拆开」）。

**Tech-Doc-Style-Chinese** 提供了五条规则优先级，第一条就是「保留事实、逻辑、限制、安全信息」——这对 AI 整理的内容尤其重要，因为 AI 最容易在改写时丢掉限定条件。

### 2.2 官方 doc-coauthoring 的三段式流程

[Anthropic 官方的 doc-coauthoring skill](https://github.com/anthropics/skills)（共 375 行）给出一套结构化协作流程，第三段对你直接有用：

**Context Gathering（收集上下文）** → **Refinement & Structure（逐节迭代）** → **Reader Testing（读者测试）**

第三段 Reader Testing 的做法是：用一个新的、没有上下文的 Claude 实例，只喂文档内容和读者会问的问题，看它能否正确回答。**这正好同时验证了「给人看」和「给 AI 看」两种效果**——如果一个无上下文的 AI 能读懂你的文档，说明文档的自包含性合格。


---

## 三、零散知识点：先确定单篇的边界

这一章针对你的实际场景——一篇只讲一个知识点，多篇陆续积累，彼此之间没有内在顺序。你的文档不是产品文档，不需要「概念/参考双轨」那种成体系结构，需要的是**条目式知识库**的组织方式。

### 3.1 篇边界怎么划：原子性原则

两个独立的来源给出了同一条结论。

**卡片盒笔记法（Zettelkasten）**把原子性列为核心信条：「one of the core tenets」，知识由离散块构成，每张卡片只放一个想法。它的理由是认知层面的——「Your thinking operates in units of thought」。

**Andy Matuschak 的常青笔记**表述得更完整：「notes which are only about one thing—but which, as much as possible, capture the entirety of that thing」。关键在后半句：**只讲一件事，但要把这件事讲完整**。

划太宽和划太碎都有代价，这点 Matuschak 说得很直白：

- 拆太宽：新想法撞上来时你注意不到它属于这个复合体里的哪一块，且指向这篇笔记的链接含义被污染（"links to that note will be muddled"）
- 拆太碎：链接网络被切断

他还明确说「there's no clear litmus test or correct answer here—just a bunch of tradeoffs」。

**对你的落地判据**：读者只读这一篇，能否独立理解这个概念？能，边界就是对的。这就是自包含性，也是第六、七章讲的两个读者共同的要求。

### 3.2 成熟度要分层：不是写完才能入库

这是零散积累场景和成体系文档最大的差别。**成体系文档隐含假设「发布即完成」，而零散知识必须是「先入库、再成熟」。**

Maggie Appleton 的数字花园（Digital Garden）给出三阶段模型，源头是 Mike Caulfield 的《The Garden and the Stream》：

| 阶段 | 原文定义 | 你的对应状态 |
|---|---|---|
| Seedling 🌱 | "for very rough and early ideas" | 只有原始问题和 AI 转述，未消化 |
| Budding 🌿 | "work I've cleaned up and clarified" | 已用自己的话重写，可以链接 |
| Evergreen 🌳 | "work that is reasonably complete (though I still tend these over time)" | 概念自洽，人和 AI 都能直接检索复用 |

两个直接可用的推论：

- **半成品也入库**。Appleton 的说法是 "Gardens are imperfect by design"；Matuschak 更激进——"very freeing to be able to link to a stub"（可以链向一个只有标题的空壳）。你不需要等一篇「完美了」才保存。
- **用 frontmatter 的 `status` 字段承载成熟度**。CNCF glossary 就是这么做的，它的取值是封闭的三种：`Completed` / `Feedback Appreciated` / `Not Started`。封闭取值的好处是 AI 能据此判断该用哪篇回答、以及哪些结论还不够可靠。

### 3.3 条目式文档的真实骨架

调研里找到了四个真实的「一文件一条目」范例，它们高度一致。

**Wikipedia 条目**是最成熟的范例，它的硬性规则：

| 规则 | 具体要求 |
|---|---|
| 导语位置 | 在第一个标题**之前**，导语本身没有标题 |
| 导语长度 | 无固定段落数；好导语通常超过约 100 词，特色条目多为 250-400 词 |
| 第一句 | 必须是简明定义，且**标题应作第一句的主语**（"Mercury is the first planet from the Sun"，不是 "Mercury (planet) is…"） |
| 首段职责 | 识别主题 + 确立上下文 + 说明为何值得关注 |
| 同步性 | 导语里的重要信息，正文必须有覆盖 |

Wikipedia 还有两个机制值得学：

- **Stub（小条目）**：短条目用模板标记，不设硬性长度线，但有个可执行的经验阈值——超过 500 词就该摘掉 stub 标记、补上章节标题。这给了你一个明确信号：**写到 500 词就该考虑是不是该拆篇或补结构了**。
- **消歧义**：同名概念在页面顶部用斜体缩进的 hatnote 指向另一篇。你整理知识时一定会遇到「同一个词在不同上下文里是两回事」。

**CNCF glossary** 对「我不懂一个概念」这个场景最贴合。它的官方模板把「这个概念为什么存在」变成强制字段：

```markdown
---
title: Definition Template
status: Feedback Appreciated
category: concept
---

A quick summary of the technology or concept.

## Problem it addresses
Define the problem it addresses. Ideally, don't even mention the term you are defining.

## How it helps
Describe how the term addresses the problem described above.

## Related terms
Add related Glossary terms (if applicable)
```

注意 `Problem it addresses` 的写法要求：**先定义问题，且尽量不要提到你要定义的那个术语**。这是防止「用自己解释自己」的硬手段，对你整理陌生知识特别有用——你得先搞懂它解决什么痛点，才谈得上懂它。

它的写作规范也很严：禁用 jargon 和 buzzword、不用缩略形式、少被动、不用感叹号、不夸大、不重复，并且要求「minimum viable definition」——能帮助理解的技术细节才保留，其余明确划到 out of scope。

**tldr pages**（6.4 万星，4722 篇命令速查表）给出了最刚性的单篇结构：

```markdown
# tar

> Archiving utility.
> Often combined with a compression method, such as `gzip` or `bzip2`.
> More information: <https://www.gnu.org/software/tar/manual/tar.html>.

- [c]reate an archive and write it to a [f]ile:
`tar cf {{path/to/target.tar}} {{…}}`
```

四件套：一级标题即条目名、1-3 行摘要（第一行是不超过 10 词的一句话定义）、More information 外链、示例列表。它的规范里有几条硬约束可以直接搬：**每篇约 5 个示例、最多不超过 8 个**；选项要渐进引入，从最简单的调用开始；只写这个命令特有的细节，不讲通用 UNIX 概念。

**Julia Evans 的博客/TIL** 是「一篇讲清一个小概念」的写作典范。她的标题模式是「小问题或小现象 + 限定范围」，而且明确点名目标读者（例如 `Using make to compile C programs (for non-C-programmers)`）。单篇结构有一个很实用的装置：**长文主动给目录**（"This post is kind of long so here's a quick table of contents"），结尾回扣开头的学习成本叙事，并自曝理解限度（"my understanding is honestly still in the subconscious pattern recognition stage"）。

最后这一条对你有特殊价值：**她不假装全知，而是把自己懂到哪一步讲清楚**。这正好是 AI 整理文档应该保留的品质——第 1.5 节会讲怎么落到实处。

### 3.4 命名一经确定就不要改

Zettelkasten 对固定地址的重视程度极高："The fixed address of each note is the alpha and omega of the world of Zettelkasten."

它的具体方案值得直接采用：数字时代用**时间戳作为 ID**，因为时间戳 "never changes"，所以你可以随时改笔记标题而不会断链。

对你的落地建议：如果知识库以文档名为主键，**slug 确定后就不要再改**；要改标题就改文档内部的 H1，不动文件名。如果确实需要迁移，做重定向而不是直接改名。


---

## 四、体系不是设计出来的，是长出来的

这一章回答你最实际的担心：我这些知识点不成体系，怎么办。

### 4.1 三条材料给出同一条路径

**Zettelkasten 的立场最激进：不要分类。** Luhmann 的原始指令是 "It is not important where you place a new note as long as you can link to it"，系统优先级是「连接优先于收集」（"connecting and not collecting a priority"）。它明确说让关联网络 "gradually emerge, unlabeled"。

**Matuschak 的理由更具体：** 过早建层级分类会 "prematurely constrain what may emerge"。

**LYT（Linking Your Thinking）的触发条件是经验性的：** "You'll know when to make a new MOC because you start to feel a building sense of being overwhelmed."——结构是被「积累到痛」逼出来的，不是规划出来的。

三条合起来就是：**先写条目、只做链接、等链接密集到读不动了再收拢**。

### 4.2 链接要说明理由，这是知识管理里最容易漏的一条

Zettelkasten 有两条链接规则：每篇新笔记必须连到已有的笔记，并且**必须显式说明为什么做这条链接**。原文说得很重：不解释原因的链接 "just create a habit of shallowness"，"you will not create knowledge"。

这条对你有双重价值：

- 对你自己：写链接理由的过程会强迫你判断「这两篇到底什么关系」，这是把收藏变成理解的唯一环节
- 对 AI：链接是 Agent 检索时**唯一能拿到的关系信号**。Matuschak 明确指出 "Tags are an ineffective association structure"——标签承担不了关联职责

### 4.3 MOC：比目录更适合零散知识

MOC（Map of Content，内容地图）和传统目录的区别，LYT 自己的表述最清楚：

| 维度 | 传统目录/文件夹 | MOC |
|---|---|---|
| 对笔记的作用 | "Folders act to limit a note's availability. They bury notes." | "MOCs are magicians: they don't limit access; they curate it" |
| 本质 | 静态分类 | 一个「主要内容是指向其他笔记的链接」的笔记 |
| 认知功能 | 仅导航 | 同时给鸟瞰视角，允许 "rapidly shuffle and edit each interrelated idea" |
| 维护成本 | 移动文件 | "You could never open your home note and MOCs for a whole year and they will be fine." |

对你的落地建议：

- **顶层只放一个入口页**，不要一开始建主题树。条目按需增长，同一篇可以被多个未来的 MOC 引用——LYT 的说法是 "items belong in many places"
- **MOC 就是一篇普通笔记**，不占独立命名空间，不需要单独的文件命名规则
- **新增知识点时不要问「该进哪个 MOC」**，只写笔记、做链接。等某个概念域的链接密集到难以通读，才为它建 MOC

### 4.4 Tiago Forte 的 PARA 补充：知识点的可执行性很低

PARA 把信息按「可执行性」降序分四类：Projects（项目）→ Areas（领域）→ Resources（资源）→ Archives（归档）。

对你的判断：**你陆续整理的技术知识点，绝大多数天然落在 Resources**（"topics you're interested in and learning about"）。这解释了一个你可能会困惑的现象——为什么它们「看起来不成体系却仍然值得存」：**体系不是知识点的存放要求，而是后续通过链接和 MOC 聚合产生的结果。** 你不必在保存每一篇时就为它找好体系位置。

## 五、排版认知科学：什么样的排版更容易被接受

这一节的结论有眼动实验和认知心理学实证支撑。

### 5.1 读者根本不逐字读

Nielsen Norman Group 的经典测试数据：**79% 的用户总是扫描新页面，只有 16% 逐字阅读**。同一份实验里，把内容改成「加粗关键词 + 简洁 + 列表」的组合后，可读性提升 124%。

232 人眼动实验（F 型模式）给出的两条可操作规则：

- 前两段必须放最重要的信息——「exhaustive reading is rare」
- **行首的信息词被读到的概率远高于第三个词**。所以标题、列表项要以名词或动词开头，不要用从句定语开头

### 5.2 认知负荷理论（Sweller）

核心命题：工作记忆是单一有限资源，「把它花在理解你的版式上，就减少了用来理解技术内容的预算」。

由此推出三个对技术文档直接有效的技术：

1. **消除分离注意（split attention）**：图和解释它的文字必须紧邻，不能一个在第 3 页一个在第 20 页。这是技术文档最常见的无形成本。
2. **工作样例效应（worked example effect）**：给完整可运行的例子，比让读者自己从规则推导更省认知资源。
3. **切块（chunking）**：一段一个论点；长说明拆成编号步骤。

### 5.3 图文分工判定表

| 内容特征 | 该用什么 | 判定标准 |
|---|---|---|
| 空间结构、连接关系（调用链、数据流向、依赖） | **图** | 若用文字描述需要 3 个以上「→」或「包含」才讲清 |
| 时间顺序、交互过程（请求响应、状态流转） | **图**（时序/状态图） | 涉及 2 个以上参与方，或有明确先后 |
| 抽象概念的解释与意图（为什么这样设计） | **文字** | 「为什么」「权衡」类问题 |
| 精确值（参数名、错误码、默认值、版本号） | **文字（表格优先）** | 需要可复制、可搜索、可 diff |
| 操作步骤 | **文字（编号列表）** | 读者要照着敲 |

一句口诀：**图回答「长什么样」，文字回答「是什么/为什么」，表格回答「有哪些/是多少」，代码回答「照做就行」。**

### 5.4 Mermaid 图型选择

| 图型 | 适合 | 不适合 |
|---|---|---|
| flowchart | 分支判断、处理流程、决策树 | 有严格时序的多方交互 |
| sequenceDiagram | 调用时序、握手、同步异步差异 | 静态结构、数据模型 |
| stateDiagram | 有限状态机、生命周期、合法迁移 | 非状态型过程 |
| erDiagram | 实体关系、基数、主外键 | 请求时序、权限逻辑 |
| classDiagram | 继承组合聚合、接口契约 | 时序行为、部署拓扑 |
| mindmap | 概念总览、术语索引、知识地图 | 有条件分支的流程 |

**选型速判**：多方且有先后 → sequence；单方且有条件分支 → flowchart；只有状态没有先后 → state；只有实体和基数 → er；只有静态归属 → class；只有分类层级 → mindmap。

拿不准时**选更抽象的那个**：用 flowchart 画时序只损失顺序信息，用时序图画流程会污染「交互」语义，读者要在错误的心智模型上重建认知。

### 5.5 渐进披露：两级封顶

NN/g 的实验结论：**超过两级折叠的设计可用性显著下降**，「users often get lost when moving between the levels」。另外，「三层以内点击」法则被证明没有数据支持，真正重要的是每次点击的「信息气味」——标签是否说清了里面是什么。

### 5.6 其他排版参数

- 正文行宽 50-75 字符（66 是常引用的甜蜜点）；代码块可略宽但设上限 80-100
- 加粗每段最多 2-3 处，只标术语、参数名、可点击值、危险项。加粗通胀后信号失效
- 用留白和接近性分组，不要靠分隔线堆叠（Gestalt 接近性原则）
- 语法高亮主要降低**定位成本**，对深层理解几乎无影响，且对资深读者收益递减——不能靠高亮替代清晰命名


---

## 六、给 AI 看的文档：当前工业实践

### 6.1 核心发现：不是两套写法

工业界并没有「给人看的文档」和「给 AI 看的文档」两套写法。**同一套 Markdown，用「渐进披露 + 结构化 + 自包含」三层机制分层服务两个读者。**

### 6.2 Agent Skills 规范的三层加载

[Agent Skills 规范](https://agentskills.io/specification)定义的渐进披露：

| 层级 | 内容 | 何时加载 |
|---|---|---|
| L1 元数据 | name + description | **启动时全部加载**，决定是否触发 |
| L2 指令正文 | 主文件正文 | 判定相关后才读入，**控制在 500 行内** |
| L3 资源 | references/、scripts/ 子文件 | 按需加载，无上限 |

规范原话：「Keep your main SKILL.md under 500 lines. Move detailed reference material to separate files.」以及「Keep file references one level deep. Avoid deeply nested reference chains.」

**拆子文件的真实判断标准**（来自官方 skill 实例对比）：接近 500 行才拆；按「任务子域」拆而不按篇幅拆；主文件必须自带路由信息，否则 AI 不知道子文件存在。

### 6.3 description 字段的写法（这是最可迁移的一条）

规范要求 description 同时回答「它做什么」和「什么时候用它」，且**必须包含帮助 AI 识别相关任务的关键词**。官方正反对照：

```yaml
# 好
description: Extracts text and tables from PDF files, fills PDF forms, and merges
  multiple PDFs. Use when working with PDF documents or when the user mentions
  PDFs, forms, or document extraction.

# 差
description: Helps with PDFs.
```

四条写法原则：用祈使句；描述用户意图不描述内部实现；宁可过度列举适用场景；保持简洁（因为它对每个会话全量加载）。

### 6.4 可检索性设计（对 RAG 的影响）

Anthropic 的 contextual retrieval 实验给了一个量化结论：孤立的文本切块会「destroy context」——一句「公司收入比上季度增长了 3%」被切出来后，检索系统不知道是哪家公司哪个季度。给每个切块补上文档级上下文化前缀后，**top-20 检索失败率从 5.7% 降到 3.7%**。

落到文档写作上：

- 每个小节要能独立回答一个问题，不依赖上一节的「该方法」「如前所述」
- 标题是人和向量模型共用的最强路由信号，所以用「为什么需要重试」而不是「重试」
- 让标题层级成为切块的自然边界；一个小节能在 300 token 内讲完就让它讲完
- 同一概念全文一个名字——BM25 检索下，「链接器/连接器/connector」三种写法会把词频打散
- 大文档（>300 行）建目录表

### 6.5 llms.txt 索引规范

[llmstxt.org](https://llmstxt.org/) v2 规范定义：文件放 `/llms.txt`，结构固定为「H1 项目名（唯一必需节）+ blockquote 摘要 + 若干 H2 分节的链接列表」，链接项必须是 `[name](url): 说明` 格式。

实测范例是 [Cloudflare 的 llms.txt](https://developers.cloudflare.com/llms.txt)（约 17KB）：H1 是站点名，blockquote 是一句摘要，然后按产品域分 H2 节，节内是 `[产品名](url): 一句话说明`。每个产品还有自己的 llms.txt，形成两级索引。

---

## 七、两个读者的冲突与调和

这是本报告对你最有直接价值的一节。

| 维度 | 人需要 | AI 需要 | 调和方式 |
|---|---|---|---|
| 入口 | 目录、导航 | 判断「跟我手上的任务相关吗」 | 顶部放 2-3 句 scope 声明（做什么+不做什么+什么时候查），替代泛泛引言 |
| 结论位置 | 常放最后（叙事） | 前置（省 token） | 开头给 TL;DR 结论块，正文再展开。人扫一眼，AI 少读 |
| 术语 | 首次出现时解释 | 一致、可精确匹配 | 就地解释一次，之后全文同一字符串 |
| 图表 | 渲染后的图 | 图的结构化语义 | **Mermaid 是文本协议，人和 AI 各取所需** |
| 示例 | 最小、可运行 | 完整、含边界 | 一个最小示例 + 一个边界示例 |
| 篇幅 | 可接受长文 | 500 行/5000 token 上限 | 主文档 ≤500 行，超出拆子文件 |
| 冗余 | 强调是噪声 | 多写一遍是保险 | 定义一次 + 交叉引用；关键约束可文末速查表汇总 |
| 指代 | 「该配置」读得顺 | 指代消解易错 | 每节首次用全名，跨节引用带章节号 |
| 比喻 | 降低门槛 | 歧义源 | 比喻只在「为什么」段出现一次，其后立即给字面定义 |

**三条最重要的调和原则：**

1. **结论前置，论证后置。** 人对结论的耐心有限（前两段必须给答案），AI 读结论能省 token。这是唯一一条两个读者诉求完全一致的做法。
2. **表格是双读者的桥梁。** 表格既是人类最好的扫描格式，也是 AI 最易解析的结构。能用表格就不用图文混排。
3. **关键信息必须留在文本里，不能只放在图里。** 截图承载逻辑信息对 AI 是完全不可读的（也无法 diff、无法评审）。Mermaid 源码本身就是文本，但如果你用了渲染图，必须保留源码。

### 7.1 AI 整理文档的可信度保障

这一条单独列出，因为它只对你有用：**AI 整理的文档必须写清核实状态**——哪些结论查过原始来源，哪些没有。没有这一行，读者（包括未来的你）只能默认全部未经验证。Tech-Doc-Style-Chinese 把「不新增来源没有提供的数字、日期、时限、能力、条件」列为最高优先级规则，正是因为 AI 改写最容易在这里丢限定条件。

---


---

## 八、反面模式清单（写之前先看这个）

来自 developer-docs-framework 的 26 个反模式，挑对**条目式知识文档**最相关的：

| 反模式 | 症状 | 修正 |
|---|---|---|
| Kitchen Sink Page | 一篇里混教程、参考、解释、排错 | 一篇只答一个目的 |
| The Abstract Description | 四段描述一个概念却不给一个例子 | 每个概念配代码、响应、图或截图 |
| Dead End | 没有前置条件、没有下一步、没有相关链接 | 底部给相关条目链接 |
| Thesaurus Trap | 一段叫 workspace，一段叫 project | 一个概念一个名字，进术语表 |
| Admonition Avalanche | 每隔两段一个警告框 | 每篇最多 1-2 个 |
| The UI Narrator | 「要部署，点部署按钮」 | 不写显而易见的操作 |

另有四条来自知识管理实践、专门针对零散条目的反模式：

| 反模式 | 症状 | 修正 |
|---|---|---|
| 来源导向标题 | 「Redis 集群某次故障复盘」「某文章读书笔记」 | 标题必须是概念本身（Matuschak：concept-oriented） |
| 等完美才入库 | 一篇改十遍还不保存 | 半成品也入库，用 `status` 区分成熟度 |
| 一开始建主题树 | 先花两天设计目录结构 | 只写条目和链接，让结构浮现（见第四章） |
| 无理由链接 | 文末堆一串相关链接 | 每条链接写明「为什么这篇相关」 |


---

## 九、针对你场景的单篇结构与库组织

综合全部调研，下面是可直接套用的方案。

### 9.1 单篇结构（一篇一个知识点）

骨架来源：CNCF glossary 的「问题—解法」字段设计 + Wikipedia 的导语硬规则 + tldr 的摘要行。

```markdown
---
title: 概念名（标题必须是概念，不能是来源）
status: seedling      # seedling | budding | evergreen
created: 2026-10-12
updated: 2026-10-12
tags: [术语, 与正文一致]
verified: partial    # all | partial | none —— AI 整理的文档尤其要写
---

（H1 概念名）

一句话定义        ← 首句给定义，标题作主语（Wikipedia 规则）
适用场景          ← 什么时候该查这篇
核实状态          ← 哪些结论查过来源、哪些没有

## 它解决什么问题      ← CNCF 的 Problem it addresses：
                       「先定义问题，尽量不要提到这个术语」
## 它怎么解决的        ← CNCF 的 How it helps
## 一个具体场景        ← 贯穿全篇的真实例子，AI 整理的内容最缺这个
## 边界与例外          ← 具体的不适用场景
## 相关概念            ← 每条链接写明「为什么相关」
```

和第一版建议的差别主要有三处，都来自第三章的调研：

1. **新增「它解决什么问题」一节且放在主位**。这是 CNCF 模板的核心设计——你不懂一个概念时，真正的障碍通常是「不知道它为什么存在」。这一节强迫你先讲清痛点。
2. **新增 `status` 和 `verified` 两个 frontmatter 字段**。前者承载成熟度（允许半成品入库），后者是 AI 整理文档的可信度保证。
3. **去掉「怎么运作/为什么」两章并列的主干**。那是成体系文档的做法。零散知识点的主干就是「问题→解法→例子」，其余按需追加。

### 9.2 知识库组织

```
knowledge-base/
├── 入口页.md          # 一个极简导览：几条可走的路 + 一声明「还有坑没填」
├── 概念条目/           # 平铺，不建主题树
│   ├── <slug>.md      # slug 一经确定不改名
│   └── ...
└── MOC-<概念域>.md     # 等链接密集到读不动了才建；MOC 就是普通笔记
```

四条规则：

1. **顶层只有一个入口页**，条目平铺。不要一开始分「网络类」「数据库类」——那是目录思维，而零散知识的条目经常跨域。
2. **slug 用不可变标识**。Zettelkasten 用时间戳 ID 的理由是它 "never changes"，改标题不断链。如果你更看重可读性，用小写英文 kebab-case 也行，但**确定后不改**。
3. **新建条目时只做两件事**：写完，加链接（含理由）。不问「该归到哪一类」。
4. **MOC 按需诞生**。触发信号是 LYT 说的「开始感到 overwhelmed」——某个域的链接多到通读不动了，为它写一篇 MOC。

### 9.3 AI 整理时的人机分工

你的流程是「AI 整理 → 你存库」，所以这一步值得固定下来：

| 环节 | 谁做 | 说明 |
|---|---|---|
| 选定知识点、判断该不该整理 | 你 | AI 无法判断你对什么有困惑 |
| 收集材料、提取事实 | AI | 但要它标注每条事实的来源 |
| 判定「它解决什么问题」 | 你审 | 这是理解的核心，AI 最容易写成同义反复 |
| 搭骨架、生成初稿 | AI | 按 9.1 的结构 |
| 逐节核对事实 | 你 | 官方 doc-coauthoring 的 Reader Testing 可以直接用 |
| 写链接理由 | 你 | 这条不能外包，它决定链接是知识还是噪声 |
| 更新 `status` 和 `verified` | 你 | 成熟度和可信度是你的判断 |

其中「Reader Testing」值得单独说：[Anthropic 官方的 doc-coauthoring skill](https://github.com/anthropics/skills) 第三阶段的做法是**用一个无上下文的 AI 实例，只喂这篇文档和读者会问的问题，看它能否答对**。这一步同时验证了两个读者——无上下文的 AI 能读懂，说明自包含性合格；你能读懂，说明它对人也可读。


---

## 十、参考资料索引

### Skill 源码（已实际克隆研读）

- https://github.com/dbreunig/scaffold-docs-skill — 迭代式三遍写作法
- https://github.com/anivar/developer-docs-framework — Diataxis + 27 规则 + 26 反模式
- https://github.com/luoling8192/technical-writing — 中文技术写作语气与句法
- https://github.com/Fenng/Tech-Doc-Style-Chinese — 中文技术文档规范体系
- https://github.com/anthropics/skills — 官方 skill（doc-coauthoring / skill-creator / pdf）

### 知识管理与条目组织（本轮新增）

- https://zettelkasten.de/introduction/ — 原子性、固定地址、链接必须说明理由
- https://zettelkasten.de/posts/zettelkasten-improves-thinking-writing/ — 小体量是基本原则
- https://notes.andymatuschak.org/Evergreen_notes — 常青笔记五原则
- https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic — 原子性的双向代价
- https://notes.andymatuschak.org/Evergreen_notes_should_be_concept-oriented — 概念导向 vs 来源导向
- https://notes.andymatuschak.org/Taxonomy_of_note_types — 笔记类型分类
- https://maggieappleton.com/garden-history — 数字花园三阶段（seedling/budding/evergreen）
- https://maggieappleton.com/evergreens — 常青笔记的培育
- https://fortelabs.com/blog/para/ — PARA 四分类，按可执行性组织
- https://blog.linkingyourthinking.com/notes/mocs-(defn) — MOC 定义
- https://blog.linkingyourthinking.com/notes/lyt-faq — MOC 与目录的区别

### 条目式文档范例（本轮新增）

- https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Lead_section — 导语硬规则（首句定义、100-400 词、独立性）
- https://en.wikipedia.org/wiki/Wikipedia:Stub — stub 机制与 500 词转正线
- https://glossary.cncf.io/style-guide/ — CNCF 条目写作规范
- https://github.com/cncf/glossary/blob/main/content/en/_TEMPLATE.md — 「Problem it addresses → How it helps」官方模板
- https://github.com/tldr-pages/tldr/blob/main/CONTRIBUTING.md — tldr 单篇规范（约 5 个示例、最多 8 个、渐进引入）
- https://jvns.ca/ 及 https://jvns.ca/til/ — 「一篇一个小概念」的写作范例
- https://github.com/oldwinter/knowledge-garden — 2461 星双链知识库（Cards/Spaces/Sources/Atlas 目录实测）

### 排版与认知科学

- https://diataxis.fr/ — Diataxis 四象限与质量论
- https://kubernetes.io/docs/contribute/style/diagram-guide/ — 唯一把图文规则写成规范的站点
- https://www.nngroup.com/articles/how-users-read-on-the-web/ — 79% 扫描、124% 可读性提升
- https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content-discovered/ — F 型扫描、行首信息词
- https://www.nngroup.com/articles/progressive-disclosure/ — 渐进披露两级封顶
- https://www.nngroup.com/articles/chunking/ — 切块原则
- https://www.nngroup.com/articles/gestalt-proximity/ — 接近性分组
- https://en.wikipedia.org/wiki/Cognitive_load — Sweller 认知负荷理论

### AI 可读性

- https://agentskills.io/specification — Agent Skills 渐进披露三层规范
- https://agentskills.io/skill-creation/optimizing-descriptions — description 触发优化
- https://llmstxt.org/ — llms.txt v2 规范
- https://developers.cloudflare.com/llms.txt — 两级索引实测范例
- https://www.anthropic.com/news/contextual-retrieval — 切块自包含的量化依据

---

## 附：本版修订说明

第二版相对第一版的改动：

- **重写第三章**：原第三章讲的是「成体系产品文档」的结构模式（K8s/Stripe/MDN 的概念参考双轨），不适用于零散知识点场景。现改为条目式知识库的组织方式：篇边界（原子性）、成熟度分层（数字花园三阶段）、四个真实范例的骨架、命名不变原则。
- **新增第四章**：回答「知识点不成体系怎么办」——三条材料一致指向「先写条目、只做链接、等链接密集再收拢」，并补充 MOC 与目录的区别、PARA 对知识点的定位。
- **重写第九章**：单篇骨架从「是什么/怎么运作/为什么」改为 CNCF 的「问题→解法→例子」；新增 `status`、`verified` 两个 frontmatter 字段；新增知识库组织方式与人机分工表。
- **第八章补充**：新增四条来自知识管理实践的反模式（来源导向标题、等完美才入库、一开始建主题树、无理由链接）。
- 第五、六、七章（排版认知科学、AI 可读性、双读者调和）内容经复核仍然成立，未改动。

*报告完成于 2026-10-12。第三、四章为第二轮调研新增；第五至七章沿用第一版。所有结论均来自实际抓取的材料，实证与推论已在正文区分。*
