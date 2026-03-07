---
name: "proxy-troubleshooting"
description: "Diagnoses and fixes GitHub connection issues via proxy. Invoke when git push fails with 'failed to open socket' or GitHub access errors."
---

# GitHub 代理连接故障排查

当 GitHub 访问不通或 `git push` 失败时，使用此 Skill 快速诊断和修复代理连接问题。

## 快速诊断

### 第一步：执行测试脚本

项目已包含 `test-proxy.ps1` 脚本，直接执行：

```powershell
.\test-proxy.ps1
```

**脚本会自动检测：**
1. 代理端口（54350）是否监听
2. GitHub 访问是否正常
3. Git 连接是否成功
4. 自动配置代理设置

### 第二步：根据输出处理

#### 场景 A：代理端口未响应
```
✗ 代理端口 54350 未响应，请检查 Clash 是否运行
```

**解决方案：**
1. 检查 Clash 是否已启动
2. 检查 Clash 系统代理是否开启
3. 确认 Clash 端口配置（可能是 7890 而非 54350）
4. 修改 `test-proxy.ps1` 中的 `$proxyPort` 变量

#### 场景 B：GitHub 访问失败
```
✗ GitHub 访问失败: ...
```

**解决方案：**
```powershell
# 手动设置环境变量代理
$env:http_proxy = "http://127.0.0.1:54350"
$env:https_proxy = "http://127.0.0.1:54350"

# 或者设置 Git 代理
git config http.proxy http://127.0.0.1:54350
git config https.proxy http://127.0.0.1:54350
```

#### 场景 C：Git 连接失败
```
✗ Git 连接失败
尝试跳过 SSL 验证...
```

**脚本会自动尝试：**
```powershell
git config http.sslVerify false
```

如果仍然失败，检查：
- 远程仓库地址是否正确：`git remote -v`
- 网络是否完全断开
- 尝试切换 Clash 模式（全局/规则）

#### 场景 D：测试通过
```
✓ Git 连接正常
可以执行: git push
```

**直接执行：**
```powershell
git push origin master
```

## 手动排查步骤

如果脚本无法执行，按以下步骤手动排查：

### 1. 检查代理端口
```powershell
netstat -ano | findstr :54350
```

### 2. 测试 GitHub 连接
```powershell
$env:http_proxy = "http://127.0.0.1:54350"
curl -I https://github.com
```

### 3. 配置 Git 代理
```powershell
git config http.proxy http://127.0.0.1:54350
git config https.proxy http://127.0.0.1:54350
```

### 4. 测试 Git 连接
```powershell
git ls-remote origin HEAD
```

### 5. 推送代码
```powershell
git push origin master
```

## 常见错误及修复

| 错误信息 | 原因 | 修复方法 |
|---------|------|---------|
| `failed to open socket: Invalid arguments` | 代理未运行或配置错误 | 启动 Clash，检查端口 |
| `getaddrinfo() thread failed to start` | DNS 解析失败 | 检查网络连接，重启 Clash |
| `TLS connect error` | SSL 证书问题 | 禁用 SSL 验证或更新证书 |
| `non-fast-forward` | 远程有更新 | 先执行 `git pull` |

## 预防措施

### 推送前检查清单
```powershell
# 1. 执行测试脚本
.\test-proxy.ps1

# 2. 如果通过，执行推送
git push origin master
```

### 创建 Git 别名（可选）
```powershell
# 添加 push-with-proxy 别名
git config alias.pwp "!powershell -ExecutionPolicy Bypass -File .\test-proxy.ps1; if ($?) { git push }"

# 使用
git pwp
```

## 快速修复命令

```powershell
# 一键修复（PowerShell）
$env:http_proxy = "http://127.0.0.1:54350"
$env:https_proxy = "http://127.0.0.1:54350"
git config http.proxy http://127.0.0.1:54350
git config https.proxy http://127.0.0.1:54350
git push origin master
```

## 注意事项

1. **端口配置**：根据您的 Clash 配置，端口可能是 `7890`、`54350` 或其他
2. **SSL 验证**：禁用 `http.sslVerify` 会降低安全性，仅用于临时排查
3. **环境变量**：`$env:` 设置仅对当前 PowerShell 会话有效
4. **Git 配置**：`git config` 设置会持久保存到 `.git/config`
