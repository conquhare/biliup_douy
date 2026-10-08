# -*- coding: utf-8 -*-
"""边录边传字幕定位逻辑的离线验证（无需开播、无需网络）。

覆盖场景：
  1. 单段录制：直接推导命中
  2. 多段录制（核心 bug）：save_path 停在 _1，实际生成 _3.ass →必须走前缀兜底
  3. 兜底选「最新」而不是「字典序最大」
  4. 完全没有 ass → 返回期望路径，由调用方告警（不静默跳过）
  5. 前缀误伤：不同主播同前缀前缀相似文件不应被选中

运行： D:/programfiles/miniforge3/python.exe tests/test_subtitle_resolve.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biliup.plugins.bili_webup_sync import resolve_ass_file


def touch(path, content='fake'):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def case(name, got, want_exists=None, want_name=None):
    """want_exists=True 断言存在；False 断言不存在（供告警打印）；None 不检查。"""
    ok = True
    if want_exists is not None:
        ok = ok and (os.path.exists(got) == want_exists)
    if want_name is not None:
        ok = ok and (os.path.basename(got) == want_name)
    print(('[PASS] ' if ok else '[FAIL] ') + name)
    print('        -> ' + got)
    return ok


def main():
    import tempfile
    all_ok = True
    with tempfile.TemporaryDirectory() as d:
        # 场景1：单段，直接命中
        sp = os.path.join(d, '主播A2026-10-08 20_00_00.mkv')
        touch(sp)
        touch(os.path.join(d, '主播A2026-10-08 20_00_00.ass'))
        all_ok &= case('场景1 单段录制：save_path 同名 ass 直接命中',
                       resolve_ass_file(sp, d), True, '主播A2026-10-08 20_00_00.ass')

    with tempfile.TemporaryDirectory() as d:
        # 场景2：3段录制，实际生成 _3.ass，而 save_path 停在 _1
        sp = os.path.join(d, '偷心九月天2026-10-08 20_00_00_1.mkv')
        touch(sp)
        touch(os.path.join(d, '偷心九月天2026-10-08 20_00_00_3.ass'))
        all_ok &= case('场景2 多段错位：_1 推导失败 -> 前缀兜底找到 _3.ass',
                       resolve_ass_file(sp, d), True, '偷心九月天2026-10-08 20_00_00_3.ass')

    with tempfile.TemporaryDirectory() as d:
        # 场景3：多个 ass 存在，应选 mtime 最新的（数字小的更新）
        sp = os.path.join(d, '蓝调野僧2026-10-08 20_00_00_2.mkv')
        touch(sp)
        a1 = os.path.join(d, '蓝调野僧2026-10-08 20_00_00_1.ass')
        a3 = os.path.join(d, '蓝调野僧2026-10-08 20_00_00_3.ass')
        a10 = os.path.join(d, '蓝调野僧2026-10-08 20_00_00_10.ass')
        touch(a1); touch(a3); touch(a10)
        os.utime(a1, (time.time() - 300, time.time() - 300))
        os.utime(a3, (time.time() - 100, time.time() - 100))
        os.utime(a10, (time.time() - 600, time.time() - 600))
        all_ok &= case('场景3 多个 ass：按 mtime 选最新（不是字典序最大）',
                       resolve_ass_file(sp, d), True, '蓝调野僧2026-10-08 20_00_00_3.ass')

    with tempfile.TemporaryDirectory() as d:
        # 场景4：没有任何 ass -> 返回期望路径，交由调用方告警
        sp = os.path.join(d, '没有弹幕2026-10-08 20_00_00_1.mkv')
        touch(sp)
        all_ok &= case('场景4 无 ass：返回期望路径(不存在)供告警，不抛异常',
                       resolve_ass_file(sp, d), False, '没有弹幕2026-10-08 20_00_00_1.ass')

    with tempfile.TemporaryDirectory() as d:
        # 场景5：同目录「同主播不同场次」的 ass（20_00_00 vs 21_00_00），不应被误选
        sp = os.path.join(d, '偷心九月天2026-10-08 20_00_00_1.mkv')
        touch(sp)
        touch(os.path.join(d, '偷心九月天2026-10-08 21_00_00_9.ass'))
        all_ok &= case('场景5 同主播不同场次：不误选他人/他场次字幕',
                       resolve_ass_file(sp, d), False, '偷心九月天2026-10-08 20_00_00_1.ass')

    print('\n结果：' + ('全部通过' if all_ok else '存在失败用例'))
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())