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

#### 创建连接测试脚本
创建 `test-proxy.ps1`:
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
