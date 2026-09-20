#!/usr/bin/env python3
"""校验 marketplace.json 中各插件的显示名解析结果。

客户端的显示名由插件市场条目的 displayName / displayName_i18n 决定，而不是
SKILL.md 的 name。本脚本复刻客户端的解析顺序（语言键精确匹配 → 语言前缀匹配
→ displayName → 插件名自动标题化），先用官方市场观察到的事实校准解析逻辑，
再逐个检查本仓库的插件条目。

用法：python3 scripts/check-display-names.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

# 每个插件名在标题化时保留的固定写法，与客户端保持一致。
SPECIAL_CASE_WORDS = {"aws": "AWS", "mcp": "MCP", "zcode": "ZCode"}


def resolve_localized_text(locale: str, default: str | None, table: dict[str, str] | None) -> str | None:
    """按语言键精确匹配，再按语言前缀匹配，最后回退 default。"""
    if table:
        if table.get(locale):
            return table[locale]
        prefix = locale.split("-")[0]
        if prefix:
            for key, value in table.items():
                if key.split("-")[0] == prefix and value:
                    return value
    return default


def format_canonical_plugin_name(name: str, locale: str) -> str:
    """把插件名转换成标题化显示名，例如 write-openapi-json → Write Openapi Json。"""
    words = [w for w in re.split(r"[-_]+", name.strip()) if w]
    return " ".join(SPECIAL_CASE_WORDS.get(w.lower()) or w[:1].upper() + w[1:] for w in words)


def resolve_plugin_display_name(plugin: dict, locale: str) -> str:
    resolved = resolve_localized_text(
        locale,
        plugin.get("displayName"),
        plugin.get("displayName_i18n"),
    )
    return resolved or format_canonical_plugin_name(plugin["name"], locale)


# 官方市场中可直接观察到的样例，用于校准解析逻辑。前缀 `official:` 与 `bare:` 区分两类。
CALIBRATION = [
    {
        "case": "official:skill-creator",
        "plugin": {
            "name": "skill-creator",
            "displayName": "Skill Creator",
            "displayName_i18n": {"zh-CN": "技能创建器"},
        },
        "expected": {"zh-CN": "技能创建器", "en-US": "Skill Creator"},
    },
    {
        "case": "official:lark-cli",
        "plugin": {
            "name": "lark-cli",
            "displayName": "Lark CLI",
            "displayName_i18n": {"en": "Lark CLI", "zh-CN": "飞书 CLI"},
        },
        # zh-CN 精确命中；en-US 前缀命中 en。
        "expected": {"zh-CN": "飞书 CLI", "en-US": "Lark CLI"},
    },
    {
        "case": "official:computer-use",
        "plugin": {
            "name": "computer-use",
            "displayName": "Computer Use",
            "displayName_i18n": {"zh-CN": "电脑控制"},
        },
        "expected": {"zh-CN": "电脑控制", "en-US": "Computer Use"},
    },
    {
        "case": "official:no-displayName",
        "plugin": {"name": "frontend-design"},
        "expected": {"zh-CN": "Frontend Design", "en-US": "Frontend Design"},
    },
    {
        "case": "official:only-en-i18n",
        "plugin": {"name": "gitlab", "displayName_i18n": {"en": "GitLab"}},
        # zh-CN 无命中，回退到 displayName（缺失），再回退到标题化名称。
        "expected": {"zh-CN": "Gitlab", "en-US": "GitLab"},
    },
    {
        "case": "official:legacy-bare-name",
        "plugin": {"name": "write-openapi-json"},
        "expected": {"zh-CN": "Write Openapi Json", "en-US": "Write Openapi Json"},
    },
]


def check_failures(plugin: dict, label: str) -> list[str]:
    failures: list[str] = []
    name = plugin.get("name", "")
    if not PLUGIN_NAME_RE.match(name):
        failures.append(f"{label}: 插件名不符合客户端校验规则 ^[a-z0-9][a-z0-9._-]{{0,127}}$，实际 {name!r}")

    source = plugin.get("source")
    if not isinstance(source, str) or not source.startswith("./"):
        failures.append(f"{label}: source 应为相对仓库根目录的路径，实际 {source!r}")
        return failures

    manifest_path = REPO_ROOT / source.lstrip("./") / ".zcode-plugin" / "plugin.json"
    if not manifest_path.is_file():
        failures.append(f"{label}: 缺少插件清单 {manifest_path.relative_to(REPO_ROOT)}")
        return failures

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # 客户端安装时校验清单名与市场条目名一致，不一致会直接报错。
    if manifest.get("name") != name:
        failures.append(
            f"{label}: 清单名 {manifest.get('name')!r} 与市场条目名 {name!r} 不一致"
        )

    skill_path = manifest_path.parent.parent / "SKILL.md"
    if not skill_path.is_file():
        failures.append(f"{label}: 缺少 {skill_path.relative_to(REPO_ROOT)}")
    else:
        text = skill_path.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)
        if not match:
            failures.append(f"{label}: SKILL.md frontmatter 缺少 name")
        elif match.group(1) != name:
            failures.append(f"{label}: SKILL.md 的 name {match.group(1)!r} 与插件名 {name!r} 不一致")

    return failures


def main() -> int:
    failures: list[str] = []

    print("== 解析逻辑校准（官方市场事实）==")
    for entry in CALIBRATION:
        for locale, expected in entry["expected"].items():
            actual = resolve_plugin_display_name(entry["plugin"], locale)
            status = "ok  " if actual == expected else "FAIL"
            if actual != expected:
                failures.append(f"校准 {entry['case']} [{locale}]: 期望 {expected!r}，实际 {actual!r}")
            print(f"  {status} {entry['case']:<28} {locale:<6} → {actual}")

    data = json.loads((REPO_ROOT / "marketplace.json").read_text(encoding="utf-8"))
    plugins = data.get("plugins", [])
    print(f"\n== 本仓库插件显示名（市场 {data.get('name')!r}，共 {len(plugins)} 个）==")

    seen: set[str] = set()
    for plugin in plugins:
        name = plugin.get("name", "<unnamed>")
        if name in seen:
            failures.append(f"{name}: 市场条目重复")
        seen.add(name)

        label = name
        failures.extend(check_failures(plugin, label))

        for locale in ("zh-CN", "en-US"):
            print(f"  {label:<20} {locale:<6} → {resolve_plugin_display_name(plugin, locale)}")

        cases = plugin.get("displayName_i18n") or {}
        if not cases:
            failures.append(f"{label}: 未配置 displayName_i18n，界面会退回标题化的 {format_canonical_plugin_name(name, 'en-US')}")
            continue
        zh = resolve_plugin_display_name(plugin, "zh-CN")
        if not re.search(r"[\u4e00-\u9fff]", zh):
            failures.append(f"{label}: 中文显示名不含汉字，实际 {zh!r}")
        if not plugin.get("displayName"):
            failures.append(f"{label}: 配置了 displayName_i18n 但缺少 displayName，非中文语言将退回标题化名称")

    print()
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        print(f"\n共 {len(failures)} 项不符合预期")
        return 1

    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
