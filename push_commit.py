# -*- coding: utf-8 -*-
"""用 GitHub Git Data API 推送本地 commit（绕开本机 git push 经代理必然卡死的问题）。

用法：python push_commit.py <local_commit_sha>
"""
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.request import ProxyHandler

REPO = "conquhare/biliup_douy"
BRANCH = "master"
API = f"https://api.github.com/repos/{REPO}"
LOCAL = r"E:\biliup_live_rec\biliup_code"

ctx = ssl._create_unverified_context()
hp = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
if hp:
    opener = urllib.request.build_opener(ProxyHandler({"https": hp, "http": hp}),
                                         urllib.request.HTTPSHandler(context=ctx))
else:
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

cred = open(os.path.expanduser("~/.git-credentials"), encoding="utf-8", errors="replace").read()
toks = [m.group(2) for line in cred.splitlines() if "github.com" in line
        for m in [re.match(r"https://([^:]+):([^@]+)@github\.com", line.strip())] if m]
TOKEN = max(toks, key=len)
H = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json",
     "User-Agent": "push-commit"}


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=H, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read(400).decode(errors="replace"))
        raise


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=LOCAL,
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args} failed: {r.stderr.decode(errors='replace')[:300]}")
    return r.stdout


def main():
    sha = sys.argv[1]
    # 远程当前状态
    ref = api("GET", f"/git/refs/heads/{BRANCH}")
    remote_sha = ref["object"]["sha"]
    commit = api("GET", f"/git/commits/{remote_sha}")
    base_tree = commit["tree"]["sha"]
    print(f"remote {BRANCH} = {remote_sha[:10]}  base_tree={base_tree[:10]}")

    changed = git("diff-tree", "--no-commit-id", "--name-status", "-r", sha).decode().strip().splitlines()
    tree_items = []
    for ln in changed:
        status, path = ln.split("\t", 1)
        if status == "D":
            tree_items.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
            continue
        content = git("show", f"{sha}:{path}").decode("utf-8")
        blob = api("POST", "/git/blobs", {"content": content, "encoding": "utf-8"})
        mode = git("ls-files", "--format=%(objectmode)", "--", path).decode().strip() or "100644"
        if len(mode) == 5:
            mode = "0" + mode
        tree_items.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
        print(f"  blob {path} -> {blob['sha'][:10]} (mode {mode})")

    tree = api("POST", "/git/trees", {"base_tree": base_tree, "tree": tree_items})
    new_commit = api("POST", "/git/commits", {
        "message": git("log", "-1", "--format=%B", sha).decode("utf-8").strip(),
        "parents": [remote_sha],
        "tree": tree["sha"],
    })
    api("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": new_commit["sha"]})
    print(f"PUSHED: local {sha[:10]} -> remote {new_commit['sha'][:10]}")
    print(new_commit["html_url"])


if __name__ == "__main__":
    main()
