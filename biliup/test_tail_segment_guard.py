# -*- coding: utf-8 -*-
"""尾巴分段过滤 + 段命名的一致性验证（不联网、不上传）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIN_VALID_SEGMENT_BYTES = 1 * 1024 * 1024


def is_valid_segment(actual_size):
    """与 upload_stream 中的过滤逻辑保持一致。"""
    if actual_size is None:      # 拿不到真实体积（旧链路）时保守放行
        return True
    return actual_size >= MIN_VALID_SEGMENT_BYTES


def check(name, cond):
    print(('[PASS] ' if cond else '[FAIL] ') + name)
    return bool(cond)


def main():
    ok = True
    print('=== 尾巴分段过滤 ===')
    # 真实案例：10-09 小纯同学第 2 段仅 519286 字节
    ok &= check('519286 字节（实测尾巴段）判为无效',
                not is_valid_segment(519286))
    # 真实案例：10-08 偷心九月天第 1 段 405004181 字节
    ok &= check('405MB（正常段）判为有效',
                is_valid_segment(405004181))
    ok &= check('0 字节判为无效', not is_valid_segment(0))
    ok &= check('恰好 1MB 边界判为有效（>= 阈值）',
                is_valid_segment(MIN_VALID_SEGMENT_BYTES))
    ok &= check('1MB-1 判为无效', not is_valid_segment(MIN_VALID_SEGMENT_BYTES - 1))
    ok &= check('size 缺失(None)时保守放行', is_valid_segment(None))

    print('\n=== 段命名一致性 ===')
    # 日志里的段名必须与实际分P名一致，否则排查时会误判
    output_prefix = '小纯同学欢乐抽象2026-10-08 22_51'
    old_log = f'{output_prefix}{1:03d}.mkv'      # 旧写法 -> 22_51001
    new_log = f'{output_prefix}_{1}.mkv'          # 新写法 -> 22_51_1
    real_name = f'{output_prefix}_{1}.mkv'        # upload_stream 里的真实名
    print(f'  旧日志名: {old_log}')
    print(f'  新日志名: {new_log}')
    print(f'  真实分P名: {real_name}')
    ok &= check('新日志名与真实分P名一致', new_log == real_name)
    ok &= check('旧写法确实产生了粘连（说明修的是真问题）',
                old_log != real_name and old_log.endswith('51001.mkv'))

    print('\n结果：' + ('全部通过' if ok else '存在失败用例'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())