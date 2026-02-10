#!/usr/bin/env python3
"""
测试所有 Claude Code Hooks 功能
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

def run_test(name: str, command: list, expected_exit_code: int = 0) -> bool:
    """运行测试"""
    print(f"\n{'='*60}")
    print(f"🧪 测试: {name}")
    print(f"{'='*60}")

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(f"stderr: {result.stderr}")

    success = result.returncode == expected_exit_code
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} (Exit Code: {result.returncode}, Expected: {expected_exit_code})")

    return success

def main():
    print("="*60)
    print("🚀 Claude Code Hooks 完整测试")
    print("="*60)

    tests = [
        # 1. Session Start Hook
        ("Session Start Hook", ["python", ".claude/hooks/session_start.py"]),

        # 2. User Prompt Submit - A4 关键词
        ("关键词检测: A4检查",
         ["python", ".claude/hooks/user_prompt_submit.py"],
         {"CLAUDE_USER_MESSAGE": "我准备开始实现了"}),

        # 3. User Prompt Submit - A6 关键词
        ("关键词检测: A6检查",
         ["python", ".claude/hooks/user_prompt_submit.py"],
         {"CLAUDE_USER_MESSAGE": "任务完成了，需要收口检查"}),

        # 4. User Prompt Submit - 6A 状态
        ("关键词检测: 6A状态",
         ["python", ".claude/hooks/user_prompt_submit.py"],
         {"CLAUDE_USER_MESSAGE": "查看一下当前6A状态"}),

        # 5. Pre-Edit Hook - 正常代码
        ("Pre-Edit: 正常代码 (应该通过)",
         ["bash", "-c", "echo 'def test(): pass' | CLAUDE_FILE_PATH=test.py python .claude/hooks/pre_edit_check.py"]),

        # 6. Pre-Edit Hook - 硬编码路径 (应该失败)
        ("Pre-Edit: 硬编码路径 (应该失败)",
         ["bash", "-c", 'echo \'path = "C:\\\\Users\\\\test"\' | CLAUDE_FILE_PATH=test.py python .claude/hooks/pre_edit_check.py'],
         1),  # 期望 exit code 1

        # 7. Pre-Edit Hook - 技术指标 (应该失败)
        ("Pre-Edit: 技术指标 (应该失败)",
         ["bash", "-c", "echo 'ma = calculate_MA(data)' | CLAUDE_FILE_PATH=test.py python .claude/hooks/pre_edit_check.py"],
         1),

        # 8. Post-Edit Hook
        ("Post-Edit: 编辑跟踪",
         ["python", ".claude/hooks/post_edit_check.py"],
         {"CLAUDE_FILE_PATH": "test.py"}),
    ]

    results = []

    for test in tests:
        if len(test) == 2:
            name, cmd = test
            env = None
            expected_code = 0
        elif len(test) == 3 and isinstance(test[2], dict):
            name, cmd, env = test
            expected_code = 0
        else:
            name, cmd, expected_code = test
            env = None

        # 设置环境变量
        import os
        test_env = os.environ.copy()
        if env:
            test_env.update(env)

        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=test_env,
            shell=True if "bash" in cmd else False
        )

        print(f"\n{'='*60}")
        print(f"🧪 {name}")
        print(f"{'='*60}")
        print(result.stdout)
        if result.stderr:
            print(f"stderr: {result.stderr}")

        success = result.returncode == expected_code
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} (Exit Code: {result.returncode}, Expected: {expected_code})")

        results.append((name, success))

    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
