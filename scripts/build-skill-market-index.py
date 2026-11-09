#!/usr/bin/env python3
"""生成 DSH 技能市场索引 index.json（Skill Market Index Format 1）。

规范：
    https://github.com/xiechenghua01/dsh-plugins/blob/main/docs/plugins/skill-manager/product/skill-market-index-spec.md

用法：
    python3 scripts/build-skill-market-index.py             # 生成/更新 index.json
    python3 scripts/build-skill-market-index.py --check     # 只校验，不写文件
    python3 scripts/build-skill-market-index.py --latest    # 每个技能只保留最新版本

本仓库的既有发布链路（ZCode 插件市场）不变：根 marketplace.json 与各技能目录下的
.zcode-plugin/plugin.json 继续供 ZCode 使用。本脚本只额外生成 DSH 侧的市场索引，
两者互不影响。

规则：
- marketplace.json 的每个插件 = 索引里的一个技能；包版本取插件条目的 x.y.z。
- 索引里的展示名/描述复用 SKILL.md frontmatter 与 marketplace.json，不另写一套短描述。
- 文件 URL 固定到当前 HEAD（40 位 commit），附带 sha256 与 size；隐藏目录
  （.zcode-plugin/ 等）和 node_modules 不进入索引，因此不影响 ZCode 安装。
- 图标从 jsDelivr @main 地址改写为同一 commit 的 raw URL，避免缓存漂移。
- 已发布 name@version 的内容一旦变化即拒绝生成（版本不可变），要求先升版本。
- 生成要求工作区干净（索引必须固定已提交的内容），但允许 index.json 自身处于修改状态。
- --check 回查索引里每个文件 URL 指向的 commit/path 是否存在且 sha256/size 与索引一致。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / "marketplace.json"
INDEX = REPO_ROOT / "index.json"
SCHEMA_URL = (
    "https://raw.githubusercontent.com/xiechenghua01/dsh-plugins/main/"
    "docs/plugins/skill-manager/product/skill-market-index.schema.json"
)

# 不写 engines.dsh：规范 §7.1 规定「无 engines 视为兼容」。DSH 桌面版当前是预发布版
# （0.2.2-rc.1），而 SemVer §11 规定预发布版本只有在某比较器命中同一 major.minor.patch
# 且带预发布标签时才满足 range；因此任何带正式上界的 range（如 >=0.2.1-rc.5 <0.3.0）
# 都会把 0.2.2-rc.1 判为不兼容。技能只是 Markdown 指令、不依赖特定 DSH 版本，
# 省略 engines 比写一个会误伤预发布宿主的 range 更安全。
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_SKILL_MD_BYTES = 256 * 1024
MAX_FILES_PER_VERSION = 200
MAX_VERSION_BYTES = 20 * 1024 * 1024
MAX_PATH_LENGTH = 200

RESERVED_SEGMENTS = {".disabled", ".skill-manager", ".git", "node_modules"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_40 = re.compile(r"^[0-9a-f]{40}$")
PATH_SEGMENT = re.compile(r"^[A-Za-z0-9_@+-][A-Za-z0-9._@+-]*$")
FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
GITHUB_REMOTE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?/?$"
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def git(*args: str, text: bool = True):
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=text,
    )
    if result.returncode != 0:
        stderr = (
            result.stderr.decode("utf-8", "replace")
            if isinstance(result.stderr, bytes)
            else result.stderr
        )
        fail(f"git {' '.join(args)} 失败：{stderr.strip()}")
    return result.stdout


def detect_repository() -> tuple[str, str]:
    """从 origin 远端推导 GitHub owner/repo，避免硬编码。"""
    url = git("remote", "get-url", "origin").strip()
    match = GITHUB_REMOTE.match(url)
    if match is None:
        fail(f"无法从 origin 推导 GitHub 仓库地址：{url!r}")
    return match.group(1), match.group(2)


def read_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if match is None:
        fail(f"{skill_md.relative_to(REPO_ROOT)}：缺少 YAML frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line_match = FRONTMATTER_LINE.match(line)
        if line_match is None:
            continue
        key, raw = line_match.group(1), line_match.group(2).strip()
        if len(raw) >= 2 and raw[0] == raw[-1] == '"':
            raw = raw[1:-1]
        fields[key] = raw
    return fields


def path_problem(relative: str) -> str | None:
    """按安装器路径规则（规范 §8.1）返回问题描述；合法时返回 None。"""
    if not relative or len(relative) > MAX_PATH_LENGTH:
        return f"文件路径为空或超过 {MAX_PATH_LENGTH} 字符：{relative!r}"
    if relative.startswith("/") or relative.endswith("/"):
        return f"文件路径不能以 / 开头或结尾：{relative!r}"
    if any(char in relative for char in "\\:?#%"):
        return f"文件路径含非法字符：{relative!r}"
    for segment in relative.split("/"):
        if not PATH_SEGMENT.fullmatch(segment):
            return (
                "文件路径段不合法（只允许 A-Za-z0-9._@+-，且不能以 . 开头）："
                f"{relative!r}"
            )
        if segment.lower() in RESERVED_SEGMENTS or segment in {"", "."}:
            return f"文件路径含保留段：{relative!r}"
    return None


def assert_path(relative: str, owner_name: str) -> None:
    problem = path_problem(relative)
    if problem is not None:
        fail(f"{owner_name}：{problem}")


def skill_files(skill_dir: Path, source: str, commit: str, repo: tuple[str, str]) -> list[dict]:
    owner, repo_name = repo
    files: list[dict] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir).as_posix()
        parts = relative.split("/")
        if any(part.startswith(".") for part in parts) or "node_modules" in parts:
            continue
        assert_path(relative, skill_dir.name)
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            fail(f"{skill_dir.name}/{relative}：超过单文件 4 MiB 上限（{len(data)} 字节）")
        if relative == "SKILL.md" and len(data) > MAX_SKILL_MD_BYTES:
            fail(f"{skill_dir.name}/SKILL.md：超过 256 KiB 上限（{len(data)} 字节）")
        files.append(
            {
                "path": relative,
                "url": raw_url(repo, commit, f"{source}/{relative}"),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    if not any(item["path"] == "SKILL.md" for item in files):
        fail(f"{skill_dir.name}：缺少根级 SKILL.md")
    if len(files) > MAX_FILES_PER_VERSION:
        fail(f"{skill_dir.name}：文件数 {len(files)} 超过 {MAX_FILES_PER_VERSION} 上限")
    total = sum(item["size"] for item in files)
    if total > MAX_VERSION_BYTES:
        fail(f"{skill_dir.name}：单版本总大小 {total} 超过 20 MiB 上限")
    return files


def raw_url(repo: tuple[str, str], commit: str, relative: str) -> str:
    owner, name = repo
    return f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{relative}"


def icon_repo_path(value: str | None, repo: tuple[str, str]) -> str | None:
    """把市场图标地址（jsDelivr @ref 或 raw 分支地址）解析成仓库内相对路径。"""
    if not value or value.startswith("data:"):
        return None
    owner, name = repo
    match = re.match(r"^https://cdn\.jsdelivr\.net/gh/[^/]+/[^@/]+@[^/]+/(.+)$", value)
    if match is not None:
        return match.group(1)
    match = re.match(
        rf"^https://raw\.githubusercontent\.com/{re.escape(owner)}/{re.escape(name)}/[^/]+/(.+)$",
        value,
    )
    if match is not None:
        return match.group(1)
    return None


def version_key(version: str) -> tuple:
    head, _, _rest = version.partition("-")
    return tuple(int(part) for part in head.split("."))


def plugin_source(plugin: dict) -> str:
    source = str(plugin.get("source") or f"./{plugin.get('name', '')}").strip()
    if source.startswith("./"):
        source = source[2:]
    if not source or source.startswith("/") or ".." in source.split("/"):
        fail(f"{plugin.get('name')}：source 路径不合法：{source!r}")
    return source


def localized_title(plugin: dict) -> dict:
    i18n = plugin.get("displayName_i18n") or {}
    english = plugin.get("displayName") or plugin.get("name", "")
    chinese = i18n.get("zh") or i18n.get("zh-CN") or i18n.get("zh-cn") or english
    return {"en": english, "zh": chinese}


def build_document(repo: tuple[str, str], commit: str, latest_only: bool) -> dict:
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    old_doc = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.is_file() else {"skills": []}
    old_by_name = {skill.get("name"): skill for skill in old_doc.get("skills", [])}

    skills: list[dict] = []
    seen_names: set[str] = set()
    for plugin in market.get("plugins", []):
        name = plugin.get("name", "")
        version = plugin.get("version", "")
        if not SKILL_NAME.fullmatch(name):
            fail(f"插件名不是 kebab-case：{name!r}")
        if name in seen_names:
            fail(f"插件名重复：{name}")
        seen_names.add(name)
        if not SEMVER.fullmatch(version):
            fail(f"{name}：版本 {version!r} 不是精确 SemVer")

        source = plugin_source(plugin)
        skill_dir = REPO_ROOT / source
        if not skill_dir.is_dir():
            fail(f"{name}：技能目录不存在：{source}")

        frontmatter = read_frontmatter(skill_dir / "SKILL.md")
        if frontmatter.get("name") != name:
            fail(f"{name}：SKILL.md 的 name={frontmatter.get('name')!r} 与目录不一致")

        previous = old_by_name.get(name, {})
        previous_versions = {item["version"]: item for item in previous.get("versions", [])}
        previous_version = previous_versions.get(version)
        if previous_version is not None:
            files = previous_version["files"]
            old_sha = {item["path"]: item["sha256"] for item in files}
            new_sha = {
                item["path"]: item["sha256"]
                for item in skill_files(skill_dir, source, commit, repo)
            }
            if old_sha != new_sha:
                fail(f"{name}@{version}：内容已变化但版本未升，请先升版本")
            pin_commit = previous_version["source"]["commit"]
        else:
            files = skill_files(skill_dir, source, commit, repo)
            timestamp = int(
                git("log", "-1", "--format=%ct", "--", source).strip()
                or git("log", "-1", "--format=%ct").strip()
            )
            pin_commit = commit
            previous_versions[version] = {
                "version": version,
                "publishTimestamp": timestamp,
                                "source": {
                    "type": "git",
                    "url": f"https://github.com/{repo[0]}/{repo[1]}",
                    "commit": commit,
                    "path": source,
                },
                "files": files,
            }

        # 版本条目对已发布版本保持冻结，但统一剥掉历史遗留的 engines（见文件头注释）。
        versions = [
            {key: value for key, value in item.items() if key != "engines"}
            for item in previous_versions.values()
        ]
        versions.sort(key=lambda item: version_key(item["version"]), reverse=True)
        if latest_only:
            versions = versions[:1]

        description_zh = frontmatter.get("description") or plugin.get("description", "")
        description_en = frontmatter.get("description_en") or description_zh
        if description_zh == "" or description_en == "":
            fail(f"{name}：描述为空，无法生成市场描述")

        entry = {
            "name": name,
            "title": localized_title(plugin),
            "description": {"en": description_en, "zh": description_zh},
            "author": repo[0],
            "homepage": f"https://github.com/{repo[0]}/{repo[1]}/tree/main/{source}",
            "repository": f"https://github.com/{repo[0]}/{repo[1]}",
            "versions": versions,
        }
        icon = plugin.get("icon")
        icon_path = icon_repo_path(icon, repo)
        if icon_path is not None:
            try:
                git("cat-file", "-e", f"{pin_commit}:{icon_path}")
            except SystemExit:
                fail(
                    f"{name}：图标 {icon_path} 不在 commit {pin_commit[:12]} 中，"
                    "请先提交图标再生成索引"
                )
            entry["icon"] = raw_url(repo, pin_commit, icon_path)
        elif icon:
            entry["icon"] = icon
        skills.append(entry)

    return {
        "$schema": SCHEMA_URL,
        "format": 1,
        "title": {"en": "Chengze Skills", "zh": "工程技能"},
        "description": {
            "en": "These skills ship in two markets: ZCode plugins and the DeepSeek Harness skill market.",
            "zh": "本仓库以 ZCode 插件市场与 DSH 技能市场两种形式发布同一批技能。",
        },
        "homepage": f"https://github.com/{repo[0]}/{repo[1]}",
        "repository": f"https://github.com/{repo[0]}/{repo[1]}",
        "author": repo[0],
        "skills": skills,
    }


def check_document(repo: tuple[str, str], stale_ok: bool = False) -> None:
    if not INDEX.is_file():
        fail("index.json 不存在，请先运行 python3 scripts/build-skill-market-index.py")
    document = json.loads(INDEX.read_text(encoding="utf-8"))
    if document.get("format") != 1:
        fail("index.json: format 必须是 1")

    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugins = {plugin.get("name"): plugin for plugin in market.get("plugins", [])}
    listed = {skill.get("name"): skill for skill in document.get("skills", [])}
    if set(plugins) != set(listed):
        missing = sorted(set(plugins) - set(listed))
        extra = sorted(set(listed) - set(plugins))
        fail(f"index.json 技能列表与 marketplace.json 不一致：缺少 {missing}，多出 {extra}")

    problems: list[str] = []
    for name, skill in listed.items():
        plugin = plugins[name]
        if not SKILL_NAME.fullmatch(name):
            problems.append(f"{name}: 不是 kebab-case")
            continue
        source = plugin_source(plugin)
        skill_dir = REPO_ROOT / source
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{name}: 缺少 {source}/SKILL.md")
            continue
        frontmatter = read_frontmatter(skill_md)
        if frontmatter.get("name") != name:
            problems.append(f"{name}: SKILL.md 的 name 与目录不一致")

        # 索引展示信息必须与当前 SKILL.md / marketplace.json 一致，否则说明索引过期。
        # --stale-ok 供 CI 使用：只校验索引自身与固定内容，不要求它已跟上最新技能改动。
        if not stale_ok:
            expected_title = localized_title(plugin)
            if skill.get("title") != expected_title:
                problems.append(f"{name}: title 与 marketplace.json 不一致，索引已过期")
            expected_description = {
                "en": frontmatter.get("description_en") or frontmatter.get("description", ""),
                "zh": frontmatter.get("description") or "",
            }
            if skill.get("description") != expected_description:
                problems.append(f"{name}: description 与 SKILL.md 不一致，索引已过期")

        versions = skill.get("versions") or []
        if not versions:
            problems.append(f"{name}: versions 为空")
            continue
        seen_versions: set[str] = set()
        for version in versions:
            version_text = version.get("version", "")
            if not SEMVER.fullmatch(version_text):
                problems.append(f"{name}: 版本 {version_text!r} 不是精确 SemVer")
            if version_text in seen_versions:
                problems.append(f"{name}: 版本 {version_text} 重复")
            seen_versions.add(version_text)
            files = version.get("files") or []
            if not files:
                problems.append(f"{name}@{version_text}: files 为空")
            if not any(item.get("path") == "SKILL.md" for item in files):
                problems.append(f"{name}@{version_text}: 缺少根级 SKILL.md")
            if sum(1 for item in files if item.get("path") == "SKILL.md") > 1:
                problems.append(f"{name}@{version_text}: SKILL.md 出现多次")
            if len(files) > MAX_FILES_PER_VERSION:
                problems.append(f"{name}@{version_text}: 文件数超过 {MAX_FILES_PER_VERSION}")
            total = 0
            for item in files:
                path = item.get("path", "")
                problem = path_problem(path)
                if problem is not None:
                    problems.append(f"{name}@{version_text}: {problem}")
                url = item.get("url", "")
                match = re.match(
                    rf"^https://raw\.githubusercontent\.com/"
                    rf"{re.escape(repo[0])}/{re.escape(repo[1])}/([0-9a-f]{{40}})/(.+)$",
                    url,
                )
                if match is None:
                    problems.append(
                        f"{name}@{version_text}: 文件 URL 未固定到 {repo[0]}/{repo[1]} 的 40 位 commit：{url}"
                    )
                    continue
                pin_commit, target = match.group(1), match.group(2)
                if target != f"{source}/{path}":
                    problems.append(
                        f"{name}@{version_text}: URL 路径 {target} 与 path {path} 不一致"
                    )
                    continue
                size = item.get("size")
                if not isinstance(size, int) or size < 1 or size > MAX_FILE_BYTES:
                    problems.append(f"{name}@{version_text}: {path} 的 size 不合法")
                total += size if isinstance(size, int) else 0
                try:
                    blob = git("cat-file", "-p", f"{pin_commit}:{target}", text=False)
                except SystemExit:
                    problems.append(
                        f"{name}@{version_text}: 本地缺少 commit {pin_commit[:12]} 的 {target}（CI 需 fetch-depth: 0）"
                    )
                    continue
                if (
                    hashlib.sha256(blob).hexdigest() != item.get("sha256")
                    or len(blob) != item.get("size")
                ):
                    problems.append(
                        f"{name}@{version_text}: {path} 的 sha256/size 与 commit {pin_commit[:12]} 内容不符"
                    )
            if total > MAX_VERSION_BYTES:
                problems.append(f"{name}@{version_text}: 单版本总大小超过 20 MiB")
        if not stale_ok and plugin.get("version") not in seen_versions:
            problems.append(
                f"{name}: marketplace.json 的版本 {plugin.get('version')} 不在索引 versions 中，索引已过期"
            )

    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"index.json 校验通过：{len(listed)} 个技能，"
        f"{sum(len(skill.get('versions', [])) for skill in listed.values())} 个版本，"
        "文件内容与固定 commit 一致"
    )


def ensure_index_inputs_clean() -> None:
    """索引只能固定已提交的内容，所以 marketplace.json 与各技能目录必须干净。

    根文档（README/AGENTS.md）与 scripts/ 未提交不影响索引，允许先生成索引再一起提交。
    """
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    watched = ["marketplace.json"]
    for plugin in market.get("plugins", []):
        watched.append(plugin_source(plugin))
    dirty = git("status", "--porcelain", "--", *watched).splitlines()
    if dirty:
        preview = "；".join(line.strip() for line in dirty[:5])
        fail(f"索引输入有未提交改动，先提交再生成（索引必须固定已提交的内容）：{preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 DSH 技能市场索引 index.json")
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    parser.add_argument("--latest", action="store_true", help="每个技能只保留最新版本")
    parser.add_argument(
        "--stale-ok",
        action="store_true",
        help="配合 --check：不要求索引已跟上 marketplace.json 的最新版本（CI 用）",
    )
    args = parser.parse_args()

    repo = detect_repository()

    if args.check:
        check_document(repo, stale_ok=args.stale_ok)
        return

    ensure_index_inputs_clean()

    commit = git("rev-parse", "HEAD").strip()
    if not COMMIT_40.fullmatch(commit):
        fail("无法取得 HEAD commit")
    remote = git("branch", "-r", "--contains", commit).strip()
    if not remote:
        warn("HEAD 尚未推送到任何远端分支，生成的 raw URL 在推送前不可访问")

    document = build_document(repo, commit, args.latest)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if INDEX.is_file() and INDEX.read_text(encoding="utf-8") == text:
        print(f"index.json 无变化（commit {commit[:12]}）")
        return
    INDEX.write_text(text, encoding="utf-8")
    print(
        f"wrote index.json：{len(document['skills'])} 个技能，commit {commit[:12]}，"
        f"{INDEX.stat().st_size} 字节"
    )


if __name__ == "__main__":
    main()