#!/usr/bin/env python3
"""
Claude Code Hook: 文档编辑前一致性检查
触发时机：Edit/Write 四文档（requirements/design/tasks/approve.md）前
功能：验证编辑不会破坏四文档的一致性契约

作者：Claude Code
创建时间：2025-12-17
"""

import os
import sys
import re
from pathlib import Path

# 从环境变量获取目标文件路径
file_path = os.environ.get("CLAUDE_FILE_PATH", "")

# 四文档路径模式
TASK_DOC_PATTERN = re.compile(
    r"(?:\.kiro[/\\]specs[/\\]phase-\d+-[\w-]+[/\\]task-\d+|Governance[/\\]specs[/\\]spiral-s\d+[/\\]task-\d+)"
    r"[/\\](requirements|design|tasks|approve)\.md"
)

def is_task_doc(path: str) -> bool:
    """检查是否为任务规格四文档"""
    return TASK_DOC_PATTERN.search(path.replace("\\", "/")) is not None

def get_task_dir(path: str) -> Path:
    """从文件路径提取任务目录"""
    path_obj = Path(path)
    # 向上查找到 task-XX 目录
    for parent in path_obj.parents:
        if parent.name.startswith("task-"):
            return parent
    return None

def main():
    """主函数"""
    # 如果不是四文档，直接通过
    if not is_task_doc(file_path):
        sys.exit(0)

    # 提取任务目录
    task_dir = get_task_dir(file_path)
    if not task_dir or not task_dir.exists():
        sys.exit(0)

    # 输出提醒
    print("=" * 60)
    print("💡 文档一致性提醒")
    print("=" * 60)
    print(f"📝 正在编辑: {Path(file_path).name}")
    print(f"📂 任务目录: {task_dir.name}")
    print()
    print("⚠️  编辑四文档后，建议运行一致性检查：")
    print(f"   /doc-check")
    print()
    print("🔍 关键检查项：")
    print("   - 工时统一（20 小时）")
    print("   - Step 数量（15 个）")
    print("   - 日期格式（YYYY-MM-DD）")
    print("   - 无 Mock 关键词")
    print("=" * 60)

    # 通过检查（仅提醒，不阻塞）
    sys.exit(0)

if __name__ == "__main__":
    main()
