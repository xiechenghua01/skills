#!/usr/bin/env python3
"""只读检查单个技能包；仅用标准库，不执行脚本或检查外链健康。"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


EXCLUSIONS = [
    "不检查外链健康，不执行目标脚本，不联网，不修改文件。",
    "不检查 § 引用、自然语言 N 项计数、语义正确性或自动触发行为。",
    "不检查仓库六字段规则、市场注册或版本一致性。",
    "只覆盖常见行内链接、单行引用定义、引用式链接和 Markdown 标题锚点；不是完整 Markdown/YAML 解析器。",
    "代码围栏和行内代码中的模板链接不作为真实链接；仅检查独立反引号内的实际 scripts/... 路径。",
]


@dataclass
class Finding:
    level: str
    code: str
    path: str
    line: int
    message: str
    fix: str


class Report:
    def __init__(self, root: Path, strict: bool = False) -> None:
        self.root = root
        self.strict = strict
        self.findings: list[Finding] = []
        self.read_failed = False
        self.scanned: list[str] = []

    def add(self, level: str, code: str, path: Path, line: int,
            message: str, fix: str) -> None:
        self.findings.append(Finding(level, code, str(path), line, message, fix))

    def read_error(self, path: Path, exc: Exception) -> None:
        self.read_failed = True
        self.add("ERROR", "READ_ERROR", path, 1, f"读取失败：{exc}",
                 "检查文件权限、UTF-8 编码和文件系统状态后重试。")

    @property
    def complete(self) -> bool:
        return not self.read_failed and not any(
            f.level == "UNSUPPORTED" for f in self.findings)

    @property
    def exit_code(self) -> int:
        if not self.complete:
            return 2
        if any(f.level == "ERROR" or (self.strict and f.level == "WARN")
               for f in self.findings):
            return 1
        return 0

    def to_dict(self) -> dict:
        return {
            "ok": self.exit_code == 0,
            "complete": self.complete,
            "error": sum(f.level == "ERROR" for f in self.findings),
            "warn": sum(f.level == "WARN" for f in self.findings),
            "unsupported": sum(f.level == "UNSUPPORTED" for f in self.findings),
            "findings": [asdict(f) for f in self.findings],
            "scanned": self.scanned,
            "coverage": EXCLUSIONS,
        }


def unsupported(report: Report, code: str, path: Path, line: int,
                message: str) -> None:
    report.add("UNSUPPORTED", code, path, line, message,
               "改用受支持的单行格式，或用专用解析器人工复核；本工具未检查此项。")


def scalar(raw: str) -> tuple[str | None, str | None]:
    """返回字符串值与失败类型；复杂/多行 YAML 不冒充语法错误。"""
    value = raw.strip()
    if not value or value.startswith("#"):
        return "", None
    if value[0] in "|>[{&*!%@`":
        return None, "UNSUPPORTED"
    if value[0] in "\"'":
        quote = value[0]
        result: list[str] = []
        i = 1
        escapes = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n",
                   "v": "\v", "f": "\f", "r": "\r", "e": "\x1b", " ": " ",
                   '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0",
                   "L": "\u2028", "P": "\u2029"}
        while i < len(value):
            char = value[i]
            if char == quote:
                if quote == "'" and i + 1 < len(value) and value[i + 1] == "'":
                    result.append("'")
                    i += 2
                    continue
                rest = value[i + 1:].strip()
                if rest and not rest.startswith("#"):
                    return None, "ERROR"
                return "".join(result), None
            if quote == '"' and char == "\\":
                i += 1
                if i >= len(value):
                    return None, "UNSUPPORTED"
                char = value[i]
                if char in escapes:
                    result.append(escapes[char])
                elif char in "xuU":
                    size = {"x": 2, "u": 4, "U": 8}[char]
                    digits = value[i + 1:i + 1 + size]
                    try:
                        if len(digits) != size:
                            raise ValueError
                        result.append(chr(int(digits, 16)))
                    except ValueError:
                        return None, "ERROR"
                    i += size
                else:
                    return None, "ERROR"
            else:
                result.append(char)
            i += 1
        return None, "UNSUPPORTED"
    value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
    if re.search(r":(?:\s|$)", value) or re.match(r"[-?:]\s", value):
        return None, "UNSUPPORTED"
    return value, None


def check_header(text: str, path: Path, report: Report) -> int:
    lines = text.splitlines()
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        report.add("ERROR", "FRONTMATTER_MISSING", path, 1,
                   "SKILL.md 缺少文件开头的 frontmatter。", "在文件开头添加 --- 和 name、description。")
        return 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if end is None:
        report.add("ERROR", "FRONTMATTER_UNCLOSED", path, 1,
                   "frontmatter 缺少结束标记。", "在头部末尾添加单独一行 ---。")
        return len(lines)
    fields: dict[str, tuple[int, str | None]] = {}
    for i in range(1, end):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][\w-]*)\s*:\s*(.*)", raw)
        if not match:
            unsupported(report, "FRONTMATTER_UNSUPPORTED", path, i + 1,
                        "不支持此 YAML 结构（可能是嵌套、复杂键或多行值），未检查。")
            continue
        key, raw_value = match.groups()
        if key in fields:
            report.add("ERROR", "FRONTMATTER_DUPLICATE", path, i + 1,
                       f"头部字段 {key} 重复，首次位于第 {fields[key][0]} 行。", "保留唯一字段定义。")
        value, failure = scalar(raw_value)
        if failure == "UNSUPPORTED":
            unsupported(report, "FRONTMATTER_UNSUPPORTED", path, i + 1,
                        f"字段 {key} 使用未支持的复杂或多行 YAML，未检查。")
        elif failure:
            report.add("ERROR", "FRONTMATTER_SCALAR_INVALID", path, i + 1,
                       f"字段 {key} 的引号或转义非法。", "使用正确闭合、正确转义的单行字符串。")
        fields.setdefault(key, (i + 1, value))
    for key in ("name", "description"):
        if key not in fields:
            # 复杂 YAML 可能实际定义了字段，不能据此断言缺失。
            if not any(f.code == "FRONTMATTER_UNSUPPORTED" for f in report.findings):
                report.add("ERROR", "FRONTMATTER_REQUIRED", path, 1,
                           f"缺少必需字段 {key}。", f"添加单行字符串字段 {key}。")
            continue
        line, value = fields[key]
        if value is None:
            continue
        raw_value = lines[line - 1].split(":", 1)[1].strip()
        if not value.strip() or (raw_value[:1] not in "\"'" and
                                (value.lower() in ("null", "~", "true", "false") or
                                 re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value))):
            report.add("ERROR", "FRONTMATTER_REQUIRED", path, line,
                       f"字段 {key} 必须是非空字符串。", f"为 {key} 填写非空字符串，必要时加引号。")
        elif key == "name":
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) or len(value) > 64:
                report.add("ERROR", "NAME_INVALID", path, line,
                           "name 应是 1–64 字符的小写 kebab-case。", "使用小写字母、数字及单个连接符。")
            if value != report.root.name:
                report.add("ERROR", "NAME_DIRECTORY_MISMATCH", path, line,
                           f"name {value!r} 与目录名 {report.root.name!r} 不一致。", "让 name 与技能目录名一致。")
    return end + 1


def blank(text: str) -> str:
    return "".join("\n" if char == "\n" else " " for char in text)


def without_fences(text: str, path: Path, report: Report, start: int = 0) -> str:
    lines = text.splitlines(keepends=True)
    fence: tuple[str, int] | None = None
    comment = False
    opened = 0
    for i, raw in enumerate(lines):
        if i < start:
            lines[i] = blank(raw)
            continue
        if not fence and not comment:
            probe = re.sub(r"^(?: {0,3}> ?)+", "", raw)
            opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", probe.rstrip("\r\n"))
            if opening and not (opening[1][0] == "`" and "`" in opening[2]):
                fence = (opening[1][0], len(opening[1]))
                opened = i + 1
                lines[i] = blank(raw)
                continue
        if not fence:
            parts = []
            position = 0
            while position < len(raw):
                if comment:
                    end = raw.find("-->", position)
                    finish = len(raw) if end < 0 else end + 3
                    parts.append(blank(raw[position:finish]))
                    position = finish
                    comment = end < 0
                else:
                    begin = raw.find("<!--", position)
                    if begin < 0:
                        parts.append(raw[position:])
                        break
                    parts.append(raw[position:begin])
                    position = begin
                    comment = True
            raw = "".join(parts)
            lines[i] = raw
        probe = re.sub(r"^(?: {0,3}> ?)+", "", raw)
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", probe.rstrip("\r\n"))
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
            lines[i] = blank(raw)
        elif match and not (match[1][0] == "`" and "`" in match[2]):
            fence = (match[1][0], len(match[1]))
            opened = i + 1
            lines[i] = blank(raw)
        elif re.match(r"^(?: {4}|\t)", raw) and ("[" in raw or "`" in raw):
            unsupported(report, "MARKDOWN_UNSUPPORTED", path, i + 1,
                        "缩进代码或列表嵌套中的链接/代码无法可靠区分，未检查。")
            lines[i] = blank(raw)
    if fence:
        report.add("WARN", "FENCE_UNCLOSED", path, opened,
                   "代码围栏未闭合，后续内容按代码忽略。", "补上同类型且长度足够的结束围栏。")
    return "".join(lines)


def inline_spans(text: str):
    i = 0
    while i < len(text):
        if text[i] != "`" or escaped(text, i):
            i += 1
            continue
        run = re.match(r"`+", text[i:])[0]
        end = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", text[i + len(run):])
        if not end:
            i += len(run)
            continue
        finish = i + len(run) + end.end()
        if re.search(r"\n[ \t\r]*\n", text[i:finish]):
            i += len(run)
            continue
        yield i, finish, text[i + len(run):finish - len(run)]
        i = finish


def escaped(text: str, index: int) -> bool:
    i = index - 1
    while i >= 0 and text[i] == "\\":
        i -= 1
    return (index - 1 - i) % 2 == 1


def markdown_unescape(value: str) -> str:
    return html.unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", value))


def label_key(label: str) -> str:
    return re.sub(r"\s+", " ", markdown_unescape(label).strip()).casefold()


def destination(value: str) -> str | None:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("<"):
        end = next((i for i in range(1, len(value)) if value[i] == ">" and not escaped(value, i)), -1)
        if end < 0:
            return None
        dest, rest = value[1:end], value[end + 1:].strip()
    else:
        depth = 0
        end = len(value)
        for i, char in enumerate(value):
            if escaped(value, i):
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char.isspace() and depth == 0:
                end = i
                break
        if depth != 0:
            return None
        dest, rest = value[:end], value[end:].strip()
    if rest and not re.fullmatch(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\([^()]*\)', rest, re.S):
        return None
    return markdown_unescape(dest)


def close_bracket(text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 1
    for i in range(start + 1, len(text)):
        if escaped(text, i):
            continue
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
    return None


def headings(text: str) -> set[str]:
    used: set[str] = set()
    previous = ""
    for raw in text.splitlines():
        match = re.match(r"^ {0,3}#{1,6}(?:\s+|$)(.*)$", raw)
        if match:
            title = re.sub(r"\s+#+\s*$", "", match[1]).strip()
        elif previous.strip() and re.fullmatch(r" {0,3}(?:=+|-+)\s*", raw):
            title = previous.strip()
        else:
            previous = raw
            continue
        title = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", title)
        title = re.sub(r"!?\[([^\]]+)\]\[[^\]]*\]", r"\1", title)
        title = re.sub(r"<[^>]*>", "", title)
        title = markdown_unescape(title).lower()
        base = "".join("-" if char.isspace() else char for char in title
                       if char.isspace() or char in "-_" or unicodedata.category(char)[0] in "LNM")
        slug = base
        suffix = 0
        while slug in used:
            suffix += 1
            slug = f"{base}-{suffix}"
        used.add(slug)
        previous = ""
    return used


class Validator:
    def __init__(self, root: Path, strict: bool = False) -> None:
        self.root = root.resolve()
        self.report = Report(self.root, strict)
        self.documents: dict[Path, str] = {}
        self.visible: dict[Path, str] = {}
        self.anchors: dict[Path, set[str]] = {}

    def safe(self, path: Path, source: Path, line: int) -> Path | None:
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(self.root):
                self.report.add("ERROR", "PATH_OUTSIDE_SKILL", source, line,
                                f"文件引用或符号链接越出技能包：{path}", "把目标放入技能包，并改用包内相对路径。")
                return None
            return resolved
        except (OSError, RuntimeError) as exc:
            self.report.read_error(path, exc)
            return None

    def read(self, path: Path) -> str | None:
        if path in self.documents:
            return self.documents[path]
        if self.safe(path, path, 1) is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.report.read_error(path, exc)
            return None
        self.documents[path] = text
        self.report.scanned.append(str(path))
        start = check_header(text, path, self.report) if path == self.root / "SKILL.md" else 0
        if start == 0 and path.name != "SKILL.md" and text.startswith("---\n"):
            lines = text.splitlines()
            end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
            if end is not None:
                start = end + 1
        visible = without_fences(text, path, self.report, start)
        self.visible[path] = visible
        self.anchors[path] = headings(visible)
        return text

    def walk(self, directory: Path):
        try:
            with os.scandir(directory) as entries:
                paths = sorted(entries, key=lambda entry: entry.name)
            for entry in paths:
                path = Path(entry.path)
                if self.safe(path, path, 1) is None:
                    continue
                if entry.is_symlink():
                    # 真实包内目录还会被正常遍历；不沿符号链接递归。
                    if path.suffix.lower() == ".md" and path.is_file():
                        yield path
                elif entry.is_dir(follow_symlinks=False):
                    yield from self.walk(path)
                elif path.suffix.lower() == ".md" and entry.is_file(follow_symlinks=False):
                    yield path
        except OSError as exc:
            self.report.read_error(directory, exc)

    def reference(self, source: Path, line: int, value: str, script: bool = False) -> None:
        try:
            parts = urlsplit(value)
        except ValueError:
            unsupported(self.report, "LINK_UNSUPPORTED", source, line,
                        f"无法可靠解析链接目标 {value!r}，未检查。")
            return
        if parts.scheme or parts.netloc or value.startswith("//"):
            return
        target = source.parent / unquote(parts.path) if parts.path else source
        if self.safe(target, source, line) is None:
            return
        try:
            exists = target.is_file() if script else target.exists()
            if not exists:
                self.report.add("ERROR", "SCRIPT_MISSING" if script else "LINK_MISSING", source, line,
                                f"{'脚本' if script else '本地链接'}目标不存在：{value}", "修正相对路径，或补齐被引用的文件。")
                return
        except OSError as exc:
            self.report.read_error(target, exc)
            return
        fragment = unquote(parts.fragment)
        if script or not fragment:
            return
        if target.suffix.lower() != ".md":
            unsupported(self.report, "ANCHOR_UNSUPPORTED", source, line,
                        f"非 Markdown 文件锚点 {value!r} 未检查。")
        elif self.read(target) is not None and fragment not in self.anchors[target]:
            if re.search(r"<(?:a|[^ >]+)\b[^>]*\b(?:id|name)\s*=", self.visible[target], re.I):
                unsupported(self.report, "ANCHOR_UNSUPPORTED", source, line,
                            f"锚点 {fragment!r} 可能来自 HTML，未检查。")
            else:
                self.report.add("ERROR", "ANCHOR_MISSING", source, line,
                                f"找不到 Markdown 标题锚点：{value}", "按标题生成的中文/小写 slug 及重复后缀修正锚点。")

    def scan(self, path: Path) -> None:
        text = self.visible[path]
        for begin, end, content in inline_spans(text):
            candidate = content.strip()
            segments = candidate.split("/")
            template = any(segment in ("...", "…") for segment in segments)
            if not template and re.fullmatch(r"scripts/[^\s<>\[\]{}*?$`]+", candidate):
                self.reference(path, text.count("\n", 0, begin) + 1, candidate, script=True)
        for begin, end, _ in reversed(list(inline_spans(text))):
            text = text[:begin] + blank(text[begin:end]) + text[end:]
        refs: dict[str, str] = {}
        pieces = []
        for line, raw in enumerate(text.splitlines(keepends=True), 1):
            match = re.match(r"^ {0,3}\[([^\]]+)\]:\s*(.*)$", raw.rstrip("\r\n"))
            if match:
                key = label_key(match[1])
                dest = destination(match[2]) if match[2].strip() else None
                if dest is None:
                    unsupported(self.report, "LINK_UNSUPPORTED", path, line,
                                "复杂或跨行引用定义未检查。")
                elif key in refs:
                    self.report.add("WARN", "REFERENCE_DUPLICATE", path, line,
                                    f"引用标签 {match[1]!r} 重复，按首个定义解析。", "删除重复定义或改用不同标签。")
                else:
                    refs[key] = dest
                    self.reference(path, line, dest)
                pieces.append(blank(raw))
            else:
                pieces.append(raw)
        text = "".join(pieces)
        for match in re.finditer(r"<(?:a|img)\b[^>]*\b(?:href|src)\s*=", text, re.I):
            unsupported(self.report, "LINK_UNSUPPORTED", path, text.count("\n", 0, match.start()) + 1,
                        "原始 HTML 文件引用未检查。")
        i = 0
        while i < len(text):
            if text[i] != "[" or escaped(text, i):
                i += 1
                continue
            end = close_bracket(text, i, "[", "]")
            if end is None:
                i += 1
                continue
            label = text[i + 1:end]
            line = text.count("\n", 0, i) + 1
            after = end + 1
            if after < len(text) and text[after] == "(":
                finish = close_bracket(text, after, "(", ")")
                if finish is None:
                    unsupported(self.report, "LINK_UNSUPPORTED", path, line,
                                "疑似未闭合或复杂行内链接，未检查。")
                    i = after + 1
                    continue
                dest = destination(text[after + 1:finish])
                if dest is None:
                    unsupported(self.report, "LINK_UNSUPPORTED", path, line,
                                "复杂行内链接目标或标题未检查。")
                else:
                    self.reference(path, line, dest)
                i = finish + 1
            elif after < len(text) and text[after] == "[":
                finish = close_bracket(text, after, "[", "]")
                if finish is None:
                    unsupported(self.report, "LINK_UNSUPPORTED", path, line,
                                "疑似未闭合引用式链接，未检查。")
                    i = after + 1
                    continue
                key = label_key(text[after + 1:finish] or label)
                if key not in refs:
                    self.report.add("ERROR", "REFERENCE_UNDEFINED", path, line,
                                    f"引用式链接缺少标签定义：{key}", "补上单行 [标签]: 相对路径 定义。")
                i = finish + 1
            else:
                key = label_key(label)
                if key in refs:
                    self.reference(path, line, refs[key])
                i = end + 1

    def run(self) -> Report:
        skill = self.root / "SKILL.md"
        if self.safe(skill, skill, 1) is not None:
            try:
                if not skill.is_file():
                    self.report.add("ERROR", "SKILL_MISSING", skill, 1,
                                    "技能目录缺少 SKILL.md 文件。", "创建带 name、description 的 SKILL.md。")
                else:
                    self.read(skill)
            except OSError as exc:
                self.report.read_error(skill, exc)
        for path in self.walk(self.root):
            self.read(path)
        for path in list(self.visible):
            self.scan(path)
        return self.report


def validate_skill(skill_dir: Path | str, strict: bool = False) -> Report:
    root = Path(skill_dir).expanduser().absolute()
    if not root.is_dir():
        raise ValueError(f"参数必须是存在的技能目录，不能是单个文件：{root}")
    return Validator(root, strict).run()


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"参数错误：{message}")


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="只读检查单个技能目录中的头部、本地链接、标题锚点和脚本引用。")
    parser.add_argument("skill_dir", help="技能目录路径（不接受单个文件）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    parser.add_argument("--strict", action="store_true", help="把 WARN 也视为失败；UNSUPPORTED 始终返回 2")
    arguments = sys.argv[1:] if argv is None else argv
    try:
        args = parser.parse_args(arguments)
        report = validate_skill(args.skill_dir, args.strict)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"参数或读取错误：{exc}", file=sys.stderr)
        if "--json" in arguments:
            print(json.dumps({"ok": False, "complete": False, "error": 1, "warn": 0,
                              "unsupported": 0, "findings": [asdict(Finding(
                                  "ERROR", "ARGUMENT_ERROR", "", 0, str(exc),
                                  "传入存在且可读取的技能目录。"))], "scanned": [],
                              "coverage": EXCLUSIONS}, ensure_ascii=False))
        return 2
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        status = "通过" if report.exit_code == 0 else ("未完成" if not report.complete else "失败")
        print(f"{status}：扫描 {len(report.scanned)} 个 Markdown 文件，"
              f"ERROR {report.to_dict()['error']}，WARN {report.to_dict()['warn']}，"
              f"UNSUPPORTED {report.to_dict()['unsupported']}")
        for finding in report.findings:
            print(f"[{finding.level}] {finding.code} {finding.path}:{finding.line} {finding.message}")
            print(f"  修复建议：{finding.fix}")
        for item in EXCLUSIONS:
            print(f"覆盖边界：{item}")
    for finding in report.findings:
        if finding.code == "READ_ERROR":
            print(f"读取错误：{finding.path}：{finding.message}", file=sys.stderr)
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
