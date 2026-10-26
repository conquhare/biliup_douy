# -*- coding: utf-8 -*-
"""CI 完成 → 下载产物 → 直播护栏 → 部署新 exe → 等 monitor 拉起 → 验证。

全流程自动化，避免人工等待 ~60 分钟 CI。
约束（本机沙箱/环境，勿违反）：
  - 不使用 schtasks（程序黑名单）
  - 不使用 shutil.rmtree（触发批量删除确认钩子）
  - 脚本放 repo 根运行（run 目录有 python3.dll 会破坏托管 python 的 ssl）
  - 拉起靠 biliup-monitor 计划任务（系统调度服务触发，跨轮次存活）
"""
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.request import ProxyHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deploy_replace  # noqa: E402

REPO = "conquhare/biliup_douy"
API = f"https://api.github.com/repos/{REPO}"
# 用法: python ci_deploy_pipeline.py [run_id] [want_sha]
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "40379969214"
WANT_SHA = (sys.argv[2] if len(sys.argv) > 2
            else "b37516e8ca35ada53c1ad196f7c707fbf1cc9c70")  # 推送后的远程 commit
ZIP = deploy_replace.ZIP
DONE = deploy_replace.DONE
LOG = os.path.join(deploy_replace.BUILD, "ci_deploy_pipeline.log")

ctx = ssl._create_unverified_context()
# ⚠️ 不使用代理：代理端口每轮会话都会变，后台任务捕获的往往是已失效端口；
# 而 api.github.com 直连可用（实测 NO-PROXY OK），且 blob 下载走直连更快（~2.3MB/s vs 20KB/s）。
# ProxyHandler({}) 显式禁用代理：build_opener 默认会带一个读环境变量的 ProxyHandler，
# 而后台任务继承的往往是已失效端口 → 必须显式传空代理覆盖掉默认行为。
opener = urllib.request.build_opener(ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))

cred = open(os.path.expanduser("~/.git-credentials"), encoding="utf-8", errors="replace").read()
TOKEN = max((m.group(2) for line in cred.splitlines() if "github.com" in line
             for m in [re.match(r"https://([^:]+):([^@]+)@github\.com", line.strip())] if m), key=len)
H = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json",
     "User-Agent": "ci-deploy"}


def log(*a):
    msg = " ".join(str(x) for x in a)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    print(msg, flush=True)


def api(path, raw=False):
    h = dict(H)
    if raw:
        h["Accept"] = "application/vnd.github.raw"
    req = urllib.request.Request(API + path, headers=h)
    # ⚠️ 必须在 with 内读完：with 退出会 close() 响应，之后再 .read() 得到空 bytes
    # → json.loads 报 "Expecting value: line 1 column 1"（曾误判为代理问题）
    with opener.open(req, timeout=300) as r:
        return r.read()


def japi(path):
    return json.loads(api(path).decode())


def wait_ci(timeout=6600):
    """等 CI run 完成，返回 True=success。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            d = japi(f"/actions/runs/{RUN_ID}")
            st, conc = d.get("status"), d.get("conclusion")
            log(f"CI {RUN_ID}: status={st} conclusion={conc}")
            if st == "completed":
                return conc == "success"
        except Exception as e:
            log(f"CI 查询异常: {repr(e)[:120]}")
        time.sleep(60)
    log("等 CI 超时")
    return False


def wait_builds_published(timeout=1800):
    """等 builds 分支出现本次提交的产物（commit message = 'build <sha>'）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = japi("/commits/builds")
            msg = c.get("commit", {}).get("message", "")
            if WANT_SHA[:10] in msg or WANT_SHA in msg:
                log(f"builds 分支已发布本次构建: {msg.strip()[:60]}")
                return True
            log(f"builds 仍是旧产物: {msg.strip()[:50]}")
        except Exception as e:
            log(f"builds 查询异常: {repr(e)[:120]}")
        time.sleep(45)
    log("等 builds 发布超时")
    return False


def download():
    """经 Git Blob API raw（走 api CDN）下载 biliup-dist.zip。"""
    c = japi("/commits/builds")
    full = c["sha"]
    tree = japi(f"/git/trees/{full}")
    sha = None
    for e in tree.get("tree", []):
        if e["path"] == "biliup-dist.zip":
            sha = e["sha"]
            log(f"blob sha={sha[:12]} size={e.get('size')}")
    if not sha:
        return False
    data = api(f"/git/blobs/{sha}", raw=True)
    with open(ZIP, "wb") as f:
        f.write(data)
    with open(DONE, "w") as f:
        f.write("done")
    log(f"下载完成: {len(data)} bytes -> {ZIP}")
    return len(data) > 10_000_000


def wait_monitor_up(timeout=660):
    """等 monitor 计划任务把新 exe 拉起（它跨轮次存活）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = subprocess.run("tasklist", capture_output=True, text=True,
                             errors="replace", shell=True).stdout or ""
        if "biliup.exe" in out:
            net = subprocess.run("netstat -ano", capture_output=True, text=True,
                                 errors="replace", shell=True).stdout or ""
            if ":19159" in net and "LISTENING" in net:
                try:
                    d = json.loads(urllib.request.urlopen(
                        "http://127.0.0.1:19159/v1/streamers", timeout=8).read().decode())
                    log(f"新 exe 已运行，API 返回 {len(d)} 个房间")
                    return True
                except Exception as e:
                    log(f"API 异常: {repr(e)[:100]}")
        time.sleep(15)
    log("等待 monitor 拉起超时")
    return False


def main():
    log("=== CI 部署流水线启动 ===")
    if not wait_ci():
        log("CI 未成功，放弃")
        return 1
    if not wait_builds_published():
        log("产物未发布，放弃")
        return 1
    if not download():
        log("下载失败，放弃")
        return 1

    # 直播护栏 + 部署（有房间在录/传则等待重试）
    deadline = time.time() + 8 * 3600
    while time.time() < deadline:
        if deploy_replace.live_guard():
            log("护栏通过，开始部署")
            if deploy_replace.deploy():
                log("部署已执行，等待 monitor 拉起新 exe...")
                if wait_monitor_up():
                    log("=== 部署完成并验证通过 ===")
                    return 0
                log("部署已替换但 monitor 未在预期内拉起，请人工确认")
                return 1
            log("deploy() 返回失败，10 分钟后重试")
        else:
            log("有房间正在录制/上传，10 分钟后重试")
        time.sleep(600)
    log("等待空闲超时（8h），未部署")
    return 1


if __name__ == "__main__":
    sys.exit(main())
