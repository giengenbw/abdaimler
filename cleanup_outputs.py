#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理当前目录中的输出文件，只保留代码和项目说明文件。

默认仅预览：
    python cleanup_outputs.py

确认删除：
    python cleanup_outputs.py --yes

指定其他目录：
    python cleanup_outputs.py C:\abman --yes

默认保留：
- 所有 .py、.pyw、.md 文件
- .gitignore、.gitattributes、.gitmodules
- requirements.txt、pyproject.toml、poetry.lock、Pipfile、Pipfile.lock
- 本脚本自身

默认不删除任何目录。
"""
from __future__ import annotations

import argparse
from pathlib import Path

KEEP_SUFFIXES = {".py", ".pyw", ".md"}
KEEP_NAMES = {
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
}


def should_keep(path: Path, script_path: Path) -> bool:
    """判断普通文件是否应保留。"""
    try:
        if path.resolve() == script_path.resolve():
            return True
    except OSError:
        pass

    return path.name in KEEP_NAMES or path.suffix.lower() in KEEP_SUFFIXES


def format_size(size: int) -> str:
    """以易读格式显示文件大小。"""
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="删除目标目录中除 Python、Markdown 和 Git 配置等以外的普通文件"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="待清理目录，默认是当前目录",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="实际执行删除；不加此参数时仅预览",
    )
    args = parser.parse_args()

    target = args.directory.expanduser().resolve()
    script_path = Path(__file__).resolve()

    if not target.is_dir():
        parser.error(f"目录不存在: {target}")

    # 只处理目标目录第一层的普通文件，不递归，不删除目录。
    candidates = sorted(
        (
            item
            for item in target.iterdir()
            if item.is_file() and not should_keep(item, script_path)
        ),
        key=lambda item: item.name.casefold(),
    )

    print(f"目标目录: {target}")
    print("模式: " + ("实际删除" if args.yes else "仅预览，不会删除"))
    print()

    if not candidates:
        print("没有需要删除的文件。")
        return 0

    total_size = 0
    for item in candidates:
        try:
            size = item.stat().st_size
        except OSError:
            size = 0
        total_size += size
        print(f"[待删除] {item.name} ({format_size(size)})")

    print()
    print(f"共 {len(candidates)} 个文件，合计 {format_size(total_size)}。")

    if not args.yes:
        print("当前为预览模式。确认列表无误后运行：")
        print(f'python "{script_path.name}" --yes')
        return 0

    deleted = 0
    failed = 0
    for item in candidates:
        try:
            item.unlink()
            deleted += 1
            print(f"[已删除] {item.name}")
        except OSError as exc:
            failed += 1
            print(f"[失败] {item.name}: {exc}")

    print()
    print(f"清理完成：成功删除 {deleted} 个，失败 {failed} 个。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
