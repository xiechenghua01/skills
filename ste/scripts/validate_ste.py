#!/usr/bin/env python3
"""STE-ZH 简化技术中文离线规则检查器。

用于检查技术文本或 Markdown 文档是否符合 STE-ZH 核心规范。
检查范围包括：
1. 非法情态词（R11：严禁用 应该/应当/务必/切勿/不要 等）
2. 虚化动词短语（R3：禁用 进行/开展/落实/做好 等虚化结构）
3. 双重否定句式（R10：禁用 不能不/不得不/并非不 等）
4. 开放式列举结尾（R17：禁用 等等/之类）
5. 超长描述句检查（R7：描述句字数超过 40 字告警）

用法：
    python3 ste/scripts/validate_ste.py <文件路径>
    python3 ste/scripts/validate_ste.py --text "待检测的文本内容"
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Diagnostic:
    line_number: int
    rule_id: str
    level: str  # "ERROR" | "WARNING"
    message: str
    matched_text: str
    suggestion: str


# 非法情态词匹配（排除受控情态词：必须、不得、可以）
FORBIDDEN_MODALS = [
    (r"应当|应该", "R11", "使用了非法情态词。必须根据语意替换为「必须」或「不得」或「可以」"),
    (r"务必", "R11", "使用了非法情态词。必须替换为「必须」"),
    (r"切勿|不要|不应|不该", "R11", "使用了非法情态词。必须替换为「不得」"),
]

# 虚化动词短语
EMPTY_VERBS = [
    (r"对[^，。\n]{1,20}进行(?:了)?", "R3", "使用了「对……进行」虚化句式。必须直接使用物理动作动词"),
    (r"进行(?:了)?(?:修改|优化|调整|删除|增加|检查|测试|重构|配置|发布)", "R3", "使用了「进行……」虚化动词。必须直接使用「修改/优化/调整」等直接动作"),
    (r"开展[^，。\n]{1,20}工作", "R3", "使用了「开展……工作」虚化句式。必须直接陈述具体动作"),
    (r"落实[^，。\n]{1,20}(?:工作|措施|要求)", "R3", "使用了「落实……」虚化句式。必须直接陈述具体动作"),
    (r"做好[^，。\n]{1,20}(?:工作|准备)", "R3", "使用了「做好……」虚化句式。必须直接陈述具体动作"),
]

# 双重否定
DOUBLE_NEGATIVES = [
    (r"不能不|不得不|并非不|并非没有|不会不", "R10", "使用了双重否定句式。必须采用肯定句直接断言"),
]

# 开放式结尾
OPEN_ENDINGS = [
    (r"(?:等等|之类)[，。；\n]", "R17", "使用了开放式列举结尾。必须列出全部项或指明完整清单出处"),
]


def strip_inline_code(line: str) -> str:
    """去除行内反引号包裹的代码内容，避免代码中的变量或语法误报。"""
    return re.sub(r"`[^`]*`", "", line)


def count_ste_words(sentence: str) -> int:
    """按 STE-ZH 规则统计字数：汉字计 1，连续英文单词/数字计 1，标点不计入。"""
    # 移除标点符号与空白
    clean = re.sub(r"[\s，。；：！？、「」『』（）()\[\]{}]", " ", sentence)
    words = clean.split()
    total = 0
    for w in words:
        # 分离中文字符与字母数字块
        hanzi_count = len(re.findall(r"[\u4e00-\u9fff]", w))
        non_hanzi = re.sub(r"[\u4e00-\u9fff]", " ", w).split()
        total += hanzi_count + len(non_hanzi)
    return total


def validate_text(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    in_code_block = False

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        # 跳过 Markdown 多行代码块
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # 忽略标题行与纯表格分割线
        if stripped.startswith("#") or re.match(r"^\|?[-:| ]+\|?$", stripped):
            continue

        # 剥离行内代码，仅检测技术中文表述
        line = strip_inline_code(raw_line)

        # 1. 检查非法情态词
        for pattern, rule_id, tip in FORBIDDEN_MODALS:
            for m in re.finditer(pattern, line):
                diagnostics.append(
                    Diagnostic(
                        line_number=idx,
                        rule_id=rule_id,
                        level="ERROR",
                        message=tip,
                        matched_text=m.group(0),
                        suggestion="仅允许使用「必须」、「不得」、「可以」三大受控情态词",
                    )
                )

        # 2. 检查虚化动词
        for pattern, rule_id, tip in EMPTY_VERBS:
            for m in re.finditer(pattern, line):
                diagnostics.append(
                    Diagnostic(
                        line_number=idx,
                        rule_id=rule_id,
                        level="ERROR",
                        message=tip,
                        matched_text=m.group(0),
                        suggestion="消灭虚化动词，直接使用明确的动作动词",
                    )
                )

        # 3. 检查双重否定
        for pattern, rule_id, tip in DOUBLE_NEGATIVES:
            for m in re.finditer(pattern, line):
                diagnostics.append(
                    Diagnostic(
                        line_number=idx,
                        rule_id=rule_id,
                        level="ERROR",
                        message=tip,
                        matched_text=m.group(0),
                        suggestion="改为直接肯定的祈使或判断句",
                    )
                )

        # 4. 检查开放式结尾
        for pattern, rule_id, tip in OPEN_ENDINGS:
            for m in re.finditer(pattern, line):
                diagnostics.append(
                    Diagnostic(
                        line_number=idx,
                        rule_id=rule_id,
                        level="ERROR",
                        message=tip,
                        matched_text=m.group(0),
                        suggestion="严禁用「等等/之类」结束列举，必须列全或指明完整清单位置",
                    )
                )

        # 5. 检查长句超标（描述句字数 > 40 字告警）
        sentences = re.split(r"[。！？]", line)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            word_count = count_ste_words(s_clean)
            if word_count > 40:
                diagnostics.append(
                    Diagnostic(
                        line_number=idx,
                        rule_id="R7",
                        level="WARNING",
                        message=f"描述句字数超标（当前 {word_count} 字，上限 40 字）",
                        matched_text=s_clean[:30] + "..." if len(s_clean) > 30 else s_clean,
                        suggestion="将长流水句按单一动作拆分为两个或多个独立单句",
                    )
                )

    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="STE-ZH 简化技术中文离线规则校验工具")
    parser.add_argument("file", nargs="?", help="待检查的 Markdown 或文本文件路径")
    parser.add_argument("--text", help="直接传入待检查的单段文本")
    args = parser.parse_args()

    if args.text:
        content = args.text
        filename = "<inline-text>"
    elif args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"错误: 目标文件不存在: {args.file}", file=sys.stderr)
            return 2
        content = path.read_text(encoding="utf-8")
        filename = path.name
    else:
        parser.print_help()
        return 2

    diags = validate_text(content)
    if not diags:
        print(f"[{filename}] 检查通过：符合 STE-ZH 受控语言规范。")
        return 0

    errors = [d for d in diags if d.level == "ERROR"]
    warnings = [d for d in diags if d.level == "WARNING"]

    print(f"[{filename}] 发现 {len(errors)} 处错误，{len(warnings)} 处告警：\n")
    for d in diags:
        print(f"  第 {d.line_number} 行 [{d.level}] ({d.rule_id}) {d.message}")
        print(f"    违规片段: {d.matched_text!r}")
        print(f"    修改建议: {d.suggestion}\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
