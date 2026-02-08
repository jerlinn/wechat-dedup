---
name: wechat-dedup
description: |
  微信文件去重工具（MacOS）。扫描 attach/video/file 目录，通过文件大小 + MD5 哈希识别重复，移动副本到隔离文件夹。
  触发：微信去重、清理微信重复文件、wechat dedup、微信文件太多、微信占用空间
---

# WeChat 文件去重

## 执行

```bash
python3 ~/.claude/skills/wechat-dedup/scripts/dedup.py
```

## 扫描范围

| 目录 | 类型 | 扩展名 |
|------|------|--------|
| `*/msg/file` | 文档 | .pdf, .doc, .docx |
| `*/msg/attach` | 图片附件 | .dat, .jpg, .png, .gif |
| `*/msg/video` | 视频 | .mp4, .mov, .avi |

## 策略
fclones 算法：按文件大小分组 → 仅对同大小文件计算 MD5 → 保留最早创建时间的文件

## Output

- 隔离目录：`~/微信重复文件_待删除/`
- 报告：`~/微信重复文件_待删除/去重报告.md`
