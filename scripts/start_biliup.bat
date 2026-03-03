@echo off
chcp 65001 >nul
title Biliup 直播录制上传工具

:: ============================================
:: Biliup Windows 启动脚本
:: 功能：启动 biliup 服务，支持自动重启和日志记录
:: 使用方式：
::   1. 直接双击运行
::   2. 添加到 Windows 开机启动项
::   3. 使用任务计划程序定时启动
:: ============================================

:: 设置工作目录为脚本所在目录的父目录（项目根目录）
cd /d "%~dp0\.."

:: 设置环境变量
set "BILIUP_HOME=%CD%"
set "PATH=%PATH%;%BILIUP_HOME%"

:: 日志目录
set "LOG_DIR=%BILIUP_HOME%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 获取当前日期时间作为日志文件名
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value ^| find "="') do set "dt=%%a"
set "LOG_FILE=%LOG_DIR%\biliup_%dt:~0,8%_%dt:~8,6%.log"

echo ============================================
echo    Biliup 直播录制上传工具
echo ============================================
echo 工作目录: %BILIUP_HOME%
echo 日志文件: %LOG_FILE%
echo 启动时间: %date% %time%
echo ============================================
echo.

:: 检查配置文件是否存在
if not exist "%BILIUP_HOME%\config.yaml" (
    if not exist "%BILIUP_HOME%\config.toml" (
        echo [警告] 未找到配置文件 config.yaml 或 config.toml
        echo 请确保配置文件存在于: %BILIUP_HOME%
        echo.
        pause
        exit /b 1
    )
)

:: 检查可执行文件
set "BILIUP_EXE="
if exist "%BILIUP_HOME%\biliup.exe" (
    set "BILIUP_EXE=biliup.exe"
) else if exist "%BILIUP_HOME%\target\release\biliup.exe" (
    set "BILIUP_EXE=target\release\biliup.exe"
) else if exist "%BILIUP_HOME%\target\debug\biliup.exe" (
    set "BILIUP_EXE=target\debug\biliup.exe"
)

if "!BILIUP_EXE!"=="" (
    echo [错误] 未找到 biliup 可执行文件
    echo 请确保已编译项目或下载了预编译版本
    echo.
    pause
    exit /b 1
)

echo [信息] 使用可执行文件: %BILIUP_EXE%
echo [信息] 正在启动服务...
echo.

:: 启动服务并记录日志
:START

echo [%date% %time%] 正在启动 biliup 服务... >> "%LOG_FILE%"

"%BILIUP_HOME%\%BILIUP_EXE%" server >> "%LOG_FILE%" 2>&1

set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] 服务已退出，退出码: %EXIT_CODE% >> "%LOG_FILE%"

:: 检查是否需要自动重启
if %EXIT_CODE% equ 0 (
    echo [信息] 服务正常退出
    goto :END
)

:: 非零退出码，等待后重启
echo [警告] 服务异常退出，5秒后自动重启...
echo [%date% %time%] 服务异常退出，准备重启... >> "%LOG_FILE%"
timeout /t 5 /nobreak >nul
goto :START

:END
echo.
echo ============================================
echo 服务已停止
echo 日志文件: %LOG_FILE%
echo ============================================
pause
