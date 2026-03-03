# GitHub Actions 工作流配置指南

## 工作流概述

本项目配置了完整的 CI/CD 工作流，包括以下功能：

### 1. Complete CI/CD (`complete-ci.yml`)
主要工作流，包含以下阶段：

| 阶段 | 说明 |
|------|------|
| 代码检查 | Rust fmt/clippy, Python Black/Ruff, ESLint |
| Rust 编译测试 | 多平台编译和单元测试 |
| Python 测试 | 多版本 Python 测试 |
| 覆盖率分析 | Rust + Python 代码覆盖率 |
| 前端构建 | Next.js 构建和测试 |
| 集成测试 | 完整功能测试 |
| 发布构建 | 多平台 Release 构建 |
| 通知 | 邮件、Telegram、Discord |

### 2. PR Check (`pr-check.yml`)
Pull Request 快速检查：
- PR 标题规范检查
- 代码格式检查
- 编译检查
- PR 大小检查
- 依赖安全检查

## 触发条件

### 自动触发
- **Push 到 main/master/develop 分支**: 运行完整 CI/CD
- **Pull Request**: 运行 PR Check
- **Tag 推送**: 构建并发布 Release

### 手动触发
在 Actions 页面选择工作流，点击 "Run workflow"

## 必需的环境变量

无需额外配置，工作流使用默认环境变量。

## 可选的 Secrets 配置

为了启用通知功能，需要在仓库 Settings → Secrets and variables → Actions 中添加：

### 代码覆盖率上传
```
CODECOV_TOKEN: Codecov 的 Token
```

### 邮件通知
```
SMTP_USERNAME: SMTP 用户名（如 Gmail 地址）
SMTP_PASSWORD: SMTP 密码或应用专用密码
NOTIFICATION_EMAIL: 接收通知的邮箱地址
```

### Telegram 通知
```
TELEGRAM_BOT_TOKEN: Telegram Bot Token
TELEGRAM_CHAT_ID: 聊天 ID（可以是用户 ID 或频道 ID）
```

### Discord 通知
```
DISCORD_WEBHOOK: Discord Webhook URL
```

## 缓存机制

工作流配置了多层缓存以提高执行效率：

1. **Rust 缓存**: 使用 `Swatinem/rust-cache@v2`
   - 缓存 Cargo 依赖和构建产物
   - 按平台和 job 类型分区

2. **pip 缓存**: 使用 `actions/cache@v4`
   - 缓存 Python 包
   - 基于 `pyproject.toml` 哈希

3. **Node 缓存**: 使用 `actions/setup-node@v4` 内置缓存
   - 缓存 `node_modules`
   - 基于 `package-lock.json`

## 测试报告

测试完成后，以下报告会自动生成并上传：

- **Pytest HTML 报告**: `pytest-report-{os}-py{version}.html`
- **覆盖率报告**: `coverage-report` (包含 Rust 和 Python)
- **前端构建产物**: `frontend-build`
- **Release 构建**: `release-{platform}`

## 故障排查

### 工作流失败常见原因

1. **代码格式错误**
   - 运行 `cargo fmt --all` 修复 Rust 格式
   - 运行 `black biliup/` 修复 Python 格式

2. **Clippy 警告**
   - 运行 `cargo clippy --fix` 自动修复

3. **测试失败**
   - 检查测试日志中的具体错误
   - 本地运行 `cargo test` 复现

4. **构建超时**
   - Release 构建可能需要较长时间
   - 检查是否启用了缓存

### 本地验证

在提交前，建议本地运行以下命令：

```bash
# Rust 检查
cargo fmt --all -- --check
cargo clippy --all-features --all-targets -- -D warnings
cargo test --workspace

# Python 检查
black --check biliup/
ruff check biliup/

# 前端检查
cd app
npm run lint
npm run build
```

## 自定义配置

### 修改触发分支
编辑工作流文件中的 `on.push.branches` 和 `on.pull_request.branches`

### 添加新的测试平台
在 `strategy.matrix` 中添加新的配置：

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest, your-new-platform]
```

### 跳过特定检查
在 commit message 中添加以下标记：
- `[skip ci]`: 跳过所有 CI
- `[skip actions]`: 跳过 Actions
- `[ci skip]`: 跳过 CI

## 性能优化建议

1. **合理使用缓存**: 缓存已配置，无需额外操作
2. **并行执行**: 各 job 已配置并行执行
3. **条件执行**: 使用 `if` 条件避免不必要的执行
4. **路径过滤**: 配置 `paths-ignore` 避免文档修改触发构建

## 安全注意事项

1. **Secrets 保护**: 不要在代码中硬编码敏感信息
2. **权限最小化**: 工作流使用最小权限原则
3. **依赖审查**: 定期运行安全检查和依赖更新

## 参考链接

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Rust Cache Action](https://github.com/Swatinem/rust-cache)
- [Codecov Action](https://github.com/codecov/codecov-action)
