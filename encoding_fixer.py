#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码修复工具 - 修复 GBK 乱码文件

功能：
1. 智能检测包含 GBK 乱码的文件
2. 使用逆向修复原理恢复原始内容
3. 批量处理整个项目

修复原理：
原始 UTF-8 内容 → 错误解析为 GBK → 保存为 UTF-8 乱码
修复：UTF-8 乱码 → 编码为 GBK 字节 → 解码为 UTF-8 正确内容
"""

import os
import sys


def analyze_byte_pattern(filepath):
    """
    分析文件字节模式，判断是否包含 GBK 乱码

    GBK 乱码的特征：
    1. 原本应是 UTF-8 的中文被错误解析为 GBK
    2. 出现扩展A区字符（Unicode 0x3400-0x4DBF 范围）
    3. 特定的字节模式
    """
    try:
        with open(filepath, 'rb') as f:
            content = f.read()

        # 移除 BOM
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]

        # 解码为当前文本（可能是乱码）
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('utf-8', errors='ignore')

        # 统计字符类型
        stats = {
            'total_chars': len(text),
            'cjk_unified': 0,      # 常用汉字 4E00-9FFF
            'cjk_extension_a': 0,   # 扩展A 3400-4DBF（乱码特征）
            'cjk_extension_b': 0,   # 扩展B 20000-2A6DF
            'gbk_gibberish': 0,     # 已知 GBK 乱码字符
        }

        # 已知的 GBK 乱码字符集
        gibberish_chars = set(
            '鎶栭煶勫彂曘綍剾弬鑰冧欼欻殑湁搴旀嚜嚚嚩嚪嚫殏殐殒殓殔殕殖殗殘殙'
            '犳犴犵犺犻犼犽犾犿狀狁琚琛琜琝琞琟琠琡琣琤琧綖綗綘継綜綝綞綟綠綡綢'
            '繀繂繃繄繅繆繈繉繊繋繌臄臅臇臈臉臊臋臍臎臏臐茛茝茞茟茠茡茢茣茤茥茦'
            '锘閹舵牠鐓堕惃鍕剨楠炴洖缍嶉崚璺哄棘閼板啩绨閸濞ｈ濮為弶銉ㄥ殰'
        )

        for char in text:
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                stats['cjk_unified'] += 1
            elif 0x3400 <= code <= 0x4DBF:
                stats['cjk_extension_a'] += 1
            elif 0x20000 <= code <= 0x2A6DF:
                stats['cjk_extension_b'] += 1

            if char in gibberish_chars:
                stats['gbk_gibberish'] += 1

        # 判断是否为乱码文件
        # 扩展A区字符比例过高或包含已知乱码字符
        is_mojibake = False
        confidence = 0.0

        if stats['total_chars'] > 0:
            ext_a_ratio = stats['cjk_extension_a'] / stats['total_chars']
            gibberish_ratio = stats['gbk_gibberish'] / stats['total_chars']

            # 扩展A区字符占比超过 0.5% 或包含 3 个以上已知乱码字符
            if ext_a_ratio > 0.005 or stats['gbk_gibberish'] >= 3:
                is_mojibake = True
                confidence = max(ext_a_ratio * 10, gibberish_ratio * 5)

        return {
            'is_mojibake': is_mojibake,
            'confidence': min(confidence, 1.0),
            'stats': stats
        }

    except Exception as e:
        return {'is_mojibake': False, 'confidence': 0, 'error': str(e)}


def fix_mojibake(filepath):
    """
    修复 GBK 乱码

    修复原理：
    1. 读取当前文件内容（UTF-8 编码的乱码字符）
    2. 将乱码字符编码为 GBK 字节（这相当于"逆向"错误过程）
    3. 将 GBK 字节解码为 UTF-8（得到原始正确内容）
    """
    try:
        # 读取文件
        with open(filepath, 'rb') as f:
            raw = f.read()

        # 保存原始 BOM 状态
        has_bom = raw.startswith(b'\xef\xbb\xbf')
        if has_bom:
            raw = raw[3:]

        # 解码为当前文本（乱码）
        mojibake_text = raw.decode('utf-8', errors='ignore')

        # 修复：编码为 GBK 再解码为 UTF-8
        try:
            # 方法1：直接转换
            gbk_bytes = mojibake_text.encode('gbk', errors='ignore')
            fixed_text = gbk_bytes.decode('utf-8', errors='ignore')
        except Exception:
            # 方法2：如果失败，尝试逐字符转换
            fixed_chars = []
            for char in mojibake_text:
                try:
                    gbk_byte = char.encode('gbk')
                    fixed_char = gbk_byte.decode('utf-8')
                    fixed_chars.append(fixed_char)
                except:
                    fixed_chars.append(char)
            fixed_text = ''.join(fixed_chars)

        # 验证修复效果
        before_gibberish = sum(1 for c in mojibake_text if ord(c) >= 0x3400 and ord(c) <= 0x4DBF)
        after_gibberish = sum(1 for c in fixed_text if ord(c) >= 0x3400 and ord(c) <= 0x4DBF)

        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_text)

        return {
            'success': True,
            'before_gibberish': before_gibberish,
            'after_gibberish': after_gibberish
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def scan_directory(directory='.', extensions=None):
    """
    扫描目录中的文件
    """
    if extensions is None:
        extensions = ['.py', '.js', '.md', '.txt', '.toml', '.yaml', '.yml', '.json']

    results = {
        'mojibake': [],
        'clean': [],
        'error': []
    }

    skip_dirs = {'.venv', 'node_modules', '.git', '_internal', '.pytest_cache', '__pycache__', 'dist', 'build'}

    for root, dirs, files in os.walk(directory):
        # 跳过指定目录
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in files:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)

                # 分析文件
                analysis = analyze_byte_pattern(filepath)

                if 'error' in analysis:
                    results['error'].append((filepath, analysis['error']))
                elif analysis['is_mojibake']:
                    results['mojibake'].append({
                        'path': filepath,
                        'confidence': analysis['confidence'],
                        'stats': analysis['stats']
                    })
                else:
                    results['clean'].append(filepath)

    return results


def main():
    print("=" * 80)
    print("编码修复工具 - 修复 GBK 乱码文件")
    print("=" * 80)
    print()

    # 扫描目录
    print("正在扫描文件...")
    results = scan_directory()

    # 显示有问题的文件
    if results['mojibake']:
        print(f"\n发现 {len(results['mojibake'])} 个可能存在乱码的文件:")
        print("-" * 80)

        for item in results['mojibake']:
            print(f"\n文件: {item['path']}")
            print(f"  置信度: {item['confidence']:.1%}")
            stats = item['stats']
            print(f"  统计: 总字符={stats['total_chars']}, "
                  f"扩展A={stats['cjk_extension_a']}, "
                  f"乱码={stats['gbk_gibberish']}")

        print("\n" + "-" * 80)
        print("开始修复...")

        fixed_count = 0
        error_count = 0

        for item in results['mojibake']:
            filepath = item['path']
            result = fix_mojibake(filepath)

            if result['success']:
                print(f"✅ {filepath}")
                print(f"  乱码字符: {result['before_gibberish']} -> {result['after_gibberish']}")
                fixed_count += 1
            else:
                print(f"❌ {filepath}")
                print(f"  错误: {result['error']}")
                error_count += 1

        print("\n" + "=" * 80)
        print("修复完成!")
        print(f"  成功: {fixed_count}")
        print(f"  失败: {error_count}")
        print(f"  干净文件: {len(results['clean'])}")
        print("=" * 80)

        return 0 if error_count == 0 else 1
    else:
        print(f"\n未发现乱码文件")
        print(f"扫描了 {len(results['clean'])} 个文件，全部正常")
        return 0


if __name__ == '__main__':
    sys.exit(main())
