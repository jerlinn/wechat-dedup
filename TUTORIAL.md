# 如何创建一个 Claude Code Skill：以微信去重为例

> 本教程将手把手教你从零开始创建一个实用的 Claude Code Skill

## 什么是 Claude Code Skill？

Skill 是一组指令和脚本，让 Claude Code 能够执行特定任务。当你说出触发词时，Claude 会自动加载对应的 Skill 并执行。

**类比**：Skill 就像是给 Claude 的"技能书"，读完后它就会了这个技能。

---

## 第一步：明确需求

### 1.1 发现问题

我发现微信会产生大量重复文件：
```
文档.pdf
文档(1).pdf
文档(2).pdf
```

这些重复文件占用了大量存储空间。

### 1.2 定义解决方案

我需要一个工具：
- 扫描微信文件夹
- 识别内容相同的文件（不只是看文件名）
- 保留最早的那个
- 把重复的移到隔离文件夹

### 1.3 选择专家视角

在开始编码前，我选择了 **Piotr Kołaczkowski**（fclones 作者）的视角来思考这个问题。他是文件去重领域的专家，他的算法思想是：

> 先按文件大小分组（快），再对候选文件计算哈希（准）

---

## 第二步：创建 Skill 目录结构

### 2.1 创建文件夹

```bash
mkdir -p ~/.claude/skills/wechat-dedup
```

### 2.2 Skill 的标准结构

```
~/.claude/skills/wechat-dedup/
├── SKILL.md      # 必需：Skill 描述文件
├── dedup.py      # 核心脚本
├── README.md     # GitHub 文档
└── .gitignore    # Git 配置
```

---

## 第三步：编写 SKILL.md

这是 Claude Code 识别 Skill 的关键文件。

```markdown
# WeChat 文档去重 Skill

## 功能

扫描微信文件夹中的重复文档，将重复项移动到隔离文件夹。

## 触发词

- `微信去重`
- `清理微信重复文件`
- `wechat dedup`

## 工作流程

1. 扫描：找出所有 PDF 和 Word 文档
2. 指纹：计算文件大小 + MD5 哈希
3. 分组：相同指纹的文件归为一组
4. 保留：每组保留最早创建的文件
5. 隔离：移动重复文件到隔离文件夹
6. 报告：生成去重报告

## 使用方法

说 "微信去重" 或运行：
python3 ~/.claude/skills/wechat-dedup/dedup.py
```

### SKILL.md 的关键要素

| 要素 | 说明 | 示例 |
|------|------|------|
| 标题 | Skill 名称 | `# WeChat 文档去重 Skill` |
| 功能 | 一句话描述 | 扫描并清理重复文档 |
| 触发词 | 用户说什么会激活 | `微信去重`、`wechat dedup` |
| 工作流程 | 步骤说明 | 1. 扫描 2. 分析 3. 移动 |
| 使用方法 | 如何调用 | 命令或自然语言 |

---

## 第四步：编写核心脚本

### 4.1 设计算法

```python
# 伪代码
def find_duplicates(documents):
    # 阶段1：按大小分组（快速筛选）
    size_groups = group_by_size(documents)

    # 阶段2：对大小相同的文件计算哈希（精确匹配）
    hash_groups = {}
    for size, files in size_groups.items():
        if len(files) >= 2:  # 只处理可能重复的
            for f in files:
                hash = calculate_md5(f)
                hash_groups[hash].append(f)

    return hash_groups
```

### 4.2 完整代码结构

```python
#!/usr/bin/env python3
"""
WeChat 文档去重工具
"""

import os
import hashlib
import shutil
from pathlib import Path
from collections import defaultdict

# ========== 配置 ==========
WECHAT_PATHS = [
    Path.home() / "Library/Containers/com.tencent.xinWeChat/...",
]
QUARANTINE_DIR = Path.home() / "微信重复文件_待删除"
FILE_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# ========== 核心函数 ==========

def get_file_hash(filepath):
    """计算文件的 MD5 哈希"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_creation_time(filepath):
    """获取文件创建时间"""
    return filepath.stat().st_birthtime

def scan_documents(paths):
    """扫描所有文档文件"""
    documents = []
    for base_path in paths:
        for filepath in base_path.rglob('*'):
            if filepath.suffix.lower() in FILE_EXTENSIONS:
                documents.append(filepath)
    return documents

def find_duplicates(documents):
    """查找重复文件"""
    # 阶段1：按大小分组
    size_groups = defaultdict(list)
    for doc in documents:
        size_groups[doc.stat().st_size].append(doc)

    # 阶段2：计算哈希
    hash_groups = defaultdict(list)
    for size, files in size_groups.items():
        if len(files) >= 2:
            for f in files:
                hash_groups[get_file_hash(f)].append(f)

    # 返回真正的重复组
    return {h: files for h, files in hash_groups.items() if len(files) >= 2}

def select_keeper(files):
    """选择保留最早创建的文件"""
    sorted_files = sorted(files, key=get_creation_time)
    return sorted_files[0], sorted_files[1:]

def move_to_quarantine(filepath, quarantine_dir):
    """移动文件到隔离文件夹"""
    target = quarantine_dir / filepath.name
    shutil.move(str(filepath), str(target))
    return target

# ========== 主程序 ==========

def main():
    print("扫描微信文件夹...")
    docs = scan_documents(WECHAT_PATHS)

    print("分析重复文件...")
    dups = find_duplicates(docs)

    print(f"发现 {len(dups)} 组重复文件")

    # 显示预览并确认
    # ...

    # 执行移动
    QUARANTINE_DIR.mkdir(exist_ok=True)
    for hash_val, files in dups.items():
        keeper, to_remove = select_keeper(files)
        for f in to_remove:
            move_to_quarantine(f, QUARANTINE_DIR)

if __name__ == "__main__":
    main()
```

---

## 第五步：测试 Skill

### 5.1 单元测试

```bash
# 测试扫描功能
python3 -c "
from dedup import scan_documents, WECHAT_PATHS
docs = scan_documents(WECHAT_PATHS)
print(f'找到 {len(docs)} 个文档')
"
```

### 5.2 集成测试

```bash
# 预览模式（不实际移动）
python3 -c "
from dedup import scan_documents, find_duplicates, WECHAT_PATHS
docs = scan_documents(WECHAT_PATHS)
dups = find_duplicates(docs)
print(f'发现 {len(dups)} 组重复')
"
```

### 5.3 完整测试

```bash
python3 ~/.claude/skills/wechat-dedup/dedup.py
```

---

## 第六步：发布到 GitHub

### 6.1 初始化仓库

```bash
cd ~/.claude/skills/wechat-dedup
git init
git add .
git commit -m "Initial release: WeChat document deduplicator"
```

### 6.2 创建 GitHub 仓库

```bash
gh repo create wechat-dedup --public --source=. --push
```

### 6.3 分享安装命令

```bash
# 其他人可以这样安装
git clone https://github.com/你的用户名/wechat-dedup.git ~/.claude/skills/wechat-dedup
```

---

## 第七步：最佳实践

### 7.1 Skill 设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 一个 Skill 只做一件事 |
| **安全第一** | 不直接删除，先隔离 |
| **可恢复** | 所有操作都可以撤销 |
| **有反馈** | 显示进度和结果 |
| **可配置** | 关键参数可以修改 |

### 7.2 触发词设计

```markdown
好的触发词：
- 简短：微信去重
- 明确：清理微信重复文件
- 英文：wechat dedup

不好的触发词：
- 太长：帮我清理一下微信里面的重复文档文件
- 太模糊：清理文件
- 有歧义：去重（去重什么？）
```

### 7.3 错误处理

```python
def safe_move(filepath, target_dir):
    """安全移动文件，处理各种异常"""
    try:
        # 检查源文件存在
        if not filepath.exists():
            return None, "文件不存在"

        # 检查目标目录
        target_dir.mkdir(parents=True, exist_ok=True)

        # 处理同名文件
        target = target_dir / filepath.name
        counter = 1
        while target.exists():
            target = target_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
            counter += 1

        # 执行移动
        shutil.move(str(filepath), str(target))
        return target, None

    except PermissionError:
        return None, "权限不足"
    except Exception as e:
        return None, str(e)
```

---

## 总结：创建 Skill 的完整流程

```
1. 明确需求
   ↓
2. 选择专家视角（可选但推荐）
   ↓
3. 创建目录结构
   ~/.claude/skills/你的skill名/
   ↓
4. 编写 SKILL.md
   - 功能描述
   - 触发词
   - 使用方法
   ↓
5. 编写核心脚本
   - 算法设计
   - 错误处理
   - 用户反馈
   ↓
6. 测试
   - 单元测试
   - 集成测试
   - 完整测试
   ↓
7. 发布到 GitHub
   - git init
   - gh repo create
   ↓
8. 分享给他人
   git clone ... ~/.claude/skills/...
```

---

## 附录：常用代码片段

### A. 文件哈希

```python
import hashlib

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### B. 递归扫描

```python
from pathlib import Path

def scan_files(directory, extensions):
    for filepath in Path(directory).rglob('*'):
        if filepath.is_file() and filepath.suffix.lower() in extensions:
            yield filepath
```

### C. 安全移动

```python
import shutil

def safe_move(src, dst_dir):
    dst = dst_dir / src.name
    counter = 1
    while dst.exists():
        dst = dst_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    return shutil.move(str(src), str(dst))
```

### D. 生成报告

```python
def generate_report(results):
    report = "# 执行报告\n\n"
    report += f"| 指标 | 数值 |\n"
    report += f"|------|------|\n"
    report += f"| 处理文件 | {results['count']} |\n"
    report += f"| 节省空间 | {results['saved_mb']:.2f} MB |\n"
    return report
```

---

*本教程基于 wechat-dedup Skill 的实际开发过程编写*
*GitHub: https://github.com/rolandwonglonam/wechat-dedup*
