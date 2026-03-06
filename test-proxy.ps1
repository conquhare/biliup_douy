# 测试代理连接脚本
$proxyPort = 54350  # 根据实际情况修改

Write-Host "测试代理端口 $proxyPort..." -ForegroundColor Yellow
$connection = Test-NetConnection -ComputerName 127.0.0.1 -Port $proxyPort

if ($connection.TcpTestSucceeded) {
    Write-Host "✓ 代理端口连接正常" -ForegroundColor Green
    
    # 测试 GitHub 访问（跳过证书验证）
    Write-Host "测试 GitHub 访问..." -ForegroundColor Yellow
    try {
        # 方法1: 使用 curl 并跳过证书验证
        $env:http_proxy = "http://127.0.0.1:$proxyPort"
        $env:https_proxy = "http://127.0.0.1:$proxyPort"
        
        # 使用 curl 的 -k 参数跳过证书验证
        $result = curl -k -s -o nul -w "%{http_code}" https://github.com 2>$null
        
        if ($result -eq "200" -or $result -eq "301" -or $result -eq "302") {
            Write-Host "✓ GitHub 访问正常 (HTTP $result)" -ForegroundColor Green
        } else {
            Write-Host "⚠ GitHub 返回状态码: $result" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "✗ GitHub 访问失败: $_" -ForegroundColor Red
    }
    
    # 测试 Git 连接
    Write-Host "`n测试 Git 连接..." -ForegroundColor Yellow
    git config http.proxy "http://127.0.0.1:$proxyPort" 2>$null
    git config https.proxy "http://127.0.0.1:$proxyPort" 2>$null
    
    # 尝试获取远程信息
    $gitTest = git ls-remote origin HEAD 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Git 连接正常" -ForegroundColor Green
        Write-Host "`n可以执行: git push" -ForegroundColor Cyan
    } else {
        Write-Host "✗ Git 连接失败" -ForegroundColor Red
        Write-Host "尝试跳过 SSL 验证..." -ForegroundColor Yellow
        git config http.sslVerify false
        $gitTest2 = git ls-remote origin HEAD 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Git 连接正常 (已禁用 SSL 验证)" -ForegroundColor Green
            Write-Host "`n可以执行: git push" -ForegroundColor Cyan
        } else {
            Write-Host "✗ Git 仍然无法连接" -ForegroundColor Red
        }
    }
} else {
    Write-Host "✗ 代理端口 $proxyPort 未响应，请检查 Clash 是否运行" -ForegroundColor Red
}
