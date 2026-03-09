#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码修复测试计划
验证所有修复后的文件编码是否正确
"""

import os
import sys

def test_file_encoding(filepath):
    """测试单个文件的编码"""
    results = {
        'filepath': filepath,
        'readable': False,
        'has_gibberish': False,
        'gibberish_chars': [],
        'first_line': '',
        'errors': []
    }

    try:
        # 尝试用 UTF-8 读取
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # 读取前2000字符

        results['readable'] = True
        results['first_line'] = content.split('\n')[0] if content else ''

        # 检查是否还有 GBK 乱码特征字符
        gibberish_patterns = set(
            '鎶栭煶勫彂曘綍剾弬鑰冧欼欻殑湁搴旀嚜嚚嚩嚪嚫殏殐殒殓殔殕殖殗殘殙'
            '犳犴犵犺犻犼犽犾犿狀狁琚琛琜琝琞琟琠琡琣琤琧綖綗綘継綜綝綞綟綠綡綢'
            '繀繂繃繄繅繆繈繉繊繋繌臄臅臇臈臉臊臋臍臎臏臐茛茝茞茟茠茡茢茣茤茥茦'
            '锘閹舵牠鐓堕惃鍕剨楠炴洖缍嶉崚璺哄棘閼板啩绨閸濞ｈ濮為弶銉ㄥ殰'
        )

        for char in content:
            if char in gibberish_patterns:
                results['has_gibberish'] = True
                results['gibberish_chars'].append(char)

        # 检查是否包含正常的中文字符
        chinese_chars = [c for c in content if '\u4e00' <= c <= '\u9fff']
        results['chinese_count'] = len(chinese_chars)

    except UnicodeDecodeError as e:
        results['errors'].append(f"UTF-8解码失败: {e}")
    except Exception as e:
        results['errors'].append(f"读取失败: {e}")

    return results

def test_critical_files():
    """测试关键文件"""
    critical_files = [
        'biliup/Danmaku/douyin.py',
        'biliup/Danmaku/__init__.py',
        'biliup/common/abogus.py',
        'biliup/common/Daemon.py',
        'biliup/plugins/douyin.py',
    ]

    print("=" * 80)
    print("编码修复测试报告")
    print("=" * 80)

    passed = 0
    failed = 0

    for filepath in critical_files:
        full_path = os.path.join('.', filepath)
        if not os.path.exists(full_path):
            print(f"\n⚠ 文件不存在: {filepath}")
            failed += 1
            continue

        result = test_file_encoding(full_path)

        print(f"\n{'='*80}")
        print(f"文件: {filepath}")
        print(f"{'='*80}")

        if result['errors']:
            print(f"❌ 测试失败:")
            for error in result['errors']:
                print(f"   - {error}")
            failed += 1
        elif result['has_gibberish']:
            print(f"⚠ 警告: 仍包含乱码字符")
            print(f"   乱码字符: {set(result['gibberish_chars'])}")
            print(f"   第一行: {result['first_line'][:60]}...")
            failed += 1
        else:
            print(f"✅ 测试通过")
            print(f"   第一行: {result['first_line'][:60]}...")
            print(f"   中文字符数: {result['chinese_count']}")
            passed += 1

    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    return failed == 0

def test_danmaku_functionality():
    """测试弹幕功能是否能正常导入"""
    print(f"\n{'='*80}")
    print("弹幕功能导入测试")
    print(f"{'='*80}")

    try:
        # 测试导入弹幕模块
        sys.path.insert(0, '.')
        from biliup.Danmaku import DanmakuClient
        print("✅ DanmakuClient 导入成功")

        # 测试导入抖音弹幕模块
        from biliup.Danmaku import douyin
        print("✅ 抖音弹幕模块导入成功")

        # 检查关键类和方法
        assert hasattr(douyin, 'Douyin'), "Douyin 类不存在"
        assert hasattr(douyin.Douyin, 'get_ws_info'), "get_ws_info 方法不存在"
        assert hasattr(douyin.Douyin, 'decode_msg'), "decode_msg 方法不存在"
        print("✅ 抖音弹幕类结构完整")

        return True
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("开始执行编码修复测试计划...\n")

    # 测试关键文件编码
    encoding_ok = test_critical_files()

    # 测试功能导入
    functionality_ok = test_danmaku_functionality()

    print(f"\n{'='*80}")
    print("最终测试结果")
    print(f"{'='*80}")
    print(f"编码测试: {'✅ 通过' if encoding_ok else '❌ 失败'}")
    print(f"功能测试: {'✅ 通过' if functionality_ok else '❌ 失败'}")

    if encoding_ok and functionality_ok:
        print("\n🎉 所有测试通过！编码修复成功。")
        return 0
    else:
        print("\n⚠ 部分测试失败，请检查修复结果。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
