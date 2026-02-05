#!/usr/bin/env python3
"""
WeChat 文档去重工具
基于 Piotr Kołaczkowski (fclones作者) 的去重算法思想

核心策略：
1. 先按文件大小分组（快速筛选）
2. 再按 MD5 哈希确认（精确匹配）
3. 保留最早创建的文件
4. 移动重复文件到隔离文件夹
"""

import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json

# 配置
WECHAT_PATHS = [
    Path.home() / "Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files",
    Path.home() / "Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support",
]
QUARANTINE_DIR = Path.home() / "微信重复文件_待删除"
REPORT_FILE = QUARANTINE_DIR / "去重报告.md"
FILE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.PDF', '.DOC', '.DOCX'}


def get_file_hash(filepath: Path, chunk_size: int = 8192) -> str:
    """计算文件的 MD5 哈希值"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None


def get_creation_time(filepath: Path) -> float:
    """获取文件创建时间（macOS）"""
    try:
        stat = filepath.stat()
        # macOS: st_birthtime 是创建时间
        return getattr(stat, 'st_birthtime', stat.st_mtime)
    except (IOError, OSError):
        return float('inf')


def scan_documents(paths: list) -> list:
    """扫描指定路径下的所有文档文件"""
    documents = []
    for base_path in paths:
        if not base_path.exists():
            continue
        for filepath in base_path.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in {'.pdf', '.doc', '.docx'}:
                documents.append(filepath)
    return documents


def find_duplicates(documents: list) -> dict:
    """
    查找重复文件

    策略（来自 fclones）：
    1. 先按文件大小分组 - O(n)
    2. 只对大小相同的文件计算哈希 - 减少 I/O
    """
    # 第一轮：按文件大小分组
    size_groups = defaultdict(list)
    for doc in documents:
        try:
            size = doc.stat().st_size
            size_groups[size].append(doc)
        except (IOError, OSError):
            continue

    # 第二轮：对大小相同的文件计算哈希
    hash_groups = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue  # 大小唯一，不可能重复

        for filepath in files:
            file_hash = get_file_hash(filepath)
            if file_hash:
                hash_groups[file_hash].append(filepath)

    # 过滤出真正的重复组（2个或以上文件）
    duplicates = {h: files for h, files in hash_groups.items() if len(files) >= 2}
    return duplicates


def select_keeper(files: list) -> tuple:
    """
    选择要保留的文件（最早创建的）
    返回：(保留的文件, 要删除的文件列表)
    """
    sorted_files = sorted(files, key=get_creation_time)
    return sorted_files[0], sorted_files[1:]


def move_to_quarantine(filepath: Path, quarantine_dir: Path) -> Path:
    """将文件移动到隔离文件夹，保持相对路径结构"""
    # 创建目标路径
    relative_path = filepath.name
    target_path = quarantine_dir / relative_path

    # 处理同名文件
    counter = 1
    while target_path.exists():
        stem = filepath.stem
        suffix = filepath.suffix
        target_path = quarantine_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    # 移动文件
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(filepath), str(target_path))
    return target_path


def generate_report(results: dict, quarantine_dir: Path) -> str:
    """生成去重报告"""
    total_groups = len(results['groups'])
    total_removed = results['removed_count']
    total_saved = results['saved_bytes']

    report = f"""# 微信文档去重报告

**执行时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 统计摘要

| 指标 | 数值 |
|------|------|
| 重复组数 | {total_groups} |
| 移除文件数 | {total_removed} |
| 节省空间 | {total_saved / 1024 / 1024:.2f} MB |
| 隔离文件夹 | `{quarantine_dir}` |

## 重复文件详情

"""

    for i, group in enumerate(results['groups'], 1):
        report += f"### 组 {i}\n\n"
        report += f"**保留**：`{group['keeper']}`\n\n"
        report += "**移除**：\n"
        for removed in group['removed']:
            report += f"- `{removed['original']}` → `{removed['quarantine']}`\n"
        report += "\n"

    report += """
---

> 这些文件已移动到隔离文件夹，30天后请自行确认删除。
> 如需恢复，请从隔离文件夹中找回。
"""
    return report


def main():
    print("=" * 50)
    print("WeChat 文档去重工具")
    print("=" * 50)

    # 1. 扫描文档
    print("\n[1/4] 扫描微信文件夹...")
    documents = scan_documents(WECHAT_PATHS)
    print(f"      找到 {len(documents)} 个文档文件")

    if not documents:
        print("      未找到文档文件，退出。")
        return

    # 2. 查找重复
    print("\n[2/4] 分析重复文件...")
    duplicates = find_duplicates(documents)
    print(f"      发现 {len(duplicates)} 组重复文件")

    if not duplicates:
        print("      没有发现重复文件，退出。")
        return

    # 3. 显示预览
    print("\n[3/4] 重复文件预览：")
    print("-" * 50)

    results = {
        'groups': [],
        'removed_count': 0,
        'saved_bytes': 0
    }

    for hash_val, files in duplicates.items():
        keeper, to_remove = select_keeper(files)

        group_info = {
            'keeper': str(keeper),
            'removed': []
        }

        print(f"\n保留: {keeper.name}")
        print(f"      创建时间: {datetime.fromtimestamp(get_creation_time(keeper))}")

        for f in to_remove:
            size = f.stat().st_size
            results['saved_bytes'] += size
            print(f"移除: {f.name} ({size / 1024:.1f} KB)")
            group_info['removed'].append({
                'original': str(f),
                'quarantine': None,
                'size': size
            })

        results['groups'].append(group_info)
        results['removed_count'] += len(to_remove)

    print("-" * 50)
    print(f"\n总计：{results['removed_count']} 个重复文件")
    print(f"可节省：{results['saved_bytes'] / 1024 / 1024:.2f} MB")

    # 4. 确认执行
    print("\n[4/4] 确认操作")
    confirm = input("是否将重复文件移动到隔离文件夹？(y/n): ").strip().lower()

    if confirm != 'y':
        print("已取消操作。")
        return

    # 执行移动
    print("\n正在移动文件...")
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    for group in results['groups']:
        for removed in group['removed']:
            original_path = Path(removed['original'])
            if original_path.exists():
                new_path = move_to_quarantine(original_path, QUARANTINE_DIR)
                removed['quarantine'] = str(new_path)
                print(f"  ✓ {original_path.name}")

    # 生成报告
    report = generate_report(results, QUARANTINE_DIR)
    REPORT_FILE.write_text(report, encoding='utf-8')
    print(f"\n报告已保存：{REPORT_FILE}")

    print("\n" + "=" * 50)
    print("完成！重复文件已移动到隔离文件夹。")
    print(f"隔离文件夹：{QUARANTINE_DIR}")
    print("请在30天后确认删除。")
    print("=" * 50)


if __name__ == "__main__":
    main()
