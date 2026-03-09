# PROJECT_KNOWLEDGE.md

## 编码问题修复技能库

> **用途**: 快速解决项目中的 GBK/UTF-8 编码乱码问题  
> **相关技能**: `encoding-checker`

---

## 相关文档

- `PROJECT_INFO.md` - 项目信息和任务管理（主文档）
- `PROJECT_INCOMPLETE.md` - 编码问题事件复盘和经验总结
- `FIX_SUMMARY.md` - 问题修复详细记录

---

## 项目技能索引

项目已沉淀以下可复用技能，位于 `.claude/skills/` 和 `.trae/skills/`：

| 技能 | 用途 | 适用场景 |
|------|------|----------|
| `encoding-checker` | 编码问题检测与修复 | 处理 GBK/UTF-8 乱码问题 |
| `proxy-troubleshooting` | GitHub 代理连接故障排查 | 解决 git push 失败、GitHub 访问问题 |
| `douyin-danmaku` | 抖音弹幕录制开发 | WebSocket 连接、签名计算、protobuf 解析 |
| `live-stream-download` | 直播流下载引擎开发 | 多平台适配、分段录制、下载管理 |
| `bilibili-upload` | B站视频上传开发 | 分P上传、线路选择、投稿接口 |
| `ci-cd-build` | CI/CD 构建流程 | Windows EXE 构建、版本号管理、发布流程 |
| `gitnexus-*` | 代码库分析 | 架构理解、影响分析、调试追踪、重构指导 |

---

## 快速开始

### 1. 检测编码问题
```bash
python encoding_fixer.py
```

### 2. 验证修复结果
```bash
python test_encoding_fix.py
```

---

## 问题诊断

### 乱码特征
- 中文显示为 `鎶栭煶勫` 等生僻字
- 出现 Unicode 扩展 A 区字符（0x3400-0x4DBF）
- 文件头部出现 `锘` 字符

### 产生机制
```
原始 UTF-8 内容 → 错误地用 GBK 解码 → 保存为 UTF-8 乱码
```

---

## 修复原理

**逆向修复**:
```python
# 乱码字符 → GBK 字节 → UTF-8 正确内容
mojibake_text = "鎶栭煶勫"
gbk_bytes = mojibake_text.encode('gbk')
fixed_text = gbk_bytes.decode('utf-8')  # "抖音弹幕"
```

---

## 工具说明

### encoding_fixer.py
- **智能检测**: 分析 Unicode 字符分布，识别扩展 A 区字符
- **自动修复**: GBK→UTF-8 逆向转换
- **批量处理**: 递归扫描项目目录

**检测算法**:
```python
if ext_a_ratio > 0.005 or gbk_gibberish_count >= 3:
    is_mojibake = True  # 判定为乱码文件
```

### test_encoding_fix.py
- 验证关键文件编码
- 测试模块导入功能
- 生成测试报告

---

## 预防措施

### 开发环境配置

**Git**:
```bash
git config core.quotepath off
git config gui.encoding utf-8
git config i18n.commit.encoding utf-8
git config i18n.logoutputencoding utf-8
```

**VS Code**:
```json
{
  "files.encoding": "utf8",
  "files.autoGuessEncoding": false,
  "files.candidateGuessEncodings": ["utf8"]
}
```

**EditorConfig**:
```ini
[*]
charset = utf-8
```

### CI/CD 集成
```yaml
- name: Check file encoding
  run: python encoding_fixer.py
```

---

## 修复记录

| 时间 | 事件 | 结果 |
|------|------|------|
| 2026-03-07 | commit 5505c09 尝试修复 47 个文件 | ❌ 失败 |
| 2026-03-08 | 使用逆向修复方法 | ✅ 成功修复 47+ 文件 |
| 2026-03-08 | 清理冗余脚本，更新技能文档 | ✅ 完成 |

**已修复文件**:
- `biliup/Danmaku/*.py` - 弹幕模块
- `biliup/common/*.py` - 通用模块
- `biliup/plugins/*.py` - 平台插件
- 总计 47+ 个文件

---

## 相关文件

| 文件 | 用途 | 状态 |
|------|------|------|
| `encoding_fixer.py` | 编码修复工具 | ✅ 可用 |
| `test_encoding_fix.py` | 编码测试工具 | ✅ 可用 |
| `PROJECT_INCOMPLETE.md` | 问题复盘 | ✅ 已更新 |
| `.claude/skills/encoding-checker/SKILL.md` | 可复用技能 | ✅ 已更新 |

---

## 使用建议

1. **定期检查**: 每月运行 `encoding_fixer.py`
2. **提交前检查**: 运行 `test_encoding_fix.py`
3. **环境统一**: 确保团队使用相同的编码配置
4. **CI 集成**: 在构建流程中添加编码检查
