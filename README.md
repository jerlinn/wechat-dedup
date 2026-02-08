# WeChat File Deduplicator

微信文件去重工具（MacOS）。扫描 `file`/`attach`/`video` 目录，通过文件大小 + MD5 哈希识别重复，移动副本到隔离文件夹。

## Install SKill

```bash
git clone git@github.com:jerlinn/wechat-dedup.git ~/.claude/skills/wechat-dedup
```

## Usage

**1. Via Skill** (Claude Code / Antigravity / Codex / Cursor)

打开任意文件夹，输入「微信去重」

**2. Direct Execution**

```bash
python3 ~/.claude/skills/wechat-dedup/wechat-dedup/scripts/dedup.py
```

## Scan Targets

| Directory | Type | Extensions |
|-----------|------|------------|
| `*/msg/file` | 文档 | .pdf, .doc, .docx |
| `*/msg/attach` | 图片附件 | .dat, .jpg, .png, .gif |
| `*/msg/video` | 视频 | .mp4, .mov, .avi |

Base path: `~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files`

## Algorithm

Inspired by [fclones](https://github.com/pkolaczk/fclones) by Piotr Kołaczkowski:

1. **Size grouping** (O(n)): Files with unique sizes cannot be duplicates
2. **Hash on demand**: Only compute MD5 for size-matched files
3. **Streaming hash**: Memory-efficient for large files
4. **Minimum size filter**: Skip files < 10KB (thumbnails)

Retention strategy: Keep the file with earliest creation time (`st_birthtime`).

## Output

| Item | Path |
|------|------|
| Quarantine | `~/微信重复文件_待删除/` |
| Report | `~/微信重复文件_待删除/去重报告.md` |

## Requirements

- Python 3.8+
- macOS
- No external dependencies

## License

MIT