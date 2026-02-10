#!/usr/bin/env python3
"""
SessionStart Hook: 会话启动检查（Spiral 兼容）
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
STATUS_FILE = PROJECT_ROOT / "Governance" / "record" / "development-status.md"

def check_git_status() -> dict:
    """检查 Git 状态"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        branch = result.stdout.strip() if result.returncode == 0 else "unknown"

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        is_clean = not result.stdout.strip()

        return {"branch": branch, "is_clean": is_clean}
    except Exception:
        return {"branch": "unknown", "is_clean": True}

def detect_current_spiral() -> str | None:
    """检测当前 Spiral（S0-S6）"""
    if not STATUS_FILE.exists():
        return None
    content = STATUS_FILE.read_text(encoding="utf-8")
    match = re.search(r"\b(S\d)\b", content)
    return match.group(1) if match else None

def main():
    try:
        git_info = check_git_status()
        spiral = detect_current_spiral()

        print("\n" + "="*60)
        print("🚀 EmotionQuant Spiral Workflow - Session Started")
        print("="*60)
        print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"🌿 Branch: {git_info['branch']} | Clean: {'✅' if git_info['is_clean'] else '❌'}")

        if spiral is not None:
            print(f"📍 Current: {spiral}")
        else:
            print("📍 No active Spiral detected")

        print("-"*60)
        print("💡 Quick Commands:")
        print("   Scope -> Build -> Verify -> Sync")
        print("   Run local quality check: python scripts/quality/local_quality_check.py --scan")
        print("   Sync status: Governance/record/development-status.md")
        print("="*60 + "\n")

        sys.exit(0)

    except Exception as e:
        print(f"⚠️ Session start hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
