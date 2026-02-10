#!/usr/bin/env python3
"""
Claude Code Hook 编排器
同时执行多个 preToolUse Hook 检查

用途：允许对同一事件（如 Edit）执行多个 Hook 脚本
作者：Claude Code
创建时间：2025-12-17
"""

import os
import sys
import subprocess
from pathlib import Path

# Hook 脚本列表（按顺序执行）
HOOKS = [
    ".claude/hooks/pre_edit_check.py",      # 零容忍检查（硬编码路径、技术指标）
    ".claude/hooks/pre_doc_edit_check.py",  # 文档一致性提醒
]

def main():
    """主函数"""
    file_path = os.environ.get("CLAUDE_FILE_PATH", "")

    for hook in HOOKS:
        hook_path = Path(hook)
        if not hook_path.exists():
            continue

        # 执行 Hook
        try:
            result = subprocess.run(
                ["python", str(hook_path)],
                env=os.environ.copy(),
                capture_output=True,
                text=True
            )

            # 输出 Hook 的标准输出
            if result.stdout:
                print(result.stdout, end="")

            # 如果 Hook 返回非零退出码，阻塞操作
            if result.returncode != 0:
                if result.stderr:
                    print(result.stderr, file=sys.stderr, end="")
                sys.exit(result.returncode)

        except Exception as e:
            print(f"⚠️  Hook 执行失败: {hook} - {e}", file=sys.stderr)
            # 继续执行下一个 Hook（不阻塞）
            continue

    # 所有 Hook 通过
    sys.exit(0)

if __name__ == "__main__":
    main()
