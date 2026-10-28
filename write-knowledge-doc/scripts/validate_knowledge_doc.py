#!/usr/bin/env python3
"""校验知识文档是否符合 write-knowledge-doc 的骨架契约。

契约来源：references/skeleton.md（本脚本是它的可执行版本，两者必须同步改）。

模式由 frontmatter 的 kind 字段决定：
- kind: entry  → 五章阿拉伯编号 1-5、H3 的 x.y、追加章节从 6 接续。
- kind: system → H2 中文数字编号连续、H3 的 x.y 与父章对应。
没有 frontmatter 一律判为结构缺失（ERROR），不再隐式推断模式。

级别：
- ERROR 结构或硬规则违反，必须修复才能交付。
- WARN  建议处理项，逐条处理或在交付说明里说明为什么不改。

阶段：
- --stage skeleton 只查结构契约（frontmatter、章节存在与编号、H1），跳过内容检查。
- --stage draft（默认）全查。

用法：
    python3 scripts/validate_knowledge_doc.py <文件> [更多文件...] [选项]
    python3 scripts/validate_knowledge_doc.py 条目.md --stage draft
    python3 scripts/validate_knowledge_doc.py 条目.md --json
    python3 scripts/validate_knowledge_doc.py 条目.md --strict   # WARN 也算失败

退出码：0 通过 / 1 未通过（有 ERROR，或 --strict 下有 WARN）/ 2 参数或文件错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

STATUS_VALUES = ("seedling", "budding", "evergreen")
VERIFIED_VALUES = ("all", "partial", "none")
KIND_VALUES = ("entry", "system")
REQUIRED_FIELDS = ("title", "kind", "applies_to", "status", "verified", "created", "updated", "tags")
# 适用范围里出现这些词等于没写：无法判断某条结论是否命中。
VAGUE_SCOPE_WORDS = ("最新", "常见版本", "一般来说", "通常")

CORE_SECTIONS = (
    "它解决什么问题",
    "它怎么解决的",
    "一个具体场景",
    "边界与例外",
    "相关概念",
)
FIRST_ENTRY_EXEMPTION = "知识库首篇"

# 来源导向标题的典型用词：出现在概念标题里几乎一定是反模式。
SOURCE_ORIENTED_WORDS = (
    "读书笔记", "学习笔记", "读后感", "心得", "复盘", "摘录", "转载", "翻译",
)

CN_NUMERALS = "一二三四五六七八九十"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)")
WIKI_LINK_RE = re.compile(r"\[\[[^\]]+\]\]")
H1_RE = re.compile(r"^#\s+(\S.*)$")
H2_RE = re.compile(r"^##\s+(.*)$")
H3_RE = re.compile(r"^###\s+(.*)$")
CN_NUM_RE = re.compile(r"^([一二三四五六七八九十]+)、")
ARABIC_NUM_RE = re.compile(r"^(\d+)\.\s*")
SUB_NUM_RE = re.compile(r"^(\d+)\.(\d+)\s*")
FENCE_RE = re.compile(r"^\s*```")


class Finding:
    """一条校验结果。fix 是可执行的修正建议，不是复述问题。"""

    __slots__ = ("level", "code", "line", "message", "fix")

    def __init__(self, level: str, code: str, message: str, line: int = 0, fix: str = "") -> None:
        self.level = level
        self.code = code
        self.line = line
        self.message = message
        self.fix = fix

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
        }


class Report:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def error(self, code: str, message: str, line: int = 0, fix: str = "") -> None:
        self.findings.append(Finding("ERROR", code, message, line, fix))

    def warn(self, code: str, message: str, line: int = 0, fix: str = "") -> None:
        self.findings.append(Finding("WARN", code, message, line, fix))

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.level == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.level == "WARN")


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #

def parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """返回 (字段表, 正文起始下标)。没有合法围栏时字段表为空、起始下标为 0。

    只支持单行 key: value 与 [a, b] 内联列表；行内注释按 ' #' 剥离。
    """
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, str] = {}
    for i, raw in enumerate(lines[1:], start=1):
        if raw.strip() == "---":
            return fields, i + 1
        line = raw.split(" #", 1)[0] if " #" in raw else raw
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return {}, 0


def code_block_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """围栏代码块的 [起始下标, 结束下标] 列表，用于跳过结构识别。"""
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            if start is None:
                start = i
            else:
                ranges.append((start, i))
                start = None
    if start is not None:
        ranges.append((start, len(lines) - 1))
    return ranges


def in_ranges(idx: int, ranges: list[tuple[int, int]]) -> bool:
    return any(a <= idx <= b for a, b in ranges)


def headings(lines: list[str], ranges: list[tuple[int, int]]) -> tuple[list[dict], list[dict]]:
    """返回 (H1 列表, H2 列表)，跳过代码块。每项含 line（1-based 行号）、title、idx。"""
    h1s: list[dict] = []
    h2s: list[dict] = []
    for i, line in enumerate(lines):
        if in_ranges(i, ranges):
            continue
        if m := H1_RE.match(line):
            h1s.append({"line": i + 1, "idx": i, "title": m.group(1).strip()})
        elif m := H2_RE.match(line):
            h2s.append({"line": i + 1, "idx": i, "title": m.group(1).strip()})
    return h1s, h2s


def section_body(lines: list[str], start_idx: int, end_idx: int) -> list[str]:
    return lines[start_idx + 1:end_idx]


# --------------------------------------------------------------------------- #
# 通用检查
# --------------------------------------------------------------------------- #

def check_frontmatter(rep: Report, lines: list[str], fields: dict[str, str], body_start: int) -> str:
    """检查七字段，返回判定出的 kind（无法判定时返回空串）。"""
    if not fields:
        rep.error(
            "FM-MISSING", "缺少 frontmatter（文件首行应为 --- 且包含七字段）", 1,
            "在文件首行加 frontmatter：title / kind / status / verified / created / updated / tags",
        )
        return ""

    field_line = {name: i for i, raw in enumerate(lines[1:body_start], start=2)
                  if ":" in raw and (name := raw.split(":", 1)[0].strip()) in REQUIRED_FIELDS}

    for name in REQUIRED_FIELDS:
        if not fields.get(name):
            rep.error(
                "FM-FIELD", f"frontmatter 缺少必填字段 {name}", field_line.get(name, 1),
                f"补一行 `{name}: <值>`，取值规则见 references/skeleton.md §一",
            )

    kind = fields.get("kind", "")
    if kind and kind not in KIND_VALUES:
        rep.error(
            "FM-KIND", f"kind 取值非法：{kind!r}，应为 entry 或 system", field_line.get("kind", 1),
            "条目式写 `kind: entry`，成体系文档写 `kind: system`",
        )
        kind = ""

    scope = fields.get("applies_to", "")
    if scope:
        hits = [w for w in VAGUE_SCOPE_WORDS if w in scope]
        if hits:
            rep.warn(
                "FM-APPLIES-VAGUE", f"applies_to 含无法比对的范围词（{'/'.join(hits)}）：{scope!r}",
                field_line.get("applies_to", 1),
                "改成版本号 / 产品名 / 平台这类可比对的值；确认不了就写 unknown 并在第 4 章说明",
            )

    if (status := fields.get("status")) and status not in STATUS_VALUES:
        rep.error(
            "FM-ENUM", f"status 取值非法：{status!r}，应为 {' / '.join(STATUS_VALUES)}",
            field_line.get("status", 1),
            "seedling（粗糙）/ budding（可链接）/ evergreen（可复用）三选一",
        )

    if (verified := fields.get("verified")) and verified not in VERIFIED_VALUES:
        rep.error(
            "FM-ENUM", f"verified 取值非法：{verified!r}，应为 {' / '.join(VERIFIED_VALUES)}",
            field_line.get("verified", 1),
            "all（每条查过）/ partial（部分查过）/ none（未查）三选一",
        )

    dates: dict[str, str] = {}
    for name in ("created", "updated"):
        value = fields.get(name, "")
        if not value:
            continue
        if not DATE_RE.match(value):
            rep.error(
                "FM-DATE", f"{name} 应为 YYYY-MM-DD，实际 {value!r}", field_line.get(name, 1),
                "改成 2026-10-28 这样的格式",
            )
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            rep.error("FM-DATE", f"{name} 日期不存在：{value!r}", field_line.get(name, 1),
                      "检查月份与日期是否越界")
            continue
        dates[name] = value

    if len(dates) == 2 and dates["updated"] < dates["created"]:
        rep.error(
            "FM-DATE-ORDER", f"updated（{dates['updated']}）早于 created（{dates['created']}）",
            field_line.get("updated", 1),
            "把 updated 改成不早于 created 的日期",
        )

    return kind


def check_h1(rep: Report, h1s: list[dict], title: str) -> None:
    if len(h1s) != 1:
        rep.error(
            "H1-COUNT", f"H1 应有且仅有一个，实际 {len(h1s)} 个",
            h1s[1]["line"] if len(h1s) > 1 else 1,
            "只保留文档开头的一个 `# 标题`",
        )
        return
    if title and h1s[0]["title"] != title:
        rep.error(
            "H1-MISMATCH", f"H1 {h1s[0]['title']!r} 与 frontmatter title {title!r} 不一致",
            h1s[0]["line"],
            "把 H1 改成与 title 完全一致；要改标题就两处一起改",
        )


def check_source_oriented(rep: Report, title: str) -> None:
    hits = [w for w in SOURCE_ORIENTED_WORDS if w in title]
    if hits:
        rep.error(
            "TITLE-SOURCE", f"标题疑似来源导向（含 {'/'.join(hits)}）", 1,
            "标题必须是被定义的概念本身，来源信息放进 frontmatter 或正文来源表",
        )


def check_typography(rep: Report, lines: list[str], ranges: list[tuple[int, int]]) -> None:
    for i, line in enumerate(lines):
        if in_ranges(i, ranges) or line.strip().startswith(("|", "#")):
            continue
        bold = line.count("**") // 2
        if bold > 3:
            rep.warn("TYPO-BOLD", f"一行内加粗 {bold} 处（每段最多 2-3 处）", i + 1,
                     "只保留术语、参数名、危险项的加粗，其余去掉")
        if len(line) > 100:
            rep.warn("TYPO-WIDTH", f"正文行宽 {len(line)} 字符超过 100", i + 1,
                     "在语义边界处折行，推荐控制在 50-75 字符")


# --------------------------------------------------------------------------- #
# entry 模式
# --------------------------------------------------------------------------- #

def check_entry(rep: Report, lines: list[str], fields: dict[str, str], body_start: int,
                h1s: list[dict], h2s: list[dict], ranges: list[tuple[int, int]],
                stage: str) -> None:
    title = fields.get("title", "")
    check_h1(rep, h1s, title)
    check_source_oriented(rep, title)

    # ---- 五章：存在性 / 编号 / 顺序 / 重复 ----
    found: list[tuple[int, str, dict]] = []  # (期望编号, 标题, heading)
    for expected, name in enumerate(CORE_SECTIONS, start=1):
        matches = [h for h in h2s if name in h["title"]]
        if not matches:
            rep.error(
                "SEC-MISSING", f"缺少核心章节「{name}」", 0,
                f"补上 `## {expected}. {name}`，位置按 1-5 顺序",
            )
            continue
        if len(matches) > 1:
            rep.error(
                "SEC-DUP", f"核心章节「{name}」出现了 {len(matches)} 次", matches[1]["line"],
                "五章各出现一次，重复的内容合并或移到追加章节",
            )
        head = matches[0]
        found.append((expected, name, head))
        m = ARABIC_NUM_RE.match(head["title"])
        if not m:
            rep.error(
                "SEC-NUM", f"核心章节「{name}」缺少阿拉伯数字编号", head["line"],
                f"改成 `## {expected}. {name}`",
            )
        elif int(m.group(1)) != expected:
            rep.error(
                "SEC-NUM", f"核心章节编号错误：「{head['title']}」应为 {expected}. {name}",
                head["line"], f"改成 `## {expected}. {name}`",
            )

    prev_line = -1
    for expected, name, head in found:
        if head["line"] < prev_line:
            rep.error(
                "SEC-ORDER", f"核心章节顺序错乱：「{head['title']}」位置在上一章之前", head["line"],
                "按 1→5 的顺序重排章节",
            )
        prev_line = max(prev_line, head["line"])

    # ---- 其他 H2：必须编号且从 6 接续 ----
    core_lines = {head["line"] for _, _, head in found}
    extras = [h for h in h2s if h["line"] not in core_lines]
    expected_extra = 6
    for h in extras:
        m = ARABIC_NUM_RE.match(h["title"])
        if not m:
            rep.error(
                "SEC-EXTRA", f"H2「{h['title']}」既不是核心章节也没有编号", h["line"],
                "五章之外的内容一律放进追加章节并从 6. 起编号（常见疑问 / 延伸 / 术语表）",
            )
            continue
        num = int(m.group(1))
        if num < 6:
            rep.error(
                "SEC-EXTRA", f"H2「{h['title']}」编号 {num} 与核心章节冲突", h["line"],
                "核心章节占用 1-5，追加章节从 6 起",
            )
            continue
        if num != expected_extra:
            rep.error(
                "SEC-GAP", f"追加章节编号不连续：「{h['title']}」应为 {expected_extra}.", h["line"],
                f"改成 `## {expected_extra}. <章节名>`，编号不得跳号",
            )
        expected_extra = max(expected_extra, num) + 1

    # ---- H3：x.y 且 x 等于父章编号 ----
    current_h2 = 0
    for i, line in enumerate(lines):
        if i < body_start or in_ranges(i, ranges):
            continue
        if m2 := H2_RE.match(line):
            num = ARABIC_NUM_RE.match(m2.group(1).strip())
            current_h2 = int(num.group(1)) if num else 0
            continue
        if m3 := H3_RE.match(line):
            sub = SUB_NUM_RE.match(m3.group(1).strip())
            if not sub:
                rep.error(
                    "H3-NUM", f"H3「{m3.group(1).strip()}」缺少 x.y 编号", i + 1,
                    f"改成 `### {current_h2 or 1}.1 <子标题>`；不需要编号就把 H3 降级为粗体行",
                )
            elif current_h2 and int(sub.group(1)) != current_h2:
                rep.error(
                    "H3-PARENT", f"H3 编号 {sub.group(1)}.{sub.group(2)} 与父章编号 {current_h2} 不对应",
                    i + 1, f"改成 `### {current_h2}.{sub.group(2)} <子标题>`",
                )

    # ---- 章节正文 ----
    sections: list[tuple[dict, list[str]]] = []
    for idx, h in enumerate(h2s):
        end = h2s[idx + 1]["idx"] if idx + 1 < len(h2s) else len(lines)
        sections.append((h, section_body(lines, h["idx"], end)))

    # ---- 导语 ----
    first_h2_idx = h2s[0]["idx"] if h2s else len(lines)
    lead_lines = [l for i, l in enumerate(lines[body_start:first_h2_idx], start=body_start)
                  if not H1_RE.match(l)]
    lead = "\n".join(lead_lines).strip()
    if not lead:
        rep.error(
            "LEAD-MISSING", "缺少导语（H1 与第一个 H2 之间需要有正文）", body_start + 1,
            "补一句话定义 + 适用场景 / 成熟度 / 核实状态三行",
        )
    elif stage != "skeleton":
        first = lead.splitlines()[0]
        if title and not first.startswith(title):
            rep.warn(
                "LEAD-OPENING", f"导语首句不以概念名开头：{first[:30]}…", body_start + 1,
                f"改成「{title}是……」的句式，标题作主语",
            )
        if "成熟度（status:" not in lead:
            rep.warn(
                "LEAD-STATUS", "导语缺少「成熟度（status: 值）」行", body_start + 1,
                "补一行；知识库不渲染 frontmatter 注释，读者只能从正文看到字段值",
            )
        if "适用范围（applies_to:" not in lead:
            rep.warn(
                "LEAD-APPLIES", "导语缺少「适用范围（applies_to: 值）」行", body_start + 1,
                "补一行，写清结论对哪个版本或环境成立；不随版本变化写 universal",
            )
        if "核实状态（verified:" not in lead:
            rep.warn(
                "LEAD-VERIFIED", "导语缺少「核实状态（verified: 值）」行", body_start + 1,
                "补一行，写清哪些结论查过来源",
            )

    if stage == "skeleton":
        return

    # ---- 内容信号 ----
    def body_of(keyword: str) -> tuple[dict, list[str]] | None:
        for h, body in sections:
            if keyword in h["title"]:
                return h, body
        return None

    if rel := body_of("相关概念"):
        head, body = rel
        text = "\n".join(body)
        links = MD_LINK_RE.findall(text) + WIKI_LINK_RE.findall(text)
        has_item = bool(re.search(r"^\s*[-*\d]", text, re.MULTILINE))
        if not links and not has_item:
            if FIRST_ENTRY_EXEMPTION in text:
                pass  # 首篇豁免：允许「暂无。本条目为知识库首篇……」
            else:
                rep.error(
                    "REL-DEADEND", "「相关概念」既没有链接也没有列表项（Dead End）", head["line"],
                    "补相关条目并写明为什么相关；知识库首篇写「暂无。本条目为知识库首篇，出现相关条目后回填。」",
                )
        link_rows = [l for l in body if MD_LINK_RE.search(l) or WIKI_LINK_RE.search(l)]
        if len(link_rows) >= 2:
            bare = sum(
                1 for l in link_rows
                if len(WIKI_LINK_RE.sub("", MD_LINK_RE.sub("", l)).strip(" -\t")) < 8
            )
            if bare > len(link_rows) / 2:
                rep.warn(
                    "REL-BARE", "「相关概念」过半链接行没有说明理由", head["line"],
                    "每条补一句关系判断：上下位 / 并列易混 / 因果 / 替代方案",
                )

    if scene := body_of("一个具体场景"):
        head, body = scene
        text = "\n".join(body)
        has_example = (
            bool(code_block_ranges(body))
            or bool(INLINE_CODE_RE.search(text))
            or "http" in text
            or bool(re.search(r"^\s*\|", text, re.MULTILINE))
        )
        if not has_example:
            rep.warn(
                "SCENE-NOEXAMPLE", "「一个具体场景」没有代码块、行内代码、URL 或表格", head["line"],
                "补一次真实的输入 / 过程 / 输出，不要停留在「比如某个系统会……」",
            )

    if problem := body_of("它解决什么问题"):
        head, body = problem
        text = "\n".join(l for l in body if not l.lstrip().startswith("#"))
        if title and len(title) >= 2 and title in text:
            rep.warn(
                "PROB-LEAK", f"「它解决什么问题」出现了概念名 {title!r}", head["line"],
                "这一节先定义问题；把该处替换成对处境的描述，写完遮住概念名通读一遍",
            )

    for head, body in sections:
        if not "\n".join(body).strip():
            rep.warn("SEC-EMPTY", f"章节「{head['title']}」没有内容", head["line"],
                     "填上内容；非核心章节也可以直接删掉")

    check_typography(rep, lines, ranges)


# --------------------------------------------------------------------------- #
# system 模式
# --------------------------------------------------------------------------- #

def check_system(rep: Report, lines: list[str], fields: dict[str, str], body_start: int,
                 h1s: list[dict], h2s: list[dict], ranges: list[tuple[int, int]],
                 stage: str) -> None:
    check_h1(rep, h1s, fields.get("title", ""))

    if len(h2s) < 2:
        rep.error("SYS-H2-COUNT", f"成体系文档至少需要 2 个 H2 章节，实际 {len(h2s)} 个", 1,
                  "单章内容更适合写成 kind: entry 的条目；确要成体系就补足章节")

    expected = 1
    for h in h2s:
        m = CN_NUM_RE.match(h["title"])
        if not m:
            rep.error("SYS-H2-NUM", f"H2「{h['title']}」缺少中文数字编号", h["line"],
                      f"改成 `## {CN_NUMERALS[expected - 1]}、<章节名>`")
            continue
        num = CN_NUMERALS.index(m.group(1)) + 1
        if num != expected:
            rep.error("SYS-H2-GAP", f"H2 编号不连续：「{h['title']}」应为「{CN_NUMERALS[expected - 1]}、」",
                      h["line"], "章节编号必须连续，不得跳号")
        expected = num + 1

    current = 0
    for i, line in enumerate(lines):
        if in_ranges(i, ranges):
            continue
        if m2 := H2_RE.match(line):
            m = CN_NUM_RE.match(m2.group(1).strip())
            current = CN_NUMERALS.index(m.group(1)) + 1 if m else 0
            continue
        if m3 := H3_RE.match(line):
            sub = SUB_NUM_RE.match(m3.group(1).strip())
            if not sub:
                rep.error("H3-NUM", f"H3「{m3.group(1).strip()}」缺少 x.y 编号", i + 1,
                          f"改成 `### {current or 1}.1 <子标题>`")
            elif current and int(sub.group(1)) != current:
                rep.error("H3-PARENT", f"H3 编号 {sub.group(1)}.{sub.group(2)} 与父章序号 {current} 不对应",
                          i + 1, f"改成 `### {current}.{sub.group(2)} <子标题>`")

    first_h2_idx = h2s[0]["idx"] if h2s else len(lines)
    lead = "\n".join(l for l in lines[body_start:first_h2_idx] if not H1_RE.match(l)).strip()
    if not lead:
        rep.error("SYS-LEAD", "缺少导语（H1 与第一个 H2 之间需要有定位说明）", body_start + 1,
                  "补一段：文档定位、覆盖范围、结构总览")

    if stage != "skeleton":
        check_typography(rep, lines, ranges)


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

def check_file(path: Path, stage: str) -> Report:
    rep = Report(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    ranges = code_block_ranges(lines)

    fields, body_start = parse_frontmatter(lines)
    if not fields:
        check_frontmatter(rep, lines, fields, body_start)  # 只报 FM-MISSING
        return rep

    kind = check_frontmatter(rep, lines, fields, body_start)

    h1s, h2s = headings(lines, ranges)
    if kind == "system":
        check_system(rep, lines, fields, body_start, h1s, h2s, ranges, stage)
    else:
        # kind 缺失时按 entry 继续查：既报 FM-FIELD，也把结构问题一并暴露出来。
        check_entry(rep, lines, fields, body_start, h1s, h2s, ranges, stage)
    return rep


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        add_help=True,
        description="校验知识文档是否符合 write-knowledge-doc 的骨架契约。",
    )
    parser.add_argument("files", nargs="*", help="待校验的 Markdown 文件，可传多个")
    parser.add_argument("--stage", choices=("skeleton", "draft"), default="draft",
                        help="skeleton 只查结构契约；draft 全查（默认）")
    parser.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = parser.parse_args(argv[1:])

    if not args.files:
        parser.print_help()
        return 2

    reports: list[Report] = []
    io_error = False
    for raw in args.files:
        path = Path(raw)
        if not path.is_file():
            print(f"[ERROR] 文件不存在：{path}", file=sys.stderr)
            io_error = True
            continue
        try:
            reports.append(check_file(path, args.stage))
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[ERROR] 读取失败：{path}：{exc}", file=sys.stderr)
            io_error = True

    if args.json:
        payload = {
            "stage": args.stage,
            "files": [
                {
                    "file": str(r.path),
                    "ok": r.errors == 0 and not (args.strict and r.warnings),
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "findings": [f.as_dict() for f in r.findings],
                }
                for r in reports
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in reports:
            print(f"== {r.path} ==")
            if not r.findings:
                print("  通过：结构与硬规则检查全部通过\n")
                continue
            for f in r.findings:
                loc = f"L{f.line}" if f.line else "  "
                print(f"  [{f.level}] {loc:<5} {f.code:<15} {f.message}")
                if f.fix:
                    print(f"          修：{f.fix}")
            print(f"  小计：{r.errors} 个 ERROR，{r.warnings} 个 WARN\n")

    if io_error:
        return 2
    failed = any(r.errors or (args.strict and r.warnings) for r in reports)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
