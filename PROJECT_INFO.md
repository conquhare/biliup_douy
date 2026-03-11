# Biliup 直播录制上传工具 - 项目信息

> **文档用途**: 项目概述、开发进度和任务管理**更新日期**: 2026-03-08**相关文档**:
>
> - `PROJECT_KNOWLEDGE.md` - 编码问题技能库
> - `PROJECT_INCOMPLETE.md` - 问题复盘和经验总结
> - `FIX_SUMMARY.md` - 问题修复详细记录

---

## 项目概述

Biliup 是一个自动录制直播、弹幕、礼物的工具，支持直播结束后立刻上传先行版视频，视频审核通过后自动评论高能位置和醒目留言。

### 核心功能

- 自动录制直播、弹幕和礼物
- 直播结束立刻上传先行版视频

---

## 技术栈

### 后端

- **Rust** - 核心服务、API、下载管理
- **Python** - 弹幕录制、平台插件
- **SQLite** - 数据存储

### 前端

- **Next.js** - React 框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式

---

## 功能模块

### 1. 直播录制模块

- 多平台支持（抖音、B站等）
- 自动检测直播状态
- 分段录制管理
- 边录边传

### 2. 弹幕录制模块

- 弹幕类型过滤
- 礼物记录
- 高能区域检测

### 3. 视频处理模块

- 视频压制
- 弹幕渲染
- 高能进度条生成

### 4. 上传模块

- B站上传
- 分P管理
- 自动换源更新

### 5. 管理界面

- Web UI 管理
- 实时监控
- 配置管理

---

## 开发进度

### ✅ 已完成（2026年3月）

| 日期       | 任务                             | 说明                                                   |
| ---------- | -------------------------------- | ------------------------------------------------------ |
| 2026-03-09 | 前端弹幕配置集成                 | 在全局配置、抖音平台配置、主播单独配置中添加弹幕配置UI |
| 2026-03-09 | 弹幕配置联动逻辑                 | 实现主播配置 > 平台配置 > 全局配置的优先级继承         |
| 2026-03-09 | Rust配置结构更新                 | 在Config结构体中添加弹幕处理相关配置项                 |
| 2026-03-09 | 弹幕录制与处理功能               | 实现抖音直播弹幕录制、ASS字幕生成、视频合成、高能检测  |
| 2026-03-09 | 弹幕处理器架构                   | 创建 `DanmakuProcessor` 整合所有弹幕相关功能         |
| 2026-03-09 | ASS字幕生成器                    | 实现弹幕到ASS字幕格式的转换，支持自定义样式            |
| 2026-03-09 | 弹幕视频渲染                     | 使用FFmpeg将ASS字幕合成到视频中，支持GPU加速           |
| 2026-03-09 | 高能区域检测                     | 基于弹幕密度的滑动窗口算法检测高能时刻                 |
| 2026-03-09 | 抖音插件集成                     | 在分段录制后自动触发弹幕处理流程                       |
| 2026-03-08 | 修复 47+ 个 Python 文件编码问题  | 使用逆向修复方法成功修复所有乱码文件                   |
| 2026-03-08 | 清理冗余编码修复脚本             | 删除 3 个旧脚本，保留最优版本                          |
| 2026-03-08 | 更新编码修复技能文档             | 更新 `.claude/skills/encoding-checker/SKILL.md`      |
| 2026-03-06 | 修复直播录制页面状态标识显示问题 | 添加调试日志和默认状态处理                             |
| 2026-03-06 | 程序启动时自动检查录制配置       | 自动加载所有主播并开始监控                             |
| 2026-03-05 | 修复 Rust 源文件编码问题         | 修复 monitor.rs 等文件的乱码                           |
| 2026-03-03 | 修复直播状态显示问题             | 解决状态不一致问题，调整状态更新顺序                   |
| 2026-03-02 | 弹幕功能增强                     | 类型过滤配置、增强日志                                 |
| 2026-03-02 | HTTP/HTTPS 代理配置              | 支持配置文件和环境变量                                 |
| 2026-03-02 | Windows 启动脚本                 | 创建启动和开机启动脚本                                 |

### ⏳ 待办任务

#### 高优先级：代码中的 TODO/FIXME（7项）

| 文件                                             | 行号 | 类型  | 描述                                                   |
| ------------------------------------------------ | ---- | ----- | ------------------------------------------------------ |
| `biliup/engine/download.py`                    | 159  | TODO  | 无日志，需要添加日志记录                               |
| `biliup/engine/download.py`                    | 455  | FIXME | 下载时出现403，不会回到上层方法获取新链接              |
| `biliup/plugins/douyu.py`                      | 132  | HACK  | 构造 hs-h5 cdn 直播流链接（临时方案）                  |
| `biliup/plugins/twitcasting.py`                | 22   | TODO  | 参数传递过于繁琐                                       |
| `crates/biliup-cli/src/server/api/auth.rs`     | 37   | TODO  | 依赖 `auth_session.user` 和 `auth_session.backend` |
| `crates/biliup/Cargo.toml`                     | 21   | FIXME | 等 rsa 0.10.0 发布后再更新                             |
| `crates/stream-gears/stream_gears/pyobject.py` | 33   | FIXME | docstring 需要完善                                     |

#### 中优先级：功能增强（12项）

- [ ] 添加编码检查 CI 流程
- [X] 视频审核通过自动评论高能位置和醒目留言
- [X] 自动根据弹幕和礼物密度检测直播高能区域
- [X] 压制带有高能进度条、弹幕的视频（支持 Nvidia GPU nvenc 加速）
- [ ] 自动用换源方法更新高能弹幕版的视频
- [ ] 生成并上传醒目留言字幕
- [ ] 主播意外下播自动拼接
- [ ] 高能路牌自动提取最相关弹幕
- [X] 支持 HTTP 代理登录
- [ ] 自动切换更高分辨率
- [ ] 根据分辨率渲染弹幕
- [ ] 边录边修录播数据流格式问题
- [ ] 高能进度条视频生成（带可视化进度条）

#### 中优先级：功能增强建议（4项）

来自 `FIX_SUMMARY.md` 的后续优化建议：

- [ ] 状态值统一（前后端统一使用相同的状态值枚举）
- [ ] 错误处理增强（添加重试机制，加载失败时自动重试）
- [ ] 配置项添加（添加配置项控制是否启用自动加载）
- [ ] 性能优化（主播数量多时考虑分批加载）

---

## 配置文件示例

### 弹幕录制与处理配置

弹幕配置支持三级优先级：**主播单独配置 > 平台配置 > 全局配置**

#### 全局配置（空间配置页面）

```toml
# 抖音平台设置
[douyin]
douyin_danmaku = true              # 启用弹幕录制
douyin_danmaku_types = ["danmaku", "gift", "like"]  # 弹幕类型筛选

# 弹幕处理设置（适用于所有平台）
danmaku_generate_ass = true         # 生成ASS字幕
danmaku_ass_font = "Microsoft YaHei"  # 字幕字体
danmaku_ass_fontsize = 25         # 字体大小
danmaku_ass_color = "00FFFFFF"    # 字幕颜色(BGR)
danmaku_ass_speed = 8              # 弹幕速度(像素/帧)
danmaku_ass_line_count = 12        # 弹幕行数

danmaku_render_video = false       # 合成弹幕视频
danmaku_use_gpu = false           # 使用GPU加速
danmaku_video_codec = "libx264"   # 视频编码器
danmaku_preset = "medium"         # 编码预设
danmaku_crf = 23                  # 质量因子

danmaku_detect_energy = true       # 高能区域检测
danmaku_energy_window = 30        # 检测窗口(秒)
danmaku_energy_threshold = 0.7     # 高能阈值
danmaku_min_energy_duration = 10  # 最小持续时间(秒)
```

#### 主播单独配置（配置覆写）

在主播的「配置覆写」中可以覆盖全局配置：

```toml
[override]
douyin_danmaku = true
danmaku_generate_ass = true
danmaku_render_video = true
```

### 代理配置

```toml
[proxy]
# HTTP/HTTPS 代理设置
http_proxy = "http://127.0.0.1:7890"
https_proxy = "https://127.0.0.1:7890"
```

---

## CI/CD 构建配置

### 版本号管理策略

#### 独立版本号体系

由于本项目是 fork 自上游仓库，但做了大量自定义修改，因此采用**独立的版本号管理体系**，不沿用上游 Cargo.toml 的版本号。

**配置位置**: `.github/workflows/pyinstaller-publish.yml`

```yaml
env:
  # 独立版本号管理 - 不依赖上游 Cargo.toml
  # 修改此值来更新版本号
  BASE_VERSION: '0.2.0'
```

#### 版本号生成规则

1. **手动触发**: 使用输入的版本号（如 `v0.2.0`）
2. **自动触发**（推送到 master/main）: `v{BASE_VERSION}-{buildNumber}-g{shortSha}`
   - 示例: `v0.2.0-15-gabc1234`

#### 修改版本号步骤

1. 编辑 `.github/workflows/pyinstaller-publish.yml`
2. 修改 `BASE_VERSION` 的值
3. 提交并推送到 master 分支

#### 触发构建方式

**方式1: 推送到 master/main 分支**

```bash
git add .
git commit -m "更新代码"
git push
```

**方式2: 手动触发（推荐用于发布）**

1. 进入 GitHub 仓库页面 → Actions → Build Windows EXE
2. 点击 "Run workflow"
3. 输入版本号（如 `v0.2.0`）
4. 勾选 "创建 Release"（如需要）
5. 点击运行

#### 产物下载

构建完成后，可在以下位置下载：

1. **Actions 页面** → 具体运行记录 → Artifacts
2. **Release 页面**（如果创建了 Release）

---

## 编码规范（重要）

### 问题背景

项目曾发生严重的编码问题，导致 47+ 个文件出现乱码。现已修复并建立预防措施。

### 开发环境配置

**Git 配置**:

```bash
git config core.quotepath off
git config gui.encoding utf-8
git config i18n.commit.encoding utf-8
git config i18n.logoutputencoding utf-8
```

**VS Code 配置**:

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

### 编码检查工具

```bash
# 检测并修复编码问题
python encoding_fixer.py

# 验证修复结果
python test_encoding_fix.py
```

---

## 文档索引

| 文档                      | 用途               | 说明                         |
| ------------------------- | ------------------ | ---------------------------- |
| `PROJECT_INFO.md`       | 项目信息（本文档） | 项目概述、开发进度、任务管理 |
| `PROJECT_KNOWLEDGE.md`  | 编码问题技能库     | 快速解决 GBK/UTF-8 编码问题  |
| `PROJECT_INCOMPLETE.md` | 问题复盘           | 编码问题事件复盘和经验总结   |
| `FIX_SUMMARY.md`        | 问题修复总结       | 详细的问题描述和修复方案     |
| `CHANGELOG.md`          | 更新日志           | 版本更新记录                 |

---

## 任务统计

| 类别            | 总数         | 已完成       | 待处理       |
| --------------- | ------------ | ------------ | ------------ |
| 2026年3月修复   | 10           | 10           | 0            |
| 代码 TODO/FIXME | 7            | 0            | 7            |
| 编码规范相关    | 3            | 0            | 3            |
| 功能增强建议    | 4            | 0            | 4            |
| **总计**  | **24** | **10** | **14** |

---

**最后更新**: 2026-03-08
