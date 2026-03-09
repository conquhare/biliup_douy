---
name: "encoding-checker"
description: "检测和修复项目文件编码问题，特别是 GBK/UTF-8 乱码问题"
---

# 编码检查与修复技能

## 适用场景

**当出现以下情况时使用此技能：**
1. 代码文件中的中文显示为乱码（如 `鎶栭煶勫` 等）
2. 构建时出现编码错误（如 "UnicodeDecodeError"）
3. 日志中出现 "stream did not contain valid UTF-8"
4. 跨平台协作时出现编码不一致
5. 从 Windows 迁移到 Linux/Mac 后出现编码问题

## 问题原理

Windows 系统默认使用 GBK/GB2312 编码，而现代开发通常使用 UTF-8。当 UTF-8 文件被错误地用 GBK 解析时，就会产生乱码。

乱码产生过程：
```
原始 UTF-8 内容 → 错误地用 GBK 解码 → 保存为 UTF-8 乱码
```

## 快速诊断

### 方法1：查看文件内容
```powershell
# 查看文件前100个字符，如果出现"锘"或"鎶"等奇怪字符，说明有编码问题
$content = Get-Content "文件路径" -Raw
Write-Host $content.Substring(0, 100)
```

### 方法2：使用 Python 检测
```python
# 读取文件字节，检查是否包含 GBK 乱码特征
with open("文件路径", 'rb') as f:
    content = f.read()
    
# 尝试用 UTF-8 解码
try:
    text = content.decode('utf-8')
    # 检查是否包含扩展A区字符（乱码特征）
    ext_a_chars = [c for c in text if 0x3400 <= ord(c) <= 0x4DBF]
    if ext_a_chars:
        print(f"发现乱码特征字符: {set(ext_a_chars)}")
except UnicodeDecodeError:
    print("文件不是有效的 UTF-8 编码")
```

### 方法3：识别乱码特征
GBK 乱码通常表现为：
- 出现 `鎶`、`栭`、`煶` 等生僻字
- 原本的中文变成了不认识的符号
- 文件头部出现 `锘` 字符（UTF-8 BOM 被错误解析）

## 修复方案

### 方案1：使用项目内置工具（推荐）
```bash
# 运行编码修复工具
python encoding_fixer.py
```

### 方案2：手动修复单个文件
```powershell
# 用 GBK 编码读取，再用 UTF-8 保存
[System.IO.File]::ReadAllText("源文件", [System.Text.Encoding]::GetEncoding("GBK")) | 
    Out-File -FilePath "目标文件" -Encoding UTF8
```

### 方案3：批量修复
```powershell
# 批量修复项目中的所有 .py 文件
Get-ChildItem -Path "." -Recurse -Filter "*.py" | ForEach-Object {
    try {
        $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::GetEncoding("GBK"))
        $content | Out-File -FilePath $_.FullName -Encoding UTF8
        Write-Host "已修复: $($_.Name)"
    } catch {
        Write-Host "跳过: $($_.Name)"
    }
}
```

## 预防措施

### 1. 编辑器配置 (VS Code)
确保 VS Code 默认使用 UTF-8 编码：

**settings.json**:
```json
{
  "files.encoding": "utf8",
  "files.autoGuessEncoding": false,
  "files.candidateGuessEncodings": ["utf8"]
}
```

⚠️ **注意**: 不要设置 `"files.candidateGuessEncodings": ["utf8", "gb2312"]`，这会导致 VS Code 自动用 GBK 打开文件，从而引入编码问题。

**修复已打开的文件**：
1. 点击 VS Code 右下角的编码显示（如 "UTF-8"）
2. 选择 "通过编码重新打开" → "GB2312" 查看原始内容
3. 然后选择 "通过编码保存" → "UTF-8"

### 2. Git 配置
```bash
# 设置 Git 使用 UTF-8
git config core.quotepath off
git config gui.encoding utf-8
git config i18n.commit.encoding utf-8
git config i18n.logoutputencoding utf-8
```

### 3. 项目级配置
在项目根目录创建 `.editorconfig` 文件：
```ini
[*]
charset = utf-8
```

### 4. Python 文件头
所有 Python 文件添加编码声明：
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```

## 验证修复

修复后验证：
1. 重新打开文件，中文显示正常
2. 运行 `python test_encoding_fix.py` 检查
3. 重新构建项目（`cargo build` 或 `npm run build`）
4. 检查日志输出是否正常
5. 提交到 Git，确保 diff 显示正常

## 常见受影响文件类型

- Python 脚本 (`.py`)
- Rust 源文件 (`.rs`)
- TypeScript/React 组件 (`.ts`, `.tsx`)
- JavaScript 文件 (`.js`, `.jsx`)
- CSS/SCSS 文件 (`.css`, `.scss`)
- Markdown 文档 (`.md`)
- 配置文件 (`.json`, `.yaml`, `.toml`)

## 核心修复原理

```
当前状态：UTF-8 编码的乱码字符（如"鎶栭煶勫"）
    ↓ 编码为 GBK 字节
中间状态：恢复原始 UTF-8 字节
    ↓ 用 UTF-8 解码
修复结果：正确的中文（如"抖音弹幕"）
```

## 最佳实践

1. **统一编码标准**：团队统一使用 UTF-8
2. **提交前检查**：提交前运行编码检查脚本
3. **CI/CD 集成**：在构建流程中添加编码验证
4. **避免自动检测**：关闭编辑器的编码自动检测功能

## 相关工具

- `encoding_fixer.py` - 项目内置编码修复工具
- `test_encoding_fix.py` - 编码测试验证工具
- `PROJECT_KNOWLEDGE.md` - 编码问题知识库
