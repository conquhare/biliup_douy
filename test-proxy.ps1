# 测试代理连接脚本
param(
    [switch]$SwitchGit  # 切换 Git Remote URL
)

$proxyPort = 54350  # 根据实际情况修改

$gitUrls = @{
    "GitHub" = "https://github.com/conquhare/biliup_douy.git"
    "GitCode" = "https://gitcode.com/codergith_hbuid/biliup_douy.git"
}

function Switch-GitRemote {
    $currentUrl = git remote get-url origin 2>$null
    if (-not $currentUrl) {
        Write-Host "✗ 未找到 origin remote" -ForegroundColor Red
        return
    }
    
    Write-Host "`n当前 Remote URL:" -ForegroundColor Cyan
    Write-Host "  $currentUrl" -ForegroundColor White
    
    $targetPlatform = ""
    $targetUrl = ""
    
    if ($currentUrl -match "github\.com") {
        $targetPlatform = "GitCode"
        $targetUrl = $gitUrls["GitCode"]
    } elseif ($currentUrl -match "gitcode\.com") {
        $targetPlatform = "GitHub"
        $targetUrl = $gitUrls["GitHub"]
    } else {
        Write-Host "✗ 未知的 remote URL 格式" -ForegroundColor Red
        return
    }
    
    Write-Host "`n即将切换到 $targetPlatform :" -ForegroundColor Yellow
    Write-Host "  $targetUrl" -ForegroundColor White
    
    git remote set-url origin $targetUrl
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 已切换到 $targetPlatform" -ForegroundColor Green
        $newUrl = git remote get-url origin
        Write-Host "  当前 URL: $newUrl" -ForegroundColor Cyan
    } else {
        Write-Host "✗ 切换失败" -ForegroundColor Red
    }
}

if ($SwitchGit) {
    Switch-GitRemote
    return
}

Write-Host "测试代理端口 $proxyPort..." -ForegroundColor Yellow
$connection = Test-NetConnection -ComputerName 127.0.0.1 -Port $proxyPort

if ($connection.TcpTestSucceeded) {
    Write-Host "✓ 代理端口连接正常" -ForegroundColor Green
    
    # 显示当前 Git Remote
    $currentUrl = git remote get-url origin 2>$null
    if ($currentUrl) {
        $platform = if ($currentUrl -match "github\.com") { "GitHub" } elseif ($currentUrl -match "gitcode\.com") { "GitCode" } else { "未知" }
        Write-Host "`n当前 Git Remote: [$platform]" -ForegroundColor Cyan
        Write-Host "  $currentUrl" -ForegroundColor White
    }
    
    # 测试 GitHub 访问（跳过证书验证）
    Write-Host "`n测试 GitHub 访问..." -ForegroundColor Yellow
    try {
        $env:http_proxy = "http://127.0.0.1:$proxyPort"
        $env:https_proxy = "http://127.0.0.1:$proxyPort"
        
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
    
    Write-Host "`n提示: 使用 -SwitchGit 参数可在 GitHub/GitCode 之间切换" -ForegroundColor DarkGray
} else {
    Write-Host "✗ 代理端口 $proxyPort 未响应，请检查 Clash 是否运行" -ForegroundColor Red
}
