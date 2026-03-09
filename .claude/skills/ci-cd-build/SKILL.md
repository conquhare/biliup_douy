---
name: "ci-cd-build"
description: "CI/CD 构建流程指南，包含 Windows EXE 构建、版本号管理和发布流程"
---

# CI/CD 构建技能

## 适用场景

**当需要以下操作时使用此技能：**
1. 触发 Windows EXE 构建
2. 更新版本号
3. 排查构建失败问题
4. 配置 GitHub Actions
5. 发布新版本

## 构建配置

### 工作流文件

```yaml
# .github/workflows/pyinstaller-publish.yml
name: Build Windows EXE

on:
  push:
    branches: [master, main]
  workflow_dispatch:
    inputs:
      version:
        description: '版本号 (如 v0.2.0)'
        required: true
      create_release:
        description: '创建 Release'
        type: boolean
        default: false

env:
  BASE_VERSION: '0.2.0'  # 修改此值更新版本号
```

### 版本号管理

#### 独立版本号体系

本项目采用**独立的版本号管理体系**：

```yaml
env:
  # 独立版本号管理 - 不依赖上游 Cargo.toml
  BASE_VERSION: '0.2.0'
```

#### 版本号生成规则

1. **手动触发**: 使用输入的版本号（如 `v0.2.0`）
2. **自动触发**: `v{BASE_VERSION}-{buildNumber}-g{shortSha}`
   - 示例: `v0.2.0-15-gabc1234`

#### 修改版本号

```bash
# 1. 编辑工作流文件
vim .github/workflows/pyinstaller-publish.yml

# 2. 修改 BASE_VERSION
env:
  BASE_VERSION: '0.3.0'  # 新版本号

# 3. 提交并推送
git add .github/workflows/pyinstaller-publish.yml
git commit -m "Bump version to 0.3.0"
git push origin master
```

## 触发构建

### 方式1：推送到主分支

```bash
git add .
git commit -m "更新代码"
git push origin master
```

构建会自动触发，版本号为 `v0.2.0-{buildNumber}-g{shortSha}`

### 方式2：手动触发（推荐用于发布）

1. 进入 GitHub 仓库页面 → Actions → Build Windows EXE
2. 点击 "Run workflow"
3. 输入版本号（如 `v0.2.0`）
4. 勾选 "创建 Release"（如需要）
5. 点击运行

### 方式3：使用 GitHub CLI

```bash
# 触发工作流
gh workflow run pyinstaller-publish.yml \
  -f version=v0.2.0 \
  -f create_release=true
```

## 构建流程

### 完整构建步骤

```yaml
jobs:
  build:
    runs-on: windows-latest
    steps:
      # 1. 检出代码
      - uses: actions/checkout@v3
      
      # 2. 设置 Python
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      # 3. 设置 Rust
      - uses: dtolnay/rust-action@stable
      
      # 4. 安装依赖
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      
      # 5. 构建前端
      - name: Build frontend
        run: |
          cd app
          npm install
          npm run build
      
      # 6. 构建 Rust
      - name: Build Rust
        run: cargo build --release
      
      # 7. 打包 EXE
      - name: Build EXE
        run: pyinstaller biliup.spec
      
      # 8. 上传产物
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: biliup-windows
          path: dist/biliup.exe
```

## 获取构建产物

### 方式1：Actions 页面

1. 进入 GitHub 仓库 → Actions
2. 找到最近的构建记录
3. 点击 Artifacts 下载 `biliup-windows`

### 方式2：Release 页面

如果勾选了 "创建 Release"：

1. 进入 GitHub 仓库 → Releases
2. 找到对应版本
3. 下载 `biliup.exe`

### 方式3：使用 GitHub CLI

```bash
# 下载最新构建产物
gh run download -n biliup-windows

# 下载特定版本的 Release
gh release download v0.2.0 -p '*.exe'
```

## 调试构建失败

### 1. 查看构建日志

在 Actions 页面点击失败的构建，查看详细日志。

### 2. 常见错误

#### 错误："No module named 'xxx'"
**原因**：依赖未安装  
**解决**：在 `requirements.txt` 中添加缺失的依赖

#### 错误："Rust compilation failed"
**原因**：Rust 代码编译错误  
**解决**：
```bash
# 本地测试编译
cargo build --release
```

#### 错误："npm install failed"
**原因**：前端依赖问题  
**解决**：
```bash
cd app
rm -rf node_modules package-lock.json
npm install
```

#### 错误："PyInstaller failed"
**原因**：打包配置问题  
**解决**：
```bash
# 本地测试打包
pyinstaller biliup.spec
```

### 3. 本地模拟构建

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 3. 构建前端
cd app && npm install && npm run build

# 4. 构建 Rust
cargo build --release

# 5. 打包
pyinstaller biliup.spec
```

## 发布流程

### 创建 Release

```bash
# 1. 确保代码已提交
git push origin master

# 2. 创建标签
git tag v0.2.0
git push origin v0.2.0

# 3. 创建 Release（使用 GitHub CLI）
gh release create v0.2.0 \
  --title "v0.2.0" \
  --notes "Release notes here" \
  dist/biliup.exe
```

### 自动生成 Release Notes

```bash
# 使用 GitHub CLI 自动生成
gh release create v0.2.0 \
  --generate-notes \
  dist/biliup.exe
```

## 高级配置

### 多平台构建

```yaml
strategy:
  matrix:
    os: [windows-latest, ubuntu-latest, macos-latest]
    
jobs:
  build:
    runs-on: ${{ matrix.os }}
    steps:
      # ... 构建步骤
```

### 缓存依赖

```yaml
- uses: actions/cache@v3
  with:
    path: |
      ~/.cargo/registry
      ~/.cargo/git
      target
    key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
```

### 条件构建

```yaml
# 只在特定文件变更时触发
on:
  push:
    paths:
      - 'biliup/**'
      - 'crates/**'
      - '.github/workflows/**'
```

## 相关文件

- `.github/workflows/pyinstaller-publish.yml` - 构建工作流
- `biliup.spec` - PyInstaller 配置
- `requirements.txt` - Python 依赖
- `Cargo.toml` - Rust 配置

## 参考资源

- [GitHub Actions 文档](https://docs.github.com/actions)
- [PyInstaller 文档](https://pyinstaller.readthedocs.io/)
- [GitHub CLI 文档](https://cli.github.com/manual/)
