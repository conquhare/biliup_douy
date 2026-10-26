# -*- coding: utf-8 -*-
"""真机验证 B站字幕 draft/save 通道：ASS 切片 -> BCC -> draft/save -> 复查。

用法: python test_bcc_save.py <aid> <cid> <ass_path> <part_seconds> [lan]
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

AID = sys.argv[1]
CID = sys.argv[2]
ASS = sys.argv[3]
PART_SEC = int(sys.argv[4]) if len(sys.argv) > 4 else 1801
LAN = sys.argv[5] if len(sys.argv) > 5 else "zh"
OFFSET = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

ctx = ssl._create_unverified_context()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                     urllib.request.HTTPSHandler(context=ctx))
CK = json.load(open("E:/biliup_live_rec/biliup_run/cookies.json", encoding="utf-8"))
MAP = {c["name"]: c["value"] for c in CK["cookie_info"]["cookies"]}
COOKIE = "; ".join(f"{k}={v}" for k, v in MAP.items())
JCT = MAP["bili_jct"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get(url, params, referer="https://www.bilibili.com/"):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA, "Cookie": COOKIE, "Referer": referer})
    with opener.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def t2s(t):
    h, m, s = t.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def ass_to_bcc(path, seconds, offset=0.0):
    """ASS -> BCC。只取 [offset, offset+seconds) 区间，时间轴平移到 0 起点。"""
    body = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if not ln.startswith("Dialogue"):
                continue
            cols = ln.rstrip("\n").split(",", 9)
            if len(cols) < 10:
                continue
            start, end, text = t2s(cols[1]), t2s(cols[2]), cols[9]
            if start < offset or start >= offset + seconds:
                continue
            # 剥掉 ASS 特效标签，\N 换成换行
            text = re.sub(r"\{[^}]*\}", "", text).replace("\\N", "\n").replace("\\n", "\n")
            text = text.strip()
            if not text:
                continue
            body.append({"from": round(start - offset, 3), "to": round(end - offset, 3),
                         "location": 2, "content": text})
    return {"font_size": 0.4, "font_color": "#FFFFFF", "background_alpha": 0.5,
            "background_color": "#9C27B0", "Stroke": "none", "body": body}


v = get("https://api.bilibili.com/x/web-interface/view", {"aid": AID})
BVID = (v.get("data") or {}).get("bvid")
print("bvid =", BVID)

bcc = ass_to_bcc(ASS, PART_SEC, OFFSET)
print("BCC 条目 =", len(bcc["body"]), "| 首条 =", bcc["body"][0]["from"] if bcc["body"] else None,
      "| 末条 =", bcc["body"][-1]["to"] if bcc["body"] else None)
if not bcc["body"]:
    sys.exit(1)

form = {"lan": LAN, "submit": "true", "csrf": JCT, "sign": "false", "bvid": BVID,
        "type": "1", "oid": CID, "data": json.dumps(bcc, ensure_ascii=False)}
req = urllib.request.Request(
    "https://api.bilibili.com/x/v2/dm/subtitle/draft/save",
    data=urllib.parse.urlencode(form).encode(),
    headers={"User-Agent": UA, "Cookie": COOKIE,
             "Content-Type": "application/x-www-form-urlencoded",
             "Origin": "https://account.bilibili.com",
             "Referer": f"https://account.bilibili.com/subtitle/edit/#/editor?bvid={BVID}&cid={CID}"})
with opener.open(req, timeout=120) as r:
    resp = r.read().decode("utf-8", "replace")
print("[draft/save] raw:", resp[:300])

time.sleep(3)
s = ((get("https://api.bilibili.com/x/player/v2", {"aid": AID, "cid": CID})
      .get("data") or {}).get("subtitle") or {})
print("[复查] 字幕 =", [(x.get("lan"), x.get("lan_doc"), x.get("ai_status"))
                        for x in (s.get("subtitles") or [])])
