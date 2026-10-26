import subprocess, time, urllib.request, json, sys

def biliup_running():
    out = subprocess.run("tasklist", capture_output=True, text=True, errors="replace", shell=True).stdout or ""
    for ln in out.splitlines():
        if "biliup.exe" in ln:
            return ln.split()[1]
    return None

def port_up():
    out = subprocess.run("netstat -ano", capture_output=True, text=True, errors="replace", shell=True).stdout or ""
    if ":19159" in out and "LISTENING" in out:
        for ln in out.splitlines():
            if ":19159" in ln and "LISTENING" in ln:
                return ln.split()[-1]
    return None

deadline = time.time() + 540  # 最多等 9 分钟（monitor 每 10 分钟触发）
print("[wait] 等待 monitor 计划任务拉起 biliup.exe ...", flush=True)
while time.time() < deadline:
    pid = biliup_running()
    p = port_up()
    if pid and p:
        print(f"[wait] biliup.exe 已运行 PID={pid} 端口={p}", flush=True)
        try:
            d = json.loads(urllib.request.urlopen("http://127.0.0.1:19159/v1/streamers", timeout=5).read().decode())
            print(f"[wait] API 返回 {len(d)} 个房间，部署验证通过", flush=True)
        except Exception as e:
            print(f"[wait] API 异常: {repr(e)[:100]}", flush=True)
        sys.exit(0)
    time.sleep(15)
print("[wait] 9 分钟内 monitor 未拉起（请手动检查 biliup-monitor 任务）", flush=True)
sys.exit(1)
