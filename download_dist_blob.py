import ssl, urllib.request, os, sys, time, json, re

REPO = "conquhare/biliup_douy"
OUT = "E:/biliup_live_rec/biliup_run/_new_build/biliup-dist.zip"
DONE = "E:/biliup_live_rec/biliup_run/_new_build/biliup-dist.zip.done"
LOG = "E:/biliup_live_rec/biliup_run/_new_build/dl_blob.log"
CHUNK = 256 * 1024
READ_TIMEOUT = 60
MAX_ATTEMPTS = 8

ctx = ssl._create_unverified_context()
cred = open(os.path.expanduser("~/.git-credentials"), encoding="utf-8", errors="replace").read()
tok = max((m.group(2) for line in cred.splitlines() if "github.com" in line for m in [re.match(r"https://([^:]+):([^@]+)@github\.com", line.strip())] if m), key=len)
op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

def log(*a):
    msg = " ".join(str(x) for x in a)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    print(msg, file=sys.stderr, flush=True)

def blob_sha():
    H = {"Authorization": f"token {tok}", "User-Agent": "sha", "Accept": "application/vnd.github+json"}
    c = json.loads(op.open(urllib.request.Request(f"https://api.github.com/repos/{REPO}/commits/builds", headers=H), timeout=20).read().decode())
    full = c["sha"]
    t = json.loads(op.open(urllib.request.Request(f"https://api.github.com/repos/{REPO}/git/trees/{full}", headers=H), timeout=20).read().decode())
    for e in t.get("tree", []):
        if e["path"] == "biliup-dist.zip":
            return e["sha"], e.get("size")
    raise RuntimeError("biliup-dist.zip 不在 builds 分支 tree 中")

def download(sha, total):
    H = {"Authorization": f"token {tok}", "User-Agent": "blobraw", "Accept": "application/vnd.github.raw"}
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{sha}"
    got = 0
    r = op.open(urllib.request.Request(url, headers=H), timeout=READ_TIMEOUT)
    if r.status != 200:
        raise RuntimeError(f"非200: {r.status}")
    with open(OUT, "wb") as f:
        while True:
            buf = r.read(CHUNK)
            if not buf:
                break
            f.write(buf)
            got += len(buf)
    if got != total:
        raise RuntimeError(f"长度不符 {got} != {total}")
    with open(DONE, "w") as f:
        f.write(str(got))
    return got

if __name__ == "__main__":
    for i in range(1, MAX_ATTEMPTS + 1):
        try:
            log(f"=== 第 {i}/{MAX_ATTEMPTS} 次: 取 blob sha ===")
            sha, total = blob_sha()
            log(f"blob sha={sha[:12]}.. size={total}")
            log("开始下载（Git Blob API raw，走 api CDN）...")
            t0 = time.time()
            got = download(sha, total)
            log(f"下载完成: {got} bytes，用时 {time.time()-t0:.1f}s")
            sys.exit(0)
        except Exception as e:
            log(f"失败: {repr(e)[:160]}")
            time.sleep(5)
    log("超过最大尝试次数")
    sys.exit(1)
