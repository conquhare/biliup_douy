import subprocess, time, urllib.request, json, sys

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 必须绕开环境代理，否则 502

def sh(c):
    return subprocess.run(c, capture_output=True, text=True, errors="replace",
                          encoding="gbk", shell=True).stdout or ""

def biliup_running():
    for ln in sh("tasklist /FI \"IMAGENAME eq biliup.exe\" /FO CSV").splitlines():
        if "biliup.exe" in ln.lower():
            return ln.split(",")[1].strip('"')
    return None

def port_up():
    """逐行匹配，避免跨行把 ESTABLISHED/TIME_WAIT 误判成监听。"""
    for ln in sh("netstat -ano").splitlines():
        if ":19159" in ln and "LISTENING" in ln:
            return ln.split()[-1]
    return None

def api_ok():
    try:
        with OPENER.open("http://127.0.0.1:19159/v1/streamers", timeout=6) as r:
            return len(json.loads(r.read().decode()))
    except Exception:
        return None

def trigger_task():
    try:
        r = subprocess.run(["powershell", "-NonInteractive", "-NoProfile", "-Command",
                            "Start-ScheduledTask -TaskName biliup-monitor"],
                           capture_output=True, text=True, errors="replace", timeout=60)
        return r.returncode == 0
    except Exception:
        return False

deadline = time.time() + 540  # 最多等 9 分钟（monitor 每 10 分钟触发）
print("[wait] 等待 biliup.exe 拉起 ...", flush=True)
up = False
while time.time() < deadline:
    pid = biliup_running()
    if pid and port_up():
        n = api_ok()
        print(f"[wait] biliup.exe PID={pid} 端口={port_up()} API 房间数={n}", flush=True)
        if n:
            up = True
            break
    time.sleep(15)

if not up:
    print("[wait] 9 分钟内未拉起（请手动检查 biliup-monitor 任务）", flush=True)
    sys.exit(1)

# ⭐ 存活复检：`cmd /c start` 拉起的进程会在后台 shell 结束时被一起回收，
# 表现为「刚验证通过，几十秒后进程消失、端口只剩 TIME_WAIT」。
# 等 150s 后复查，若已被回收则改用任务计划重新拉起。
SURVIVE_WAIT = 150
print(f"[wait] 存活复检：{SURVIVE_WAIT}s 后确认进程仍在 ...", flush=True)
time.sleep(SURVIVE_WAIT)
for attempt in range(3):
    pid = biliup_running()
    if pid and port_up() and api_ok():
        print(f"[wait] 存活确认 OK PID={pid} 房间数={api_ok()}", flush=True)
        sys.exit(0)
    print(f"[wait] 第 {attempt + 1} 次复检发现进程已退出，改用任务计划重新拉起", flush=True)
    trigger_task()
    time.sleep(60)

print("[wait] 反复被回收，请人工介入", flush=True)
sys.exit(2)
