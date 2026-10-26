# -*- coding: utf-8 -*-
"""
以 GBK 编码重写 biliuprun.bat。

⚠️ 该文件必须是 GBK(ANSI)：cmd 默认代码页 936，若存成 UTF-8，
   中文注释的字节会被 cmd 误解析，可能报「xxx 不是内部或外部命令」。
   因此不能用普通文本工具直接改写，必须按字节 encode('gbk') 写出。

改动要点：
  1. 去掉 UAC 提权（biliup.exe 不需要管理员；取消提权会导致直接不启动）
  2. 默认无代理裸启（注入 54350 会触发 B站 -611 风控 / ttwid 获取失败），
     仅当显式传 -Proxy 参数时才走代理
  3. 增加端口占用判断：19159 已在监听 → 提示已运行并退出，避免起冲突实例
     （守护任务 biliup-monitor 已 24/7 保活，重复启动会端口绑定失败）
"""
import io, os

BAT_LINES = [
    "@echo off",
    "chcp 936 >nul 2>&1",
    "setlocal",
    "",
    "REM ============================================================",
    "REM  biliup 启动器（手动重启用）",
    "REM",
    "REM  本文件必须是 GBK(ANSI) 编码！cmd 默认代码页 936，",
    "REM  存成 UTF-8 会让中文注释被误解析，可能报「不是内部或外部命令」。",
    "REM  如需修改，用 Python 按字节写：",
    "REM      io.open('x.bat','wb').write(s.encode('gbk'))",
    "REM",
    "REM  24/7 常驻由 Windows 任务计划 biliup-monitor 负责（每 10 分钟保活，",
    "REM  无代理裸启）。本脚本仅用于需要手动重启的场景。",
    "REM",
    "REM  可选参数：",
    "REM    -Proxy   走 127.0.0.1:54350 代理（不推荐，仅特殊需要时用）",
    "REM             已知问题：B站 -611 风控（代理 IP 异地登录）、",
    "REM             ttwid 获取失败、请求卡死",
    "REM    默认     无代理裸启（推荐，与看门狗 biliup_watchdog.bat 一致）",
    "REM ============================================================",
    "",
    "cd /D \"%~dp0\"",
    "",
    "echo.",
    "echo ============================================================",
    "echo   biliup 启动器",
    "echo ============================================================",
    "echo.",
    "",
    "REM ---- 前置检查：exe 是否存在 ----",
    "if not exist \"biliup.exe\" (",
    "    echo [错误] 找不到 biliup.exe",
    "    echo        当前目录：%CD%",
    "    echo        请确认本 bat 与 biliup.exe 在同一目录。",
    "    echo.",
    "    pause",
    "    goto :EOF",
    ")",
    "",
    "REM ---- 端口占用检查：已在运行则不再重复启动 ----",
    "REM  守护任务 biliup-monitor 常驻保活，重复启动会因 19159 被占而绑定失败。",
    "netstat -ano | findstr \":19159\" | findstr \"LISTENING\" >nul",
    "if %errorlevel%==0 (",
    "    echo [提示] biliup 已在运行（端口 19159 正在监听），无需重复启动。",
    "    echo.",
    "    echo   如需重启：先结束 biliup.exe 进程，再重新运行本脚本。",
    "    echo   常驻保活由任务计划 biliup-monitor 负责，无需手动干预。",
    "    echo.",
    "    pause",
    "    goto :EOF",
    ")",
    "",
    "REM ---- 启动方式 ----",
    "set \"PROXY_MODE=off\"",
    "if /I \"%1\"==\"-Proxy\" (",
    "    set \"PROXY_MODE=on\"",
    "    set \"HTTP_PROXY=http://127.0.0.1:54350\"",
    "    set \"HTTPS_PROXY=http://127.0.0.1:54350\"",
    "    set \"http_proxy=http://127.0.0.1:54350\"",
    "    set \"https_proxy=http://127.0.0.1:54350\"",
    ")",
    "",
    "echo   exe 路径  : %CD%\\biliup.exe",
    "if \"%PROXY_MODE%\"==\"on\" (",
    "    echo   启动方式  : 走代理 127.0.0.1:54350（不推荐）",
    ") else (",
    "    echo   启动方式  : 无代理裸启（推荐）",
    ")",
    "echo.",
    "echo [提示] 关闭本窗口即停止 biliup。",
    "echo        需要 24/7 常驻请交给任务计划 biliup-monitor。",
    "echo.",
    "",
    "biliup.exe",
    "",
    "echo.",
    "echo biliup 已退出。",
    "pause >nul",
    "endlocal",
]

path = r"E:\biliup_live_rec\biliup_run\biliuprun.bat"
content = "\r\n".join(BAT_LINES) + "\r\n"
with io.open(path, "wb") as f:
    f.write(content.encode("gbk"))

print("written:", path)
print("bytes:", os.path.getsize(path))
# 校验：按 GBK 读回，确认无乱码字符且编码自洽
with io.open(path, "r", encoding="gbk") as f:
    back = f.read()
print("gbk round-trip lines:", len(back.splitlines()))
for probe in ("biliup 启动器", "无代理裸启", "19159"):
    print(f"  probe {probe!r}: {probe in back}")
