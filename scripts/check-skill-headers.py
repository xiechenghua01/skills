#!/usr/bin/env python3
"""校验各 skill 的 SKILL.md 头部与包版本一致性。

头部六字段与两个版本号的约定见 AGENTS.md「SKILL.md 头部与内容版本」。

检查项：
- 六字段齐全且顺序固定：name / display_name_zh / display_name_en / description / description_en / version
- name 与所在目录同名
- version 形如 vYYYYMMDD 且是真实日期
- 每个值都是单行标量，引号成对：
  * 双引号包裹时，内部不得出现未转义的双引号（YAML 会提前结束字符串，整份头部解析失败）
  * 单引号包裹时，内部的单引号必须写成两个
  * 不加引号（普通标量）时，不得含 ": " 或 " #"——前者解析失败，后者会被静默当成注释截断
- .zcode-plugin/plugin.json 与根目录 marketplace.json 里的 x.y.z 一致

严重级别：
- ERROR 一定失败：引号或标量写错、name 与目录不符、版本格式非法、两处包版本不一致
- WARN  建议处理：缺失六字段中的可选项（历史 skill 常见），可用 --strict 转为失败

用法：
    python3 scripts/check-skill-headers.py
    python3 scripts/check-skill-headers.py --strict
    python3 scripts/check-skill-headers.py write-knowledge-doc    # 只查指定 skill

退出码：0 通过 / 1 有 ERROR（或 --strict 下有 WARN）/ 2 参数或读取错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_ORDER = (
    "name",
    "display_name_zh",
    "display_name_en",
    "description",
    "description_en",
    "version",
)
# 缺失这些字段直接判 ERROR：没有它们，skill 无法被正确识别或触发。
CRITICAL_FIELDS = ("name", "description")
LEGACY_OPTIONAL = ("display_name_zh", "display_name_en", "description_en", "version")

PLAIN_FORBIDDEN_HEAD = set("-?:,[]{}#&*!|>'\"%@`")
VERSION_RE = re.compile(r"^v(\d{4})(\d{2})(\d{2})$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class Problem:
    def __init__(self, level: str, field: str, message: str) -> None:
        self.level = level
        self.field = field
        self.message = message


def parse_header(text: str) -> tuple[list[tuple[int, str, str]], list[Problem], int]:
    """返回 (字段列表 [(行号, key, 原始值)], 解析问题, 正文起始行号)。"""
    problems: list[Problem] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], [Problem("ERROR", "frontmatter", "文件首行不是 ---")], 0

    fields: list[tuple[int, str, str]] = []
    for i, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "---":
            return fields, problems, i
        if not raw.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if not m:
            problems.append(Problem("ERROR", "frontmatter", f"第 {i} 行不是 key: value 形式"))
            continue
        fields.append((i, m.group(1), m.group(2)))
    return [], [Problem("ERROR", "frontmatter", "缺少结束的 ---")], 0


def check_scalar(line_no: int, key: str, raw: str) -> list[Problem]:
    """检查单个值能否被 YAML 安全解析。"""
    problems: list[Problem] = []
    value = raw.strip()

    if not value:
        return [Problem("ERROR", key, f"第 {line_no} 行 {key} 的值为空")]

    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            problems.append(Problem("ERROR", key, f"{key} 以双引号开头但未闭合"))
            return problems
        inner = value[1:-1].replace('\\"', "")
        if '"' in inner:
            problems.append(Problem(
                "ERROR", key,
                f'{key} 外层已用双引号，内部又出现未转义的 "（YAML 会提前结束字符串）。'
                f"英文引用词请改用“ ”或 ' '",
            ))
    elif value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            problems.append(Problem("ERROR", key, f"{key} 以单引号开头但未闭合"))
            return problems
        if value[1:-1].count("'" ) % 2:
            problems.append(Problem("ERROR", key, f"{key} 内部的单引号需写成两个 '' "))
    else:
        if ": " in value or value.endswith(":"):
            problems.append(Problem(
                "ERROR", key, f"{key} 是普通标量却含 ': '（YAML 会解析失败）。加双引号包裹，或改用全角冒号",
            ))
        if " #" in value:
            problems.append(Problem(
                "ERROR", key, f"{key} 含 ' #'，会被当成注释静默截断。加双引号包裹",
            ))
        if value[0] in PLAIN_FORBIDDEN_HEAD:
            problems.append(Problem(
                "ERROR", key, f"{key} 以 YAML 指示符 {value[0]!r} 开头，必须加引号",
            ))
    return problems


def check_version(line_no: int, value: str) -> list[Problem]:
    m = VERSION_RE.match(value.strip())
    if not m:
        return [Problem("ERROR", "version", f"version 应为 vYYYYMMDD（如 v20261028），实际 {value!r}")]
    try:
        datetime.strptime("".join(m.groups()), "%Y%m%d")
    except ValueError:
        return [Problem("ERROR", "version", f"version 里的日期不存在：{value!r}")]
    return []


def load_package_versions(skill_dir: Path) -> tuple[str | None, str | None, list[Problem]]:
    """返回 (plugin.json 版本, marketplace 条目版本, 问题列表)。"""
    problems: list[Problem] = []
    plugin_path = skill_dir / ".zcode-plugin" / "plugin.json"
    plugin_ver = None
    if plugin_path.is_file():
        try:
            plugin_ver = json.loads(plugin_path.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError as exc:
            problems.append(Problem("ERROR", "plugin.json", f"不是合法 JSON：{exc}"))
        else:
            if plugin_ver and not SEMVER_RE.match(str(plugin_ver)):
                problems.append(Problem(
                    "ERROR", "plugin.json", f"包版本应为 x.y.z，实际 {plugin_ver!r}",
                ))
    else:
        problems.append(Problem("ERROR", "plugin.json", "缺少 .zcode-plugin/plugin.json"))

    market_ver = None
    market_path = REPO_ROOT / "marketplace.json"
    if market_path.is_file():
        try:
            entries = json.loads(market_path.read_text(encoding="utf-8")).get("plugins", [])
        except json.JSONDecodeError as exc:
            problems.append(Problem("ERROR", "marketplace.json", f"不是合法 JSON：{exc}"))
            entries = []
        for entry in entries:
            if entry.get("name") == skill_dir.name:
                market_ver = entry.get("version")
                break
        if market_ver is None:
            problems.append(Problem("ERROR", "marketplace.json", "市场条目缺少该插件或未写 version"))
    else:
        problems.append(Problem("ERROR", "marketplace.json", "根目录缺少 marketplace.json"))

    return plugin_ver, market_ver, problems


def check_skill(skill_dir: Path) -> list[Problem]:
    problems: list[Problem] = []
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fields, parse_problems, _ = parse_header(text)
    problems.extend(parse_problems)
    if not fields:
        return problems

    keys = [k for _, k, _ in fields]
    values: dict[str, str] = {}
    for line_no, key, raw in fields:
        values[key] = raw.strip().strip('"').strip("'") if raw.strip()[:1] in "\"'" else raw.strip()
        problems.extend(check_scalar(line_no, key, raw))

    for key in REQUIRED_ORDER:
        if key not in keys:
            level = "ERROR" if key in CRITICAL_FIELDS else "WARN"
            hint = "（历史 skill 未迁移时会出现）" if key in LEGACY_OPTIONAL else ""
            problems.append(Problem(level, key, f"缺少字段 {key}{hint}"))

    if values.get("name") and values["name"] != skill_dir.name:
        problems.append(Problem(
            "ERROR", "name", f"name {values['name']!r} 与目录名 {skill_dir.name!r} 不一致",
        ))

    # 顺序：已存在的字段必须按约定顺序出现，插错位置会让下游按行解析的工具读错。
    present = [k for k in keys if k in REQUIRED_ORDER]
    expected = [k for k in REQUIRED_ORDER if k in present]
    if present != expected:
        problems.append(Problem(
            "WARN", "frontmatter", f"字段顺序为 {present}，约定为 {expected}",
        ))

    if values.get("version"):
        problems.extend(check_version(0, values["version"]))

    plugin_ver, market_ver, ver_problems = load_package_versions(skill_dir)
    problems.extend(ver_problems)
    if plugin_ver and market_ver and plugin_ver != market_ver:
        problems.append(Problem(
            "ERROR", "version",
            f"包版本不一致：plugin.json={plugin_ver} / marketplace.json={market_ver}，两处必须同步",
        ))
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="校验 SKILL.md 头部六字段与包版本一致性")
    parser.add_argument("skills", nargs="*", help="只检查指定 skill 目录名，默认全部")
    parser.add_argument("--strict", action="store_true", help="WARN 也算失败")
    args = parser.parse_args(argv[1:])

    if args.skills:
        dirs = [REPO_ROOT / name for name in args.skills]
        missing = [d for d in dirs if not (d / "SKILL.md").is_file()]
        if missing:
            print(f"找不到 skill：{', '.join(d.name for d in missing)}", file=sys.stderr)
            return 2
    else:
        dirs = sorted(
            p for p in REPO_ROOT.iterdir()
            if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").is_file()
        )

    failures = 0
    for d in dirs:
        try:
            problems = check_skill(d)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[FAIL] {d.name}: 读取失败 {exc}")
            failures += 1
            continue
        errors = [p for p in problems if p.level == "ERROR"]
        warns = [p for p in problems if p.level == "WARN"]
        status = "FAIL" if errors else ("WARN" if warns else "OK  ")
        print(f"[{status}] {d.name}")
        for p in problems:
            where = f"{p.field}：" if p.field else ""
            print(f"       {p.level:<5} {where}{p.message}")
        if errors or (args.strict and warns):
            failures += 1

    print(f"\n{len(dirs) - failures}/{len(dirs)} 通过")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
