#!/usr/bin/env python3
"""WeChat 文件去重 - fclones 算法：文件大小分组 + MD5 哈希"""

import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

WECHAT_BASE = Path.home() / "Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files"
SCAN_TARGETS = {
    'file': {
        'pattern': '*/msg/file',
        'extensions': {'.pdf', '.doc', '.docx'},
        'description': '文档'
    },
    'attach': {
        'pattern': '*/msg/attach',
        'extensions': {'.dat', '.jpg', '.jpeg', '.png', '.gif'},
        'description': '图片附件'
    },
    'video': {
        'pattern': '*/msg/video',
        'extensions': {'.mp4', '.mov', '.avi'},
        'description': '视频'
    }
}
QUARANTINE_DIR = Path.home() / "微信重复文件_待删除"
REPORT_FILE = QUARANTINE_DIR / "去重报告.md"
MIN_FILE_SIZE = 10 * 1024  # 10KB，跳过缩略图


def get_file_hash(filepath: Path, chunk_size: int = 8192) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None


def get_creation_time(filepath: Path) -> float:
    try:
        s = filepath.stat()
        return getattr(s, 'st_birthtime', s.st_mtime)
    except (IOError, OSError):
        return float('inf')


def scan_documents(base_path: Path, targets: dict, min_size: int = 0) -> dict:
    results = {}
    if not base_path.exists():
        return results

    for target_name, config in targets.items():
        files = []
        for target_dir in base_path.glob(config['pattern']):
            if not target_dir.exists():
                continue
            for filepath in target_dir.rglob('*'):
                if not filepath.is_file():
                    continue
                if filepath.suffix.lower() not in config['extensions']:
                    continue
                try:
                    if filepath.stat().st_size < min_size:
                        continue
                except (IOError, OSError):
                    continue
                files.append(filepath)

        if files:
            results[target_name] = {'files': files, 'description': config['description']}
    return results


def find_duplicates(documents: list) -> dict:
    size_groups = defaultdict(list)
    for doc in documents:
        try:
            size_groups[doc.stat().st_size].append(doc)
        except (IOError, OSError):
            continue

    hash_groups = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) < 2:
            continue
        for filepath in files:
            file_hash = get_file_hash(filepath)
            if file_hash:
                hash_groups[file_hash].append(filepath)

    return {h: files for h, files in hash_groups.items() if len(files) >= 2}


def select_keeper(files: list) -> tuple:
    sorted_files = sorted(files, key=get_creation_time)
    return sorted_files[0], sorted_files[1:]


def move_to_quarantine(filepath: Path, quarantine_dir: Path) -> Path:
    target_path = quarantine_dir / filepath.name
    counter = 1
    while target_path.exists():
        target_path = quarantine_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
        counter += 1
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(filepath), str(target_path))
    return target_path


def generate_report(results: dict, quarantine_dir: Path) -> str:
    report = f"""# 微信文件去重报告

**执行时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 统计摘要

| 指标 | 数值 |
|------|------|
| 重复组数 | {len(results['groups'])} |
| 移除文件数 | {results['removed_count']} |
| 节省空间 | {format_size(results['saved_bytes'])} |
| 隔离文件夹 | `{quarantine_dir}` |

## 重复文件详情

"""

    # 按类型分组
    by_type = {}
    for group in results['groups']:
        file_type = group.get('type', '未知')
        if file_type not in by_type:
            by_type[file_type] = []
        by_type[file_type].append(group)

    for file_type, groups in by_type.items():
        report += f"### {file_type}\n\n"
        for i, group in enumerate(groups, 1):
            keeper_name = Path(group['keeper']).name
            report += f"**组 {i}** - 保留：`{keeper_name}`\n"
            for removed in group['removed']:
                removed_name = Path(removed['original']).name
                report += f"- `{removed_name}` ({format_size(removed['size'])})\n"
            report += "\n"

    report += "---\n\n> 文件已移动到隔离文件夹，确认后可删除。\n"
    return report


def format_size(bytes_size: int) -> str:
    if bytes_size >= 1024 ** 3:
        return f"{bytes_size / 1024 ** 3:.2f} GB"
    if bytes_size >= 1024 ** 2:
        return f"{bytes_size / 1024 ** 2:.2f} MB"
    if bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} KB"
    return f"{bytes_size} B"


def main():
    print("WeChat 文件去重")

    print("\n[1/4] 扫描微信文件夹...")
    scan_results = scan_documents(WECHAT_BASE, SCAN_TARGETS, MIN_FILE_SIZE)

    if not scan_results:
        print("      未找到文件，退出。")
        return

    total_files = 0
    for target_name, data in scan_results.items():
        count = len(data['files'])
        total_files += count
        print(f"      {data['description']}: {count} 个文件")

    print(f"      总计: {total_files} 个文件")

    print("\n[2/4] 分析重复文件...")
    all_duplicates = {}
    total_dup_groups = 0

    for target_name, data in scan_results.items():
        duplicates = find_duplicates(data['files'])
        if duplicates:
            all_duplicates[target_name] = {
                'duplicates': duplicates,
                'description': data['description']
            }
            total_dup_groups += len(duplicates)
            print(f"      {data['description']}: {len(duplicates)} 组重复")

    if not all_duplicates:
        print("      未发现重复文件，退出。")
        return

    print(f"\n[3/4] 重复文件预览（共 {total_dup_groups} 组）：")
    print("-" * 50)

    results = {
        'groups': [],
        'removed_count': 0,
        'saved_bytes': 0
    }

    for target_name, dup_data in all_duplicates.items():
        print(f"\n【{dup_data['description']}】")

        for hash_val, files in dup_data['duplicates'].items():
            keeper, to_remove = select_keeper(files)

            group_info = {
                'type': dup_data['description'],
                'keeper': str(keeper),
                'removed': []
            }

            print(f"\n  保留: {keeper.name}")

            for f in to_remove:
                try:
                    size = f.stat().st_size
                except (IOError, OSError):
                    continue
                results['saved_bytes'] += size
                print(f"  移除: {f.name} ({format_size(size)})")
                group_info['removed'].append({
                    'original': str(f),
                    'quarantine': None,
                    'size': size
                })

            results['groups'].append(group_info)
            results['removed_count'] += len(to_remove)

    print("-" * 50)
    print(f"\n总计：{results['removed_count']} 个重复文件，可节省 {format_size(results['saved_bytes'])}")

    print("\n[4/4] 确认操作")
    if input("是否将重复文件移动到隔离文件夹？(y/n): ").strip().lower() != 'y':
        print("已取消操作。")
        return

    print("\n正在移动文件...")
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    for group in results['groups']:
        for removed in group['removed']:
            original_path = Path(removed['original'])
            if original_path.exists():
                new_path = move_to_quarantine(original_path, QUARANTINE_DIR)
                removed['quarantine'] = str(new_path)
                moved_count += 1
                if moved_count <= 20:  # 只显示前20个
                    print(f"  ✓ {original_path.name}")
                elif moved_count == 21:
                    print(f"  ... 省略剩余 {results['removed_count'] - 20} 个文件")

    REPORT_FILE.write_text(generate_report(results, QUARANTINE_DIR), encoding='utf-8')

    if moved_count != results['removed_count']:
        print(f"\n⚠️ 校验失败：预期 {results['removed_count']}，实际 {moved_count}，差异 {results['removed_count'] - moved_count}")
    else:
        print(f"\n✓ 完成：移动 {moved_count} 个文件，节省 {format_size(results['saved_bytes'])}")
        print(f"  隔离：{QUARANTINE_DIR}")
        print(f"  报告：{REPORT_FILE}")


if __name__ == "__main__":
    main()
