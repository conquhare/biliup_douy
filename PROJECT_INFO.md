# Biliup 直播录制上传工具 - 项目信息

## 项目概述

Biliup 是一个自动录制直播、弹幕、礼物的工具，支持直播结束后立刻上传先行版视频，视频审核通过后自动评论高能位置和醒目留言。

### 核心功能
- 自动录制直播、弹幕和礼物
- 直播结束立刻上传先行版视频
- 视频审核通过自动评论高能位置和醒目留言
- 自动根据弹幕和礼物密度检测直播高能区域
- 压制带有高能进度条、弹幕的视频（支持 Nvidia GPU nvenc 加速）
- 自动用换源方法更新高能弹幕版的视频
- 生成并上传醒目留言字幕
- 主播意外下播自动拼接
- 高能路牌自动提取最相关弹幕
- 支持 HTTP 代理登录
- 自动切换更高分辨率
- 根据分辨率渲染弹幕
- 边录边修录播数据流格式问题

## 技术栈

### 后端
- **Rust** - 核心服务、API、下载管理
- **Python** - 弹幕录制、平台插件
- **SQLite** - 数据存储

### 前端
- **Next.js** - React 框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式

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

## 开发进度

### 已完成

#### 2026-03-03 修复直播状态显示问题
**问题**：直播结束后，前端界面仍然显示"直播中"状态，不会自动变为"空闲"

**根本原因**：
1. 下载任务完成时，`execute` 方法内部调用 `wake_waker` 将房间放回检测队列
2. `wake_waker` 调用 `push_back`，`push_back` 直接将状态设为 `Idle`
3. 但此时状态还是 `Working`（因为 `change_status` 只在切换出 `Working` 状态时停止任务）
4. 直接修改状态跳过了 `change_status` 的清理逻辑，导致状态不一致

**修复方案**：

**1. 修改 `push_back` 方法** ([monitor.rs](file:///e:/biliup_live_rec/biliup_code/crates/biliup-cli/src/server/core/monitor.rs)):
- 如果当前状态是 `Working`，拒绝放入队列，等待状态更新后再放入
- 添加日志记录状态变更

**2. 修改下载任务处理** ([download.rs](file:///e:/biliup_live_rec/biliup_code/crates/biliup-cli/src/server/common/download.rs)):
- 将 `wake_waker` 从 `execute` 方法内部移到外部
- 下载完成后，先调用 `change_status(Stage::Download, WorkerStatus::Idle)` 更新状态
- 然后再调用 `wake_waker` 将房间放回检测队列
- 确保状态更新和队列放入的顺序正确

**关键修改**:
```rust
// 下载完成后，将状态从 Working 改为 Idle
// 注意：必须先改变状态，再调用 wake_waker，否则 push_back 会拒绝放入队列
ctx.change_status(Stage::Download, WorkerStatus::Idle).await;

// 将房间放回检测队列
self.rooms_handle.wake_waker(ctx.worker_id()).await;
```

#### 2026-03-02 弹幕功能增强
- 弹幕类型过滤配置
- 增强弹幕录制日志
- 显示开始/结束录制消息
- 显示初始弹幕样本

#### 2026-03-02 HTTP/HTTPS 代理配置
- 支持配置文件设置代理
- 支持环境变量设置代理
- 自动检测系统代理

#### 2026-03-02 Windows 启动脚本
- 创建 `scripts/start_biliup.bat` 启动脚本
- 创建 `scripts/install_startup.bat` 开机启动安装脚本
- 支持日志记录和自动重启

## 配置文件

### 弹幕配置
```toml
[danmaku]
# 弹幕类型过滤，空数组表示不过滤
dm_types = ["emoticon", "common", "gift", "like", "social", "enter", "subscribe"]
```

### 代理配置
```toml
[proxy]
# HTTP/HTTPS 代理设置
http_proxy = "http://127.0.0.1:7890"
https_proxy = "https://127.0.0.1:7890"
```

#### 2026-03-05 修复 Rust 源文件编码问题
**问题**: `monitor.rs` 等 Rust 源文件出现乱码，中文注释显示为 `锟斤拷` 等乱码字符

**修复文件**:
- `crates/biliup-cli/src/server/core/monitor.rs` - 修复 50+ 处中文注释
- `crates/biliup-cli/src/server/config.rs` - 修复中文注释
- `crates/biliup-cli/src/server/common/download.rs` - 修复中文注释

**修复方法**:
1. 从 Git 历史中找到正确编码的版本（commit 3c9cc3f）
2. 逐行对比，只替换乱码的注释部分
3. 保留所有逻辑代码修改

**预防措施**:
- 已在 `.editorconfig` 中设置 `charset = utf-8`
- 已在 `PROJECT_KNOWLEDGE.md` 中记录编码问题解决方案
- 建议 VS Code 设置 `"files.encoding": "utf8"`

## 待完成任务

- [ ] 集成AI自动切片功能
- [ ] 优化API响应速度
- [ ] 完善错误处理机制
- [ ] 添加更多平台支持
- [ ] 优化存储空间管理
