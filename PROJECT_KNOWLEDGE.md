# 项目知识库

## GitHub 代理连接问题解决方案

### 问题现象
- `failed to open socket: Invalid arguments`
- `getaddrinfo() thread failed to start`
- `TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`

### 排查步骤

#### 1. 检查 Clash 是否运行
```powershell
# 检查 Clash 端口是否在监听（默认 7890 或 54350）
netstat -ano | findstr :54350
netstat -ano | findstr :7890
```

#### 2. 测试代理连接
```powershell
# 方法1: 使用 curl 测试
$env:http_proxy = "http://127.0.0.1:54350"
$env:https_proxy = "http://127.0.0.1:54350"
curl -I https://github.com

# 方法2: 使用 Invoke-WebRequest 测试
Invoke-WebRequest -Uri "https://github.com" -Proxy "http://127.0.0.1:54350" -Method HEAD

# 方法3: 测试 GitHub API
$env:http_proxy = "http://127.0.0.1:54350"
$env:https_proxy = "http://127.0.0.1:54350"
curl https://api.github.com
```

#### 3. 配置 Git 使用代理
```bash
# 设置代理
git config http.proxy http://127.0.0.1:54350
git config https.proxy http://127.0.0.1:54350

# 验证配置
git config --get http.proxy
git config --get https.proxy
```

#### 4. 如果代理不可用
- 检查 Clash 是否开启系统代理
- 尝试切换 Clash 模式（规则模式/全局模式）
- 重启 Clash 服务

### 预防措施

#### 使用现成的测试脚本
项目已包含 `test-proxy.ps1` 脚本，GitHub 不通时直接执行即可：

```powershell
# 快速测试代理和 GitHub 连接
.\test-proxy.ps1
```

**脚本功能**:
1. 测试代理端口（默认 54350）是否监听
2. 测试 GitHub 访问（HTTP 状态码）
3. 测试 Git 连接（自动配置代理）
4. 如连接失败，自动尝试禁用 SSL 验证

**使用方法**:
```powershell
# 在 PowerShell 中执行
.\test-proxy.ps1

# 如果测试通过，会提示可以执行 git push
```

#### 创建连接测试脚本（备用）
如果 `test-proxy.ps1` 不存在，可创建如下脚本：
```powershell
# 测试代理连接脚本
$proxyPort = 54350  # 根据实际情况修改

Write-Host "测试代理端口 $proxyPort..." -ForegroundColor Yellow
$connection = Test-NetConnection -ComputerName 127.0.0.1 -Port $proxyPort

if ($connection.TcpTestSucceeded) {
    Write-Host "✓ 代理端口连接正常" -ForegroundColor Green
    
    # 测试 GitHub 访问
    Write-Host "测试 GitHub 访问..." -ForegroundColor Yellow
    try {
        $env:http_proxy = "http://127.0.0.1:$proxyPort"
        $env:https_proxy = "http://127.0.0.1:$proxyPort"
        $response = Invoke-WebRequest -Uri "https://github.com" -Method HEAD -TimeoutSec 10
        Write-Host "✓ GitHub 访问正常 (HTTP $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "✗ GitHub 访问失败: $_" -ForegroundColor Red
    }
} else {
    Write-Host "✗ 代理端口 $proxyPort 未响应，请检查 Clash 是否运行" -ForegroundColor Red
}
```

#### Git 配置检查清单
```powershell
# 推送前检查清单
function Test-GitConnection {
    Write-Host "=== Git 连接测试 ===" -ForegroundColor Cyan
    
    # 1. 检查远程仓库
    Write-Host "`n1. 远程仓库配置:" -ForegroundColor Yellow
    git remote -v
    
    # 2. 检查代理设置
    Write-Host "`n2. Git 代理设置:" -ForegroundColor Yellow
    git config --get http.proxy
    git config --get https.proxy
    
    # 3. 测试连接
    Write-Host "`n3. 测试 GitHub 连接..." -ForegroundColor Yellow
    git ls-remote origin HEAD 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 连接正常" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ 连接失败，请检查网络或代理" -ForegroundColor Red
        return $false
    }
}
```

### 快速修复命令
```powershell
# 如果确认代理可用但 Git 无法连接，尝试以下命令：

# 1. 清除 Git 代理设置
git config --global --unset http.proxy
git config --global --unset https.proxy

# 2. 设置环境变量代理（当前会话有效）
$env:http_proxy = "http://127.0.0.1:54350"
$env:https_proxy = "http://127.0.0.1:54350"

# 3. 或者设置 Git 代理
git config http.proxy http://127.0.0.1:54350
git config https.proxy http://127.0.0.1:54350

# 4. 推送
git push
```

### 常见 Clash 端口
- HTTP 代理: `7890` 或 `54350`
- SOCKS5 代理: `7891` 或 `54351`

根据您的 Clash 配置选择正确的端口。

---

## GitHub Actions CI/CD 构建知识

### 版本号管理策略

#### 问题背景
- 本项目是 fork 自上游仓库，但做了大量自定义修改
- 不沿用上游 Cargo.toml 的版本号
- 需要独立的版本号管理体系

#### 解决方案
在 `.github/workflows/pyinstaller-publish.yml` 中使用 `env` 定义独立版本号：

```yaml
env:
  # 独立版本号管理 - 不依赖上游 Cargo.toml
  # 修改此值来更新版本号
  BASE_VERSION: '0.2.0'
```

#### 版本号生成规则
1. **手动触发**: 使用输入的版本号（如 `v0.2.0`）
2. **自动触发**: `v{BASE_VERSION}-{buildNumber}-g{shortSha}`
   - 示例: `v0.2.0-15-gabc1234`

#### 修改版本号步骤
1. 编辑 `.github/workflows/pyinstaller-publish.yml`
2. 修改 `BASE_VERSION` 的值
3. 提交并推送

### 构建流程

#### 完整构建步骤
1. **设置版本号** - 根据触发方式确定版本号
2. **更新 Cargo.toml** - 将版本号写入 Rust 配置
3. **构建前端** - `npm install && npm run build`
4. **构建 Rust 扩展** - 使用 maturin 构建 wheel
5. **构建 EXE** - 使用 PyInstaller 打包
6. **打包发布** - 创建 zip 压缩包
7. **上传产物** - 上传 Artifact
8. **创建 Release** - 可选，手动触发时创建

#### 关键配置
```yaml
# Node.js 版本 - 使用固定版本避免网络问题
node-version: '20'

# Python 版本
python-version: '3.x'

# Rust 工具链
uses: dtolnay/rust-toolchain@stable

# Maturin 构建
uses: PyO3/maturin-action@v1
with:
  command: build
  args: --release
```

### 常见问题排查

#### maturin 构建失败 (exit code 1)
**可能原因**:
- Cargo.toml 版本号格式错误
- Rust 代码编译错误
- 依赖项问题

**排查步骤**:
1. 检查 Cargo.toml 版本号格式是否正确
2. 本地运行 `maturin build --release` 测试
3. 检查 Rust 代码是否有语法错误

#### 版本号替换失败
**检查正则表达式**:
```powershell
$pattern = '(\[workspace\.package\]\s*\nversion\s*=\s*)"[^"]*"'
```

**验证方法**:
```powershell
# 本地测试版本号替换
$cargoToml = Get-Content Cargo.toml -Raw
$pattern = '(\[workspace\.package\]\s*\nversion\s*=\s*)"[^"]*"'
$replacement = '$1"0.2.0"'
$cargoToml -replace $pattern, $replacement
```

### 触发构建方式

#### 1. 推送到 master/main 分支
```bash
git add .
git commit -m "更新代码"
git push origin master
```

#### 2. 手动触发（带版本号）
1. 进入 GitHub 仓库页面
2. 点击 Actions → Build Windows EXE
3. 点击 "Run workflow"
4. 输入版本号（如 `v0.2.0`）
5. 选择是否创建 Release
6. 点击运行

### 产物下载
构建完成后，可在以下位置下载：
1. **Actions 页面** → 具体运行记录 → Artifacts
2. **Release 页面**（如果创建了 Release）

### 最佳实践

#### 版本号规范
- 使用语义化版本: `v主版本.次版本.修订号`
- 示例: `v0.2.0`, `v1.0.0`, `v2.1.3`

#### 发布流程
1. 更新 `BASE_VERSION`
2. 提交代码变更
3. 手动触发构建，输入新版本号
4. 勾选 "创建 Release"
5. 等待构建完成
6. 在 Release 页面查看并编辑发布说明

#### 调试技巧
```powershell
# 本地测试 PowerShell 脚本逻辑
$version = "v0.2.0-15-gabc1234"
$version = $version -replace '^v', ''
$version = $version -replace '-[a-f0-9]+$', ''
$version = $version -replace '-\d+$', ''
Write-Host "清理后的版本号: $version"
# 输出: 0.2.0
```

---

## 网络诊断工具

### 测试 GitHub 连接
```powershell
# 测试 DNS 解析
Resolve-DnsName github.com

# 测试端口连通性
Test-NetConnection -ComputerName github.com -Port 443

# 完整连接测试
curl -v https://github.com 2>&1 | Select-String "SSL|error|connected"
```

### 代理诊断
```powershell
# 查看系统代理设置
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyServer, ProxyEnable

# 查看环境变量
Get-ChildItem Env: | Where-Object { $_.Name -like "*proxy*" }

# 测试代理速度
Measure-Command { curl -s -o $null -w "%{http_code}" https://github.com }
```
