#!/usr/bin/env python3
"""STE-ZH 简化技术中文离线规则检查器。

只做机械可判定的检查，判断不了的一律交给人工（覆盖对照见 references/coverage.md）。

两档强度：
- pragmatic（默认）：只查结构规则——虚化动词 R3、句长 R7、双重否定 R10、开放式列举 R17。
- strict：结构规则 + 受控情态词 R11 + 生造状态词 R19。用户点名 ste/STE 或要求合规审计时使用。

用法：
    python3 scripts/validate_ste.py <文件> [--mode strict] [--json]
    python3 scripts/validate_ste.py --text "待检测文本" [--mode strict]

退出码：0 无错误 / 1 有错误 / 2 用法或文件错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 受控情态词只允许这三个，其余近义词一律视为违规（strict 档生效）。
FORBIDDEN_MODALS = [
    (r"应当|应该", "R11", "使用了非法情态词。按语意替换为「必须」「不得」或「可以」"),
    (r"务必", "R11", "使用了非法情态词。必须替换为「必须」"),
    (r"切勿|不要|不应|不该", "R11", "使用了非法情态词。必须替换为「不得」"),
]

# 虚化动词：用抽象名词包装动作，读者看不出到底做了什么（两档都查）。
EMPTY_VERBS = [
    (r"对[^，。\n]{1,20}进行(?:了)?", "R3", "「对……进行」是虚化句式。必须直接写出动作动词"),
    (r"进行(?:了)?(?:修改|优化|调整|删除|增加|检查|测试|重构|配置|发布)", "R3",
     "「进行……」是虚化动词。必须直接写「修改/优化/调整」等动作"),
    (r"开展[^，。\n]{1,20}工作", "R3", "「开展……工作」是虚化句式。必须直接陈述动作"),
    (r"落实[^，。\n]{1,20}(?:工作|措施|要求)", "R3", "「落实……」是虚化句式。必须直接陈述动作"),
    (r"做好[^，。\n]{1,20}(?:工作|准备)", "R3", "「做好……」是虚化句式。必须直接陈述动作"),
]

DOUBLE_NEGATIVES = [
    (r"不能不|不得不|并非不|并非没有|不会不", "R10", "双重否定。必须改为肯定句直接断言"),
]

OPEN_ENDINGS = [
    (r"(?:等等|之类)[，。；\n]", "R17", "开放式列举结尾。必须列全，或指明完整清单的出处"),
]

# 生造状态词：用模糊说法代替十个受控状态词（strict 档生效）。
VAGUE_STATUS = [
    (r"搞定|弄好|弄得差不多|没问题了|差不多完成|基本完成|大体完成", "R19",
     "使用了生造状态词。必须改用受控状态词（已完成/部分完成/未开始/进行中/阻塞/跳过/已验证/未验证/失败/未确认）"),
    (r"理论上(?:没问题|可以|能行)|应该(?:能|可以)跑通", "R19",
     "用推测代替验证结论。必须写明「已验证」或「未验证」，并给出验证方法与结果"),
]

STEP_LIMIT = 30   # 步骤句字数上限（R7）
DESC_LIMIT = 40   # 描述句字数上限（R7）


@dataclass
class Diagnostic:
    line_number: int
    rule_id: str
    level: str
    message: str
    matched_text: str
    suggestion: str

    def as_dict(self) -> dict:
        return {
            "line": self.line_number,
            "rule": self.rule_id,
            "level": self.level,
            "message": self.message,
            "matched": self.matched_text,
            "suggestion": self.suggestion,
        }


def strip_inline_code(line: str) -> str:
    """去掉行内反引号内容，避免把代码里的词当正文判违规。"""
    return re.sub(r"`[^`]*`", "", line)


def count_ste_words(sentence: str) -> int:
    """汉字计 1；连续英文/数字块计 1；标点与空白不计。"""
    clean = re.sub(r"[\s，。；：！？、「」『』（）()\[\]{}]", " ", sentence)
    total = 0
    for word in clean.split():
        total += len(re.findall(r"[\u4e00-\u9fff]", word))
        total += len(re.sub(r"[\u4e00-\u9fff]", " ", word).split())
    return total


def is_step_line(line: str) -> bool:
    """编号或列表项视为步骤句，其余按描述句判句长。"""
    return bool(re.match(r"^\s*(?:\d+[.、)]|[-*+])\s+", line))


def scan_patterns(line: str, line_number: int, patterns, suggestion: str) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    for pattern, rule_id, message in patterns:
        for match in re.finditer(pattern, line):
            found.append(
                Diagnostic(line_number, rule_id, "ERROR", message, match.group(0), suggestion)
            )
    return found


def validate_text(text: str, mode: str = "pragmatic") -> list[Diagnostic]:
    """检查一段文本。mode 取 pragmatic 或 strict。"""
    diagnostics: list[Diagnostic] = []
    in_code_block = False

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # 标题与表格分隔线不参与判定
        if stripped.startswith("#") or re.match(r"^\|?[-:| ]+\|?$", stripped):
            continue

        line = strip_inline_code(raw_line)

        diagnostics.extend(
            scan_patterns(line, idx, EMPTY_VERBS, "消灭虚化动词，直接写明确的动作")
        )
        diagnostics.extend(
            scan_patterns(line, idx, DOUBLE_NEGATIVES, "改为直接肯定的祈使句或判断句")
        )
        diagnostics.extend(
            scan_patterns(line, idx, OPEN_ENDINGS, "列出全部项，或写明完整清单的存放位置")
        )

        if mode == "strict":
            diagnostics.extend(
                scan_patterns(line, idx, FORBIDDEN_MODALS, "仅允许「必须」「不得」「可以」三个情态词")
            )
            diagnostics.extend(
                scan_patterns(line, idx, VAGUE_STATUS, "状态必须落在十个受控状态词内，并区分执行态与验证态")
            )

        # 句长：步骤句 30 字，描述句 40 字
        limit = STEP_LIMIT if is_step_line(raw_line) else DESC_LIMIT
        kind = "步骤句" if limit == STEP_LIMIT else "描述句"
        for sentence in re.split(r"[。！？]", line):
            sentence = sentence.strip()
            if not sentence:
                continue
            words = count_ste_words(sentence)
            if words > limit:
                preview = sentence[:30] + "..." if len(sentence) > 30 else sentence
                diagnostics.append(
                    Diagnostic(
                        idx,
                        "R7",
                        "WARNING",
                        f"{kind}字数超标（当前 {words} 字，上限 {limit} 字）",
                        preview,
                        "按单一动作拆成多个独立单句",
                    )
                )

    return diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STE-ZH 简化技术中文离线检查器")
    parser.add_argument("file", nargs="?", help="待检查的 Markdown 或文本文件")
    parser.add_argument("--text", help="直接传入待检查文本")
    parser.add_argument("--mode", choices=("pragmatic", "strict"), default="pragmatic",
                        help="pragmatic 只查结构规则；strict 追加情态词与状态词（默认 pragmatic）")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = parser.parse_args(argv)

    if args.text:
        content, filename = args.text, "<inline-text>"
    elif args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"错误: 目标文件不存在: {args.file}", file=sys.stderr)
            return 2
        content, filename = path.read_text(encoding="utf-8"), path.name
    else:
        parser.print_help()
        return 2

    diagnostics = validate_text(content, args.mode)
    errors = [d for d in diagnostics if d.level == "ERROR"]
    warnings = [d for d in diagnostics if d.level == "WARNING"]

    if args.json:
        print(
            json.dumps(
                {
                    "file": filename,
                    "mode": args.mode,
                    "ok": not errors,
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "diagnostics": [d.as_dict() for d in diagnostics],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif not diagnostics:
        print(f"[{filename}] 检查通过（{args.mode} 档）：未发现可机械判定的违规项。")
        print("提示：语义类规则（一词一义、主语明确、证据可定位）仍需人工核，见 references/coverage.md。")
    else:
        print(f"[{filename}] 发现 {len(errors)} 处错误，{len(warnings)} 处告警（{args.mode} 档）：\n")
        for d in diagnostics:
            print(f"  第 {d.line_number} 行 [{d.level}] ({d.rule_id}) {d.message}")
            print(f"    违规片段: {d.matched_text!r}")
            print(f"    修改建议: {d.suggestion}\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
