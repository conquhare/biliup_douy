@echo off
chcp 65001 >nul
title Biliup 开机启动安装

:: ============================================
:: Biliup Windows 开机启动安装脚本
:: 功能：将 biliup 添加到 Windows 开机启动项
:: ============================================

cd /d "%~dp0"

set "STARTUP_NAME=Biliup直播录制工具"
set "SCRIPT_PATH=%~dp0start_biliup.bat"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo ============================================
echo    Biliup 开机启动安装程序
echo ============================================
echo.

:: 检查脚本文件是否存在
if not exist "%SCRIPT_PATH%" (
    echo [错误] 未找到启动脚本: %SCRIPT_PATH%
    echo 请确保 start_biliup.bat 与此脚本在同一目录
    pause
    exit /b 1
)

:: 创建快捷方式
echo [信息] 正在创建开机启动快捷方式...

:: 使用 PowerShell 创建快捷方式
powershell -Command "
$WshShell = New-Object -comObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%STARTUP_FOLDER%\%STARTUP_NAME%.lnk');
$Shortcut.TargetPath = '%SCRIPT_PATH%';
$Shortcut.WorkingDirectory = '%~dp0..';
$Shortcut.IconLocation = '%SystemRoot%\System32\shell32.dll, 14';
$Shortcut.Description = 'Biliup 直播录制上传工具';
$Shortcut.Save();
"

if %ERRORLEVEL% neq 0 (
    echo [错误] 创建快捷方式失败
    pause
    exit /b 1
)

echo [成功] 已添加到开机启动项
echo.
echo 快捷方式位置: %STARTUP_FOLDER%\%STARTUP_NAME%.lnk
echo 启动脚本位置: %SCRIPT_PATH%
echo.
echo ============================================
echo 安装完成！系统启动时将自动运行 biliup
echo ============================================
echo.

:: 询问是否立即启动
set /p START_NOW="是否立即启动 biliup? (Y/N): "
if /i "%START_NOW%"=="Y" (
    echo.
    echo [信息] 正在启动 biliup...
    start "" "%SCRIPT_PATH%"
)

echo.
pause
