# -*- coding: utf-8 -*-
"""验证 biliuprun.bat：编码正确性 + 端口占用判断分支行为。

安全说明：全程不启动真实的 biliup.exe。
  - 测试1：把 bat 复制到不含 biliup.exe 的临时目录运行 → 应命中「找不到 biliup.exe」分支，
           同时验证 cmd 能正确解析中文注释（编码正确则无「不是内部或外部命令」报错）。
  - 测试2：独立测试 bat 只跑 netstat|findstr 判断，不启动任何程序。
"""
import io, os, subprocess, tempfile, sys

BAT = r"E:\biliup_live_rec\biliup_run\biliuprun.bat"
raw = open(BAT, "rb").read()

print("=== 1) 编码验证 ===")
print("  字节数:", len(raw))
print("  含 UTF-8 BOM:", raw[:3] == b"\xef\xbb\xbf")
try:
    raw.decode("utf-8")
    print("  可解为 UTF-8: True  <-- 若同时是 GBK 中文，说明存错了编码！")
except UnicodeDecodeError:
    print("  可解为 UTF-8: False（符合预期：这是 GBK，不是 UTF-8）")
try:
    txt = raw.decode("gbk")
    print("  可解为 GBK: True")
    print("  CRLF 行尾:", b"\r\n" in raw)
except UnicodeDecodeError as e:
    print("  GBK 解码失败:", e)
    sys.exit(1)

# 关键中文是否完好（乱码则说明编码写错）
probes = ["biliup 启动器", "无代理裸启", "已在运行", "找不到 biliup.exe", "不推荐"]
for p in probes:
    print(f"  中文探针 {p!r}: {'OK' if p in txt else '缺失'}")

print()
print("=== 2) cmd 解析测试（临时目录，无 biliup.exe）===")
tmp = tempfile.mkdtemp(prefix="biliuprun_test_")
test_bat = os.path.join(tmp, "biliuprun.bat")
with open(test_bat, "wb") as f:
    f.write(raw)  # 原样复制（GBK）
# stdin 重定向到 NUL，让 pause 立即返回
r = subprocess.run(
    [test_bat],
    cwd=tmp,
    shell=True,
    stdin=subprocess.DEVNULL,
    capture_output=True,
    text=True,
    errors="replace",
    timeout=60,
)
out = r.stdout or ""
print("  退出码:", r.returncode)
print("  命中「找不到 biliup.exe」:", "找不到 biliup.exe" in out)
print("  cmd 编码报错（不该出现）:", ("不是内部或外部命令" in out) or ("命令语法不正确" in out))
print("  --- 输出片段 ---")
for ln in out.splitlines()[:14]:
    print("   ", ln)

print()
print("=== 3) 端口占用判断分支测试（独立 bat，不启动任何程序）===")
guard_bat = os.path.join(tmp, "guard_test.bat")
with open(guard_bat, "w", encoding="gbk", newline="\r\n") as f:
    f.write(
        "@echo off\r\n"
        'netstat -ano | findstr ":19159" | findstr "LISTENING" >nul\r\n'
        "if %errorlevel%==0 (echo GUARD_HIT_RUNNING) else (echo GUARD_PASS_START)\r\n"
    )
r2 = subprocess.run(
    [guard_bat], cwd=tmp, shell=True, stdin=subprocess.DEVNULL,
    capture_output=True, text=True, errors="replace", timeout=60,
)
out2 = (r2.stdout or "").strip()
print("  当前 biliup 实际在跑（19159 监听）→ 期望 GUARD_HIT_RUNNING")
print("  实际输出:", out2)
print("  结论:", "端口判断正确（会阻止重复启动）" if out2 == "GUARD_HIT_RUNNING"
      else ("端口判断未命中，需排查" if out2 == "GUARD_PASS_START" else "异常输出"))

# 清理临时目录（仅删本次创建的空目录文件，非用户数据）
for fn in ("biliuprun.bat", "guard_test.bat"):
    p = os.path.join(tmp, fn)
    if os.path.exists(p):
        os.remove(p)
try:
    os.rmdir(tmp)
except OSError:
    pass
print()
print("临时测试目录已清理:", tmp)
