#!/usr/bin/env python3
"""校验知识文档是否符合 write-knowledge-doc 的结构规范。

两种模式自动判定：
- 模式一（条目式）：有 frontmatter 六字段。全套检查——frontmatter 字段与枚举取值、
  五章编号与顺序（1-5 按序、编号不得省略）、导语三行标注、Dead End、来源导向标题等。
- 模式二（成体系）：无 frontmatter。检查 H1 唯一、H2 中文数字编号连续、H3 编号与父章对应。

检查分两级：
- ERROR：结构或硬规则违反，必须修复后才能入库。
- WARN：建议处理项（概念名泄漏进「问题」章节、缺例子、裸链接堆砌、加粗通胀等）。

用法：python3 scripts/validate_knowledge_entry.py <文档文件> [更多文件...]
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

STATUS_VALUES = ("seedling", "budding", "evergreen")
VERIFIED_VALUES = ("all", "partial", "none")
REQUIRED_FIELDS = ("title", "status", "created", "updated", "tags", "verified")
CORE_SECTIONS = (
    "它解决什么问题",
    "它怎么解决的",
    "一个具体场景",
    "边界与例外",
    "相关概念",
)
# 来源导向标题的典型用词：出现在概念标题里几乎一定是反模式。
SOURCE_ORIENTED_WORDS = (
    "读书笔记",
    "学习笔记",
    "读后感",
    "心得",
    "复盘",
    "摘录",
    "转载",
    "翻译",
)
CN_NUMERALS = "一二三四五六七八九十"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)")
WIKI_LINK_RE = re.compile(r"\[\[[^\]]+\]\]")
H2_RE = re.compile(r"^##\s+(.*)$")
H3_RE = re.compile(r"^###\s+(.*)$")
H1_RE = re.compile(r"^#\s+(\S.*)$")
CN_NUM_RE = re.compile(r"^([一二三四五六七八九十]+)、")
SUB_NUM_RE = re.compile(r"^(\d+)\.(\d+)\s")


def parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """极简 frontmatter 解析：仅支持单行 key: value 与 [a, b] 内联列表。

    行内注释按 ' #'（空格加井号）剥离，与模板中 `status: seedling  # ...` 的写法兼容。
    返回 (字段表, 正文起始行号)；没有合法围栏时字段表为空。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, str] = {}
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return fields, i
        if " #" in line:
            line = line[: line.index(" #")]
        match = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return {}, 0


def split_sections(body_lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """按 H2 切分正文，返回 (导语行, [(章节标题, 章节行)])。H1 与 H3 以下不进入导语。"""
    lead: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current: list[str] = []
    for line in body_lines:
        m = H2_RE.match(line)
        if m:
            if current_title is not None:
                sections.append((current_title, current))
            current_title, current = m.group(1).strip(), []
        elif current_title is None:
            if not H1_RE.match(line):
                lead.append(line)
        else:
            current.append(line)
    if current_title is not None:
        sections.append((current_title, current))
    return lead, sections


def code_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """返回代码块 (起始行号, 结束行号) 列表（行号相对传入的 lines）。"""
    blocks: list[tuple[int, int]] = []
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            if start is None:
                start = i
            else:
                blocks.append((start, i))
                start = None
    if start is not None:
        blocks.append((start, len(lines) - 1))
    return blocks


def in_code_block(idx: int, blocks: list[tuple[int, int]]) -> bool:
    return any(start <= idx <= end for start, end in blocks)


def check_typography(lines: list[str], body_start: int, add) -> None:
    """排版检查：加粗通胀与行宽（跳过代码块、表格行、标题、frontmatter）。"""
    fm_block = [(0, body_start)]
    blocks_all = sorted(fm_block + [(body_start + s + 1, body_start + e + 1)
                                    for s, e in code_blocks(lines[body_start:])])
    for i, line in enumerate(lines):
        if in_code_block(i, blocks_all):
            continue
        if line.strip().startswith("|") or line.strip().startswith("#"):
            continue
        bold_count = line.count("**") // 2
        if bold_count > 3:
            add("WARN", f"一行内加粗 {bold_count} 处（每段最多 2-3 处）", i + 1)
        if len(line) > 100:
            add("WARN", f"正文行宽 {len(line)} 字符超过 100", i + 1)


def check_mode1(lines: list[str], fields: dict[str, str], body_start: int,
                add) -> None:
    """模式一（条目式）：有 frontmatter，全套检查。"""
    err = lambda msg, line=0: add("ERROR", msg, line)
    warn = lambda msg, line=0: add("WARN", msg, line)

    # ---- frontmatter ----
    fm_lines = {name: i for i, line in enumerate(lines[1:body_start], start=2)
                if (name := line.split(":", 1)[0].strip()) in REQUIRED_FIELDS}
    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            err(f"frontmatter 缺少必填字段 {field}", fm_lines.get(field, 1))
    if fields.get("status") and fields["status"] not in STATUS_VALUES:
        err(f"status 取值非法：{fields['status']!r}，应为 {' / '.join(STATUS_VALUES)}", fm_lines.get("status"))
    if fields.get("verified") and fields["verified"] not in VERIFIED_VALUES:
        err(f"verified 取值非法：{fields['verified']!r}，应为 {' / '.join(VERIFIED_VALUES)}", fm_lines.get("verified"))
    for date_field in ("created", "updated"):
        value = fields.get(date_field, "")
        if value and not DATE_RE.match(value):
            err(f"{date_field} 应为 YYYY-MM-DD，实际 {value!r}", fm_lines.get(date_field))
        elif value and DATE_RE.match(value):
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                err(f"{date_field} 日期不存在：{value!r}", fm_lines.get(date_field))

    # ---- H1 与 title 一致性 ----
    body = lines[body_start:]
    h1_lines = [(body_start + i + 1, line[2:].strip())
                for i, line in enumerate(body) if H1_RE.match(line)]
    if len(h1_lines) != 1:
        err(f"H1 应有且仅有一个，实际 {len(h1_lines)} 个", body_start + 1)
    elif fields.get("title") and h1_lines[0][1] != fields["title"]:
        err(f"H1 {h1_lines[0][1]!r} 与 title {fields['title']!r} 不一致", h1_lines[0][0])

    # ---- 来源导向标题 ----
    title = fields.get("title", "")
    hit_words = [w for w in SOURCE_ORIENTED_WORDS if w in title]
    if hit_words:
        err(f"标题疑似来源导向（含 {'/'.join(hit_words)}）：标题必须是概念本身", fm_lines.get("title"))

    # ---- 章节 ----
    lead, sections = split_sections(body)
    titles = [t for t, _ in sections]
    offset = {t: body_start + i + 1 for i, line in enumerate(body)
              if (m := H2_RE.match(line)) and (t := m.group(1).strip())}

    # ---- 核心章节：存在性 + 编号 + 顺序（编号是固定契约） ----
    core_hits: list[tuple[int, int, str]] = []  # (文档内出现次序, 期望编号, 标题)
    for idx, core in enumerate(CORE_SECTIONS, start=1):
        match_title = next((t for t in titles if core in t), None)
        if match_title is None:
            err(f"缺少核心章节「{core}」")
            continue
        core_hits.append((len(core_hits), idx, match_title))
        m = re.match(rf"^(\d+)\.\s+{re.escape(core)}", match_title)
        if not m:
            err(f"核心章节「{core}」缺少阿拉伯数字编号，应为「{idx}. {core}」", offset.get(match_title))
        elif int(m.group(1)) != idx:
            err(f"核心章节编号与顺序错乱：「{match_title}」应为「{idx}. {core}」", offset.get(match_title))
    # 顺序检查：出现的核心章节编号应严格递增（缺章时跳过，不乱报编号错乱）
    prev_idx = 0
    for _, idx, t in core_hits:
        if idx <= prev_idx:
            err(f"核心章节顺序错乱：编号 {idx} 出现在编号 {prev_idx} 之后（「{t}」）", offset.get(t))
        prev_idx = idx

    def find_section(core: str) -> tuple[str, list[str]] | None:
        for t, c in sections:
            if core in t:
                return t, c
        return None

    # ---- 导语 ----
    lead_text = "\n".join(lead).strip()
    lead_offset = body_start + 1
    if not lead_text:
        err("缺少导语（H1 与第一个 ## 之间需要有正文）", lead_offset)
    else:
        first_line = lead_text.splitlines()[0]
        if title and not first_line.startswith(title):
            warn(f"导语首句不以概念名开头（标题应作第一句主语）：{first_line[:30]}...", lead_offset)
        if "成熟度（status:" not in lead_text:
            warn("导语缺少「成熟度（status: 值）」标注行（知识库不渲染 frontmatter 注释，读者靠正文理解字段）", lead_offset)
        if "核实状态（verified:" not in lead_text:
            warn("导语缺少「核实状态（verified: 值）」标注行（知识库不渲染 frontmatter 注释，读者靠正文理解字段）", lead_offset)

    # ---- 相关概念：Dead End 与裸链接 ----
    related = find_section("相关概念")
    if related:
        _, rel_lines = related
        rel_text = "\n".join(rel_lines)
        links = MD_LINK_RE.findall(rel_text) + WIKI_LINK_RE.findall(rel_text)
        if not links and not re.search(r"^\s*[-*\d]", rel_text, re.MULTILINE):
            err("「相关概念」章节没有任何链接或列表项（Dead End）", offset.get(titles[0], 0))
        link_rows = [i for i, line in enumerate(rel_lines)
                     if MD_LINK_RE.search(line) or WIKI_LINK_RE.search(line)]
        if len(link_rows) >= 2:
            bare = 0
            for i in link_rows:
                stripped = MD_LINK_RE.sub("", rel_lines[i])
                stripped = WIKI_LINK_RE.sub("", stripped)
                if len(stripped.strip(" -\t")) < 8:
                    bare += 1
            if bare > len(link_rows) / 2:
                warn("「相关概念」中过半链接行没有说明理由（无理由链接堆砌）")

    # ---- 「它解决什么问题」不得泄漏概念名 ----
    problem = find_section("它解决什么问题")
    if problem and title and len(title) >= 2:
        _, prob_lines = problem
        prob_text = "\n".join(l for l in prob_lines if not l.strip().startswith("#"))
        if title in prob_text:
            warn(f"「它解决什么问题」正文出现了概念名 {title!r}（该节应先定义问题、尽量不提术语）")

    # ---- 「一个具体场景」必须有例子特征 ----
    scene = find_section("一个具体场景")
    if scene:
        _, scene_lines = scene
        scene_text = "\n".join(scene_lines)
        blocks = code_blocks(scene_lines)
        has_example = (
            bool(blocks)
            or bool(INLINE_CODE_RE.search(scene_text))
            or "http" in scene_text
            or bool(re.search(r"^\s*\|", scene_text, re.MULTILINE))
        )
        if not has_example:
            warn("「一个具体场景」没有代码块、行内代码、URL 或表格等例子特征（每个概念都要配具体例子）")

    # ---- 空章节 ----
    for t, c in sections:
        if not "\n".join(c).strip():
            warn(f"章节「{t}」没有内容", offset.get(t))

    check_typography(lines, body_start, add)


def check_mode2(lines: list[str], add) -> None:
    """模式二（成体系）：无 frontmatter，检查编号体系与基本结构。"""
    err = lambda msg, line=0: add("ERROR", msg, line)
    warn = lambda msg, line=0: add("WARN", msg, line)

    h1_lines = [(i + 1, m.group(1).strip())
                for i, line in enumerate(lines) if (m := H1_RE.match(line))]
    if len(h1_lines) != 1:
        err(f"H1 应有且仅有一个，实际 {len(h1_lines)} 个", 1)
    if not h1_lines:
        return

    # H2：中文数字编号且连续；H3：x.y 编号与当前父章对应（同一遍历跟踪父章序号）
    h2_entries = [(i + 1, m.group(1).strip())
                  for i, line in enumerate(lines) if (m := H2_RE.match(line))]
    if not h2_entries:
        err("成体系文档没有任何 H2 章节", 1)
    expected = 1
    current_h2_num = 0
    for i, line in enumerate(lines):
        m2 = H2_RE.match(line)
        if m2:
            title = m2.group(1).strip()
            cn = CN_NUM_RE.match(title)
            if not cn:
                err(f"H2「{title}」缺少中文数字编号（应为「一、二、三……」样式）", i + 1)
            else:
                num = CN_NUMERALS.index(cn.group(1)) + 1
                if num != expected:
                    err(f"H2 编号不连续：「{title}」应为「{CN_NUMERALS[expected-1]}、」", i + 1)
                current_h2_num = num
                expected = num + 1
            continue
        m3 = H3_RE.match(line)
        if m3:
            sub = SUB_NUM_RE.match(m3.group(1).strip())
            if not sub:
                warn(f"H3「{m3.group(1).strip()}」缺少 x.y 编号（如 1.1）", i + 1)
            elif current_h2_num and int(sub.group(1)) != current_h2_num:
                warn(f"H3 编号 {sub.group(1)}.{sub.group(2)} 与父章序号 {current_h2_num} 不对应", i + 1)

    # 导语：H1 与第一个 H2 之间应有定位说明
    first_h2 = min((i for i, line in enumerate(lines) if H2_RE.match(line)), default=len(lines))
    lead_text = "\n".join(l for l in lines[1:first_h2] if not H1_RE.match(l)).strip()
    if not lead_text:
        warn("成体系文档缺少导语（H1 与第一个章节之间应有定位与结构总览）", 2)

    check_typography(lines, 0, add)


def check_entry(path: Path) -> list[tuple[str, str, int]]:
    """返回 (级别, 规则说明, 行号) 列表；级别为 ERROR 或 WARN。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    problems: list[tuple[str, str, int]] = []

    def add(level: str, msg: str, line: int) -> None:
        problems.append((level, msg, line))

    fields, body_start = parse_frontmatter(text)
    if fields:
        check_mode1(lines, fields, body_start, add)
    else:
        # 无 frontmatter：判定为模式二（成体系文档）。条目忘写 frontmatter 时，
        # 五章的阿拉伯编号会触发模式二的「H2 缺少中文数字编号」错误，仍会被发现。
        check_mode2(lines, add)
    return problems


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    exit_code = 0
    for arg in argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"[ERROR] 文件不存在：{path}")
            exit_code = 1
            continue
        problems = check_entry(path)
        errors = [p for p in problems if p[0] == "ERROR"]
        warns = [p for p in problems if p[0] == "WARN"]
        print(f"== {path} ==")
        if not problems:
            print("  通过：结构与硬规则检查全部通过\n")
            continue
        for level, msg, line_no in problems:
            loc = f"L{line_no}" if line_no else "   "
            print(f"  [{level}] {loc:<5} {msg}")
        print(f"  小计：{len(errors)} 个 ERROR，{len(warns)} 个 WARN\n")
        if errors:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
