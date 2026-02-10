#!/usr/bin/env python3
"""
UserPromptSubmit Hook: 用户消息提交时的关键词检测
检测用户消息中的关键词，自动提醒运行相应的 slash commands
适配版本：Claude Code
"""
import sys
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
STATUS_FILE = PROJECT_ROOT / "Governance" / "record" / "development-status.md"

# 关键词 → 命令映射
KEYWORD_COMMAND_MAP = {
    # A4 检查相关
    "a4": "/a4-check",
    "A4": "/a4-check",
    "a4检查": "/a4-check",
    "A4检查": "/a4-check",
    "gate检查": "/a4-check",
    "Gate检查": "/a4-check",
    "进入实现": "/a4-check",
    "开始实现": "/a4-check",
    "准备实现": "/a4-check",

    # A6 检查相关
    "a6": "/a6-check",
    "A6": "/a6-check",
    "a6检查": "/a6-check",
    "A6检查": "/a6-check",
    "收口": "/a6-check",
    "task完成": "/a6-check",
    "Task完成": "/a6-check",
    "任务完成": "/a6-check",
    "完成检查": "/a6-check",

    # TDD 相关
    "tdd": "/tdd",
    "TDD": "/tdd",
    "tdd提醒": "/tdd",
    "TDD提醒": "/tdd",
    "测试驱动": "/tdd",
    "红绿重构": "/tdd",

    # 6A 状态相关
    "6a": "/6a-status",
    "6A": "/6a-status",
    "6a状态": "/6a-status",
    "6A状态": "/6a-status",
    "工作流状态": "/6a-status",
    "工作流进度": "/6a-status",
    "当前进度": "/6a-status",

    # Phase 启动相关
    "phase启动": "/phase-start",
    "Phase启动": "/phase-start",
    "新会话": "/phase-start",
    "会话启动": "/phase-start",
    "加载上下文": "/phase-start",
}

def detect_current_phase() -> str:
    """检测当前 Spiral（兼容旧函数名）"""
    if STATUS_FILE.exists():
        content = STATUS_FILE.read_text(encoding="utf-8")
        match = re.search(r"\b(S\d)\b", content)
        if match:
            return match.group(1)
    return "S0"

def detect_keywords(message: str) -> list[tuple[str, str]]:
    """检测消息中的关键词，返回 [(关键词, 命令)]"""
    detected = []
    for keyword, command in KEYWORD_COMMAND_MAP.items():
        if keyword in message:
            detected.append((keyword, command))
    return detected

def main():
    try:
        # 读取用户消息（从 stdin 或环境变量）
        import os
        user_message = os.environ.get('CLAUDE_USER_MESSAGE', '')

        if not user_message:
            # 尝试从 stdin 读取
            try:
                input_data = json.load(sys.stdin)
                user_message = input_data.get('message', '')
            except Exception:
                pass

        if not user_message:
            sys.exit(0)

        # 检测关键词
        detected = detect_keywords(user_message)

        if detected:
            # 去重（同一命令只提醒一次）
            commands = list(dict.fromkeys([cmd for _, cmd in detected]))

            # 获取当前 Phase（用于 a4-check/a6-check）
            current_phase = detect_current_phase()

            print("\n" + "="*60)
            print("💡 关键词检测 - 自动命令提醒")
            print("="*60)

            for cmd in commands:
                if cmd in ["/a4-check", "/a6-check"]:
                    print(f"🎯 检测到关键词，建议运行: {cmd} {current_phase}")
                else:
                    print(f"🎯 检测到关键词，建议运行: {cmd}")

            print("="*60 + "\n")

        sys.exit(0)

    except Exception as e:
        # 静默失败，不影响正常工作流
        sys.exit(0)

if __name__ == "__main__":
    main()
