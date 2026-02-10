#!/usr/bin/env python3
"""
PreToolUse Hook: 编辑前检查（Spiral 兼容）
"""

from __future__ import annotations

import os
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
STATUS_FILE = PROJECT_ROOT / "Governance" / "record" / "development-status.md"

# Reuse quality-check regex to avoid rule drift.
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.quality.local_quality_check import WINDOWS_ABS_RE, UNIX_ABS_RE  # noqa: E402

# S6 收口阶段才阻断简化关键词；开发中允许 TODO/FIXME。
FORBIDDEN_KEYWORDS = [
    "HACK",
    "临时绕过",
    "hardcoded",
]


def check_hardcoded_paths(content: str) -> list[str]:
    """检查硬编码路径（与 local_quality_check 保持一致）"""
    violations = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if line.startswith("#!"):
            continue
        if WINDOWS_ABS_RE.search(line) or UNIX_ABS_RE.search(line):
            violations.append(f"发现硬编码路径 (行{lineno})")
    return violations


def detect_current_spiral() -> str:
    """检测当前 Spiral（默认 S0）"""
    if STATUS_FILE.exists():
        content = STATUS_FILE.read_text(encoding="utf-8")
        match = re.search(r"\b(S\d)\b", content)
        if match:
            return match.group(1)
    return "S0"


def check_forbidden_keywords(content: str) -> list[str]:
    """检查收口阶段禁止关键词"""
    violations = []
    for keyword in FORBIDDEN_KEYWORDS:
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if keyword in line and not line.strip().startswith("#"):
                violations.append(f"发现简化方案关键词 '{keyword}' (行{i})")
    return violations


def is_python_file(path: str) -> bool:
    return path.endswith(".py")


def main():
    try:
        file_path = os.environ.get("CLAUDE_FILE_PATH", "")
        content = sys.stdin.read() if not sys.stdin.isatty() else ""

        # 只检查 Python 文件
        if not is_python_file(file_path):
            sys.exit(0)

        current_spiral = detect_current_spiral()

        violations = []
        violations.extend(check_hardcoded_paths(content))

        # 仅在收口阶段阻断简化关键词。
        if current_spiral == "S6":
            violations.extend(check_forbidden_keywords(content))

        if violations:
            print("\n" + "="*60)
            print("❌ 编辑前检查失败 - 发现零容忍违规")
            print("="*60)
            print(f"📄 文件: {file_path}")
            print(f"📍 Spiral: {current_spiral}")
            print("\n违规项:")
            for i, v in enumerate(violations, 1):
                print(f"  {i}. {v}")
            print("\n建议:")
            print("  1. 使用 Config.from_env() 获取路径")
            print("  2. 路径放入 .env/.env.example，不在代码中硬编码")
            print("  3. S6 收口阶段清理临时绕过标记")
            print("="*60 + "\n")
            sys.exit(1)

        print(f"⚠️ [{current_spiral}] 编辑前提醒: 保持数据模型/API/信息流三维一致性")
        sys.exit(0)

    except Exception as e:  # pragma: no cover
        print(f"⚠️ Pre-edit hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
