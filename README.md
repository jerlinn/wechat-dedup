# WeChat Document Deduplicator

> A Claude Code Skill for finding and removing duplicate documents in WeChat folders

微信文档去重工具 - 自动识别并清理微信产生的重复文档文件

## Problem

WeChat (微信) tends to create multiple copies of the same document when:
- Files are forwarded multiple times
- Files are saved from different chats
- Sync issues between devices

This results in files like:
```
document.pdf
document(1).pdf
document(2).pdf
```

These duplicates waste significant storage space.

## Solution

This skill scans your WeChat folder, identifies duplicate documents by **content hash** (not filename), and safely moves duplicates to a quarantine folder.

### Key Features

- **Content-based detection**: Uses MD5 hash to identify truly identical files
- **Safe operation**: Moves files to quarantine instead of deleting
- **Smart retention**: Keeps the oldest (original) file
- **Detailed report**: Generates a markdown report of all actions

## Installation

### For Claude Code Users

```bash
# Clone to your skills directory
git clone https://github.com/rolandwong/wechat-dedup.git ~/.claude/skills/wechat-dedup
```

### Manual Installation

```bash
git clone https://github.com/rolandwong/wechat-dedup.git
cd wechat-dedup
python3 dedup.py
```

## Usage

### Via Claude Code

Just say:
- `微信去重`
- `清理微信重复文件`
- `wechat dedup`

### Via Command Line

```bash
python3 ~/.claude/skills/wechat-dedup/dedup.py
```

## How It Works

1. **Scan**: Finds all PDF and Word documents in WeChat folder
2. **Hash**: Groups files by size first (fast), then by MD5 hash (accurate)
3. **Select**: Keeps the file with earliest creation time
4. **Move**: Moves duplicates to `~/微信重复文件_待删除/`
5. **Report**: Generates `去重报告.md` with full details

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Scan Path | WeChat folder | Auto-detected on macOS |
| File Types | PDF, DOC, DOCX | Can be extended |
| Quarantine | `~/微信重复文件_待删除/` | 30-day holding period |
| Keep Strategy | Oldest file | By creation time |

## Requirements

- Python 3.8+
- macOS (for WeChat path detection)
- No external dependencies

## Safety

- **No direct deletion**: Files are moved, not deleted
- **Original paths recorded**: Full paths saved in report
- **Recoverable**: Files can be restored from quarantine
- **Preview mode**: Review before executing

## Algorithm

Inspired by [fclones](https://github.com/pkolaczk/fclones) by Piotr Kołaczkowski:

1. **Size grouping** (O(n)): Files with unique sizes can't be duplicates
2. **Hash only when needed**: Only compute MD5 for size-matched files
3. **Streaming hash**: Memory-efficient for large files

## License

MIT

## Author

Created by Roland Wong with Claude Code

---

*Part of the [awesome-claude-skills](https://github.com/anthropics/awesome-claude-skills) ecosystem*
