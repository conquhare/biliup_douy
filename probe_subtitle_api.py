# -*- coding: utf-8 -*-
"""只读探针：验证 B 站稿件状态 / allow_submit 真值 / wbi 未签名的影响。
用法: python probe_subtitle_api.py <aid>
仅读取，不做任何上传。
"""
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request

AID = sys.argv[1] if len(sys.argv) > 1 else "117507838973867"
COOKIE_FILE = "E:/biliup_live_rec/biliup_run/cookies.json"

ctx = ssl._create_unverified_context()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                     urllib.request.HTTPSHandler(context=ctx))


def load_cookie():
    with open(COOKIE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("cookie_info", {}).get("cookies") or data.get("cookies") or []
    if isinstance(data, dict) and not items:
        items = [{"name": k, "value": v} for k, v in data.items()]
    return "; ".join(f"{c['name']}={c['value']}" for c in items), {
        c["name"]: c["value"] for c in items}


def get(url, params, referer="https://www.bilibili.com/"):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Referer": referer,
        "Cookie": COOKIE,
    })
    with opener.open(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


COOKIE, MAP = load_cookie()
print("cookie 字段:", sorted(MAP.keys())[:12])
print("bili_jct:", "有" if MAP.get("bili_jct") else "无",
      "| SESSDATA:", "有" if MAP.get("SESSDATA") else "无")

try:
    v = json.loads(get("https://api.bilibili.com/x/web-interface/view", {"aid": AID}))
    print("view code =", v.get("code"), v.get("message"))
    d = v.get("data") or {}
    print("稿件:", d.get("title"), "| state=", d.get("state"),
          "| 分P 数 =", len(d.get("pages") or []))
    for p in (d.get("pages") or [])[:12]:
        print(f"  part {p['page']}: cid={p['cid']} 时长={p.get('duration')}s "
              f"part={p.get('part')} 首帧={p.get('first_frame') is not None}")
except Exception as e:
    print("view 失败:", repr(e)[:160])
    sys.exit(1)

pages = (d.get("pages") or [])
if not pages:
    sys.exit(0)
cid = pages[0]["cid"]

# 1) 未签名直接打 wbi 接口（当前代码就是这么调的）
try:
    raw = get("https://api.bilibili.com/x/player/wbi/v2", {"aid": AID, "cid": cid})
    j = json.loads(raw)
    print("\n[wbi 未签名] code =", j.get("code"), "| message =", j.get("message"))
    sub = ((j.get("data") or {}).get("subtitle")) or {}
    print("  subtitle =", json.dumps(sub, ensure_ascii=False)[:400])
    print("  allow_submit =", sub.get("allow_submit"))
except Exception as e:
    print("wbi 探测失败:", repr(e)[:160])

# 2) 非 wbi 旧接口对照
try:
    j2 = json.loads(get("https://api.bilibili.com/x/player/v2", {"aid": AID, "cid": cid}))
    sub2 = ((j2.get("data") or {}).get("subtitle")) or {}
    print("[player/v2 ] code =", j2.get("code"), "| allow_submit =", sub2.get("allow_submit"),
          "| 现有字幕 =", [s.get("lan") for s in (sub2.get("subtitles") or [])])
except Exception as e:
    print("player/v2 探测失败:", repr(e)[:160])

# 3) 字幕草稿接口可读性
try:
    j3 = json.loads(get("https://api.bilibili.com/x/v2/dm/subtitle/draft/list",
                        {"oid": cid, "type": 1}))
    print("[draft/list] code =", j3.get("code"), json.dumps(j3.get("data"), ensure_ascii=False)[:300])
except Exception as e:
    print("draft/list 探测失败:", repr(e)[:160])

print("\n现在时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
