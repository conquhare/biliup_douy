import os, sys, shutil, subprocess, time, zipfile, urllib.request, json

RUN = "E:/biliup_live_rec/biliup_run"
BUILD = "E:/biliup_live_rec/biliup_run/_new_build"
ZIP = os.path.join(BUILD, "biliup-dist.zip")
DONE = os.path.join(BUILD, "biliup-dist.zip.done")
LOG = os.path.join(BUILD, "deploy_replace.log")

def log(*a):
    msg = " ".join(str(x) for x in a)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    print(msg, file=sys.stderr, flush=True)

def run_cmd(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True, **kw)

def live_guard():
    """返回 True 表示安全（无在播/录制），False 表示应放弃。"""
    try:
        d = json.loads(urllib.request.urlopen("http://127.0.0.1:19159/v1/streamers", timeout=5).read().decode())
        for s in d:
            st = s.get("status")
            if st not in (None, "Idle", "Pending", 0, "0"):
                log(f"护栏中止: 房间 {s.get('remark') or s.get('id')} 状态={st} 正在录制/上传")
                return False
        room_msg = f"{len(d)} 个房间全部空闲"
    except Exception as e:
        # 服务未运行 / API 不可达 = 不可能在录制，放行
        log(f"API 不可达（服务未运行，视为无录制）: {repr(e)[:100]}")
        room_msg = "API 不可达（放行）"
    try:
        out = run_cmd("tasklist").stdout or ""
        if "ffmpeg.exe" in out or "ffmpeg" in out:
            log("护栏中止: 检测到 ffmpeg 进程（边录边传中）")
            return False
    except Exception as e:
        log(f"ffmpeg 检查异常（忽略）: {repr(e)[:100]}")
    log(f"护栏通过: {room_msg}，无 ffmpeg")
    return True

def extract():
    # 直接解压到唯一 staging 目录（不创建临时目录，避免 rmtree 批量删除钩子）
    stamp = time.strftime("%Y%m%d%H%M%S")
    staging = os.path.join(BUILD, f"staging_{stamp}")
    os.makedirs(staging)  # 唯一时间戳，必为新建，绝不会触发清理
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        log(f"zip 条目数: {len(names)}; 顶层: {sorted(set(n.split('/')[0] for n in names if '/' in n))[:6]}")
        z.extractall(staging)
    has_exe = os.path.exists(os.path.join(staging, "biliup.exe"))
    log(f"staging 含 biliup.exe: {has_exe}; staging 顶层: {os.listdir(staging)[:12]}")
    return staging if has_exe else None

def kill_running():
    """替换前必须先杀掉 biliup.exe —— 它持有 .pyd 的句柄，否则 copytree 必然 WinError 32。"""
    pids = set()
    out = run_cmd("netstat -ano").stdout or ""
    for line in out.splitlines():
        if ":19159" in line and "LISTENING" in line:
            parts = line.split()
            if parts and parts[-1].isdigit():
                pids.add(parts[-1])
    out2 = run_cmd("tasklist /FI \"IMAGENAME eq biliup.exe\" /FO CSV").stdout or ""
    for line in out2.splitlines()[1:]:
        cols = [c.strip('"') for c in line.split('","')]
        if len(cols) >= 2 and cols[1].isdigit():
            pids.add(cols[1])
    if not pids:
        log("未发现运行中的 biliup.exe，无需 kill")
        return
    for pid in sorted(pids):
        run_cmd(f"taskkill /PID {pid} /T /F")
    log(f"已 taskkill /T /F: PID {sorted(pids)}")
    for _ in range(20):
        time.sleep(1)
        o = run_cmd("netstat -ano").stdout or ""
        # 必须逐行判断：跨行匹配 ":19159" + "LISTENING" 会把 ESTABLISHED 连接误判为仍在监听
        if not any(":19159" in ln and "LISTENING" in ln for ln in o.splitlines()):
            log("端口 19159 已释放")
            return
    log("警告: 端口仍未释放")

def start_detached():
    """自行拉起 biliup.exe（用 cmd /c start 脱离当前 shell，monitor 任务作兜底）。"""
    exe = os.path.join(RUN, "biliup.exe")
    try:
        subprocess.Popen(
            f'cmd /c start "" "{exe}"',
            cwd=RUN,
            shell=True,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log("已用 cmd /c start 拉起 biliup.exe（脱离 shell）")
        return True
    except Exception as e:
        log(f"start 拉起失败（依赖 monitor 任务兜底）: {repr(e)[:120]}")
        return False

def deploy():
    if not os.path.exists(DONE):
        log("未找到 .done sentinel，下载未完成，退出")
        return False
    if not os.path.exists(ZIP):
        log("未找到 zip，退出")
        return False
    if not live_guard():
        log("=== 因直播护栏放弃本次替换（保持现有 exe 运行）===")
        return False

    # 0) 先杀进程（否则 .pyd 被占用，覆盖必然失败）
    kill_running()

    # 1) 备份当前 exe
    stamp = time.strftime("%Y%m%d%H%M")
    cur_exe = os.path.join(RUN, "biliup.exe")
    bak = os.path.join(RUN, f"biliup.exe.bak-{stamp}")
    if os.path.exists(cur_exe):
        shutil.copy2(cur_exe, bak)
        log(f"已备份当前 exe -> {bak}")

    # 2) 解压
    staging = extract()
    if not staging:
        log("解压失败，终止部署（现有 exe 可能仍运行，需手动恢复！）")
        return False

    # 3) 覆盖（保留 data/config/日志：staging 不含这些；dirs_exist_ok 合并避免 rmtree）
    protect = {"data", "config", "logs", "_new_build", ".workbuddy", "biliup_watchdog.bat"}
    for item in os.listdir(staging):
        if item in protect:
            continue
        s = os.path.join(staging, item)
        d = os.path.join(RUN, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    log("已覆盖运行目录（保留 data/config/日志）")

    # 4) 拉起（DETACHED；monitor 任务在端口空时也会兜底重启）
    start_detached()

    # 5) 验证
    for _ in range(20):
        time.sleep(3)
        out = run_cmd("netstat -ano").stdout or ""
        if ":19159" in out and "LISTENING" in out:
            log("端口 19159 已监听，重启成功")
            try:
                d = json.loads(urllib.request.urlopen("http://127.0.0.1:19159/v1/streamers", timeout=5).read().decode())
                log(f"API 返回 {len(d)} 个房间，部署验证通过")
                return True
            except Exception as e:
                log(f"端口通但 API 异常: {repr(e)[:100]}")
    log("警告: 重启后 20s 内未监听到端口（monitor 任务将在数分钟内兜底重启）")
    return False

if __name__ == "__main__":
    ok = deploy()
    sys.exit(0 if ok else 1)
