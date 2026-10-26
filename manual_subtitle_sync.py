# -*- coding: utf-8 -*-
"""给【已投稿】的稿件手动补传弹幕字幕（复用插件真实方法，避免测试代码与线上分叉）。

用法: python manual_subtitle_sync.py <aid> <整场累计的 ass 路径>
用途：CI/录制流程没跑到字幕时的补救，也可用于验证字幕通道。
"""
import asyncio
import json
import os
import sys


async def main():
    import requests
    from biliup.plugins.bili_webup_sync import BiliBili

    aid, ass = sys.argv[1], sys.argv[2]
    if not os.path.exists(ass):
        print("ASS 不存在:", ass)
        return 1

    ck = json.load(open("E:/biliup_live_rec/biliup_run/cookies.json", encoding="utf-8"))
    cookies = {c["name"]: c["value"] for c in ck["cookie_info"]["cookies"]}
    b = BiliBili.__new__(BiliBili)
    s = requests.Session()
    s.trust_env = False  # 不走系统代理（代理 IP 会触发 B站风控）
    s.cookies.update(cookies)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Referer": "https://member.bilibili.com/",
    })
    b.__dict__["_BiliBili__session"] = s
    b.__dict__["_BiliBili__bili_jct"] = cookies.get("bili_jct")

    bvid, pages = b._get_aid_info(aid, max_wait=30)
    if not bvid:
        return 1
    print(f"稿件 {bvid} 共 {len(pages)} 个分P")
    offset = 0.0
    ok = 0
    for idx, (cid, dur, title) in enumerate(pages, 1):
        bcc = b._ass_to_bcc(ass, offset=offset, duration=dur)
        if b._save_subtitle_bcc(bvid, cid, bcc, tag=f"P{idx} {title}"):
            ok += 1
        offset += dur
    print(f"完成 {ok}/{len(pages)} 个分P")
    return 0 if ok == len(pages) else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
