#!/usr/bin/env python3
"""
PostToolUse Hook: 编辑后检查
在文件编辑完成后根据编辑次数触发检查提醒
适配版本：Claude Code
"""
import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
SESSION_FILE = Path.home() / ".claude" / "edit_session.json"

# 触发阈值
PERIODIC_CHECK_INTERVAL = 5   # 每 5 次编辑提醒状态
A6_CHECK_THRESHOLD = 15       # 达到 15 次编辑建议 A6 检查

def get_session() -> dict:
    """读取编辑会话状态"""
    try:
        if SESSION_FILE.exists():
            return json.loads(SESSION_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {
        "count": 0,
        "a6_suggested": False,
        "files_edited": [],
        "session_start": datetime.now().isoformat()
    }

def save_session(session: dict):
    """保存编辑会话状态"""
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

def main():
    try:
        import os
        file_path = os.environ.get('CLAUDE_FILE_PATH', '')

        # 只跟踪代码文件
        if not file_path.endswith(('.py', '.md')):
            sys.exit(0)

        session = get_session()
        session["count"] += 1

        # 记录编辑的文件（去重）
        if file_path and file_path not in session["files_edited"]:
            session["files_edited"].append(file_path)

        # 定期提醒
        if session["count"] % PERIODIC_CHECK_INTERVAL == 0:
            print(f"\n💡 已编辑 {session['count']} 个文件 - 建议运行 /6a-status 检查进度\n")

        # A6 检查建议
        if session["count"] >= A6_CHECK_THRESHOLD and not session["a6_suggested"]:
            print("\n" + "="*60)
            print("⚠️ 检测到大量代码修改")
            print("="*60)
            print(f"📊 统计: {session['count']} 次编辑，涉及 {len(session['files_edited'])} 个文件")
            print("\n建议:")
            print("  1. 运行 /a6-check [phase] 进行完整检查")
            print("  2. 运行全量测试: pytest tests/ -v")
            print("  3. 检查三维文档是否同步更新")
            print("="*60 + "\n")
            session["a6_suggested"] = True

        save_session(session)
        sys.exit(0)

    except Exception as e:
        sys.exit(0)

if __name__ == "__main__":
    main()
