# Biliup 项目知识库

## 配置系统架构

### 配置存储位置
- **数据库**: `data/data.sqlite3`
- **表**: `configuration`
- **格式**: JSON 字符串存储在 `value` 字段中

### 配置结构

#### 后端配置结构 (`crates/biliup-cli/src/server/config.rs`)
```rust
pub struct Config {
    // 全局下载设置
    pub downloader: Option<DownloaderType>,
    pub file_size: u64,
    pub segment_time: Option<String>,
    pub filtering_threshold: u64,
    
    // 全局上传设置
    pub lines: String,
    pub threads: u32,
    pub delay: u64,
    pub event_loop_interval: u64,
    pub checker_sleep: u64,
    pub pool1_size: u32,
    pub pool2_size: u32,
    
    // 代理设置 (新增)
    pub http_proxy: Option<String>,
    pub https_proxy: Option<String>,
    
    // 平台特定设置
    pub douyin_danmaku: Option<bool>,
    pub douyin_danmaku_types: Option<Vec<String>>,  // 新增
    pub douyin_quality: Option<String>,
    
    // 主播配置
    pub streamers: HashMap<String, StreamerConfig>,
}
```

#### 前端配置页面
- **主页面**: `app/(app)/dashboard/page.tsx`
- **全局设置组件**: `app/ui/plugins/global.tsx`
- **平台设置组件**: `app/ui/plugins/*.tsx`

### 添加新配置项步骤

1. **后端配置结构** (`config.rs`):
   ```rust
   #[serde(default)]
   pub new_field: Option<String>,
   ```

2. **前端全局配置** (`global.tsx`):
   ```tsx
   <Form.Input
     field="new_field"
     label="新字段名"
     extraText="字段说明"
     style={{ width: '100%' }}
   />
   ```

3. **前端平台配置** (如 `douyin.tsx`):
   ```tsx
   <Form.Select
     field="douyin_new_field"
     label="新字段"
     multiple  // 如果是多选
   >
     <Select.Option value="option1">选项1</Select.Option>
   </Form.Select>
   ```

### 配置数据流

```
Web UI (React Form)
    ↓ (submit)
API Endpoint (/v1/configuration)
    ↓ (PUT)
Database (SQLite)
    ↓ (JSON parse)
Config Struct (Rust)
    ↓ (use)
Download Manager / Uploader
```

### 配置热重载

- **触发条件**: 调用 `/v1/configuration/reload` API
- **检测间隔**: 每分钟检查一次系统状态
- **安全条件**: 只有在无录制和上传任务时才能重载
- **自动重启**: 配置 `auto_restart = true` 时，空闲自动重启

### 重要配置项说明

| 配置项 | 说明 | 生效方式 |
|--------|------|----------|
| `event_loop_interval` | 平台检测间隔 | 重载配置 |
| `checker_sleep` | 单个主播检测间隔 | 重载配置 |
| `delay` | 下播延迟检测 | 重载配置 |
| `pool1_size` | 下载线程池大小 | 重启程序 |
| `pool2_size` | 上传线程池大小 | 重启程序 |
| `http_proxy` | HTTP代理 | 即时生效 |
| `https_proxy` | HTTPS代理 | 即时生效 |

## 状态管理

### 工作器状态 (WorkerStatus)
```rust
pub enum WorkerStatus {
    Working(Arc<DownloadTask>),  // 正在录制
    Pending,                      // 等待检测
    Idle,                         // 空闲
    Pause,                        // 暂停
}
```

### 状态流转
```
Idle → Pending → Working → Idle
              ↓
            Pause
```

### 状态更新机制
1. **monitor.rs**: 检测直播状态，控制 `Pending` → `Working`
2. **download.rs**: 下载任务完成，控制 `Working` → `Idle`
3. **endpoints.rs**: API 调用控制暂停/恢复

## 常见问题

### 配置项不显示在前端
**原因**: 只修改了后端配置结构，未添加前端表单字段
**解决**: 在对应的 `app/ui/plugins/*.tsx` 中添加 Form 组件

### 配置保存后未生效
**原因**: 部分配置需要重载或重启才能生效
**解决**: 
- 点击"重载配置"按钮
- 或设置 `auto_restart = true` 等待自动重启
- 或手动重启程序

### 直播状态显示不正确
**原因**: 状态更新顺序问题
**解决**: 确保 `change_status` 在 `wake_waker` 之前调用

## 文件编码问题

### 问题描述
Windows 环境下文件容易出现 GBK/GB2312 编码，导致：
- Rust 编译失败: `stream did not contain valid UTF-8`
- 前端页面显示乱码（如"锟斤拷"或"??"）
- 日志输出乱码

### 根本原因
- Windows 默认使用 GBK 编码
- Rust 和现代前端工具链要求 UTF-8
- 文件在不同编辑器间复制时编码可能改变

### 从 Git 历史恢复乱码文件
当文件出现乱码时，可以从 Git 历史中找到正确编码的版本：

```bash
# 查看文件历史
git log --oneline -- crates/biliup-cli/src/server/core/monitor.rs

# 获取特定版本的文件内容
git show 3c9cc3f:crates/biliup-cli/src/server/core/monitor.rs > monitor_fixed.rs

# 对比当前版本和正确版本
git diff HEAD 3c9cc3f -- crates/biliup-cli/src/server/core/monitor.rs
```

**注意事项**:
- 不要直接替换整个文件，可能丢失最新的逻辑修改
- 应该逐行对比，只替换乱码的注释部分
- 使用 `SearchReplace` 工具精确替换，保留代码逻辑

### 预防措施
1. **配置编辑器**: VS Code 设置 `"files.encoding": "utf8"`
2. **配置 Git**: `git config core.quotepath off`
3. **EditorConfig**: 项目根目录创建 `.editorconfig` 设置 `charset = utf-8`
