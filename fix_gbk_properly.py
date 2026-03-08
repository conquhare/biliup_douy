#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 GBK 解码重新编码的方式修复乱码
"""

import os

def fix_file_properly(filepath):
    """通过 GBK 解码修复文件"""
    try:
        # 先读取原始字节
        with open(filepath, 'rb') as f:
            raw_bytes = f.read()
        
        # 尝试用 UTF-8 解码，看是否有乱码
        try:
            content_utf8 = raw_bytes.decode('utf-8')
            # 检查是否包含乱码特征字符
            if '�' not in content_utf8 and '\ue000' not in content_utf8:
                print(f"⏭️  跳过: {filepath} (无需修复)")
                return 0
        except:
            pass
        
        # 尝试用 GBK 解码
        try:
            content_gbk = raw_bytes.decode('gbk', errors='ignore')
            # 再编码为 UTF-8
            content_fixed = content_gbk.encode('utf-8').decode('utf-8')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content_fixed)
            print(f"✅ 已修复: {filepath}")
            return 1
        except Exception as e:
            print(f"⚠️  无法修复: {filepath} - {e}")
            return 0
            
    except Exception as e:
        print(f"❌ 无法读取: {filepath} - {e}")
        return 0

if __name__ == '__main__':
    # 修复所有 Python 文件
    files_to_fix = [
        'biliup/plugins/afreecaTV.py',
        'biliup/plugins/bigo.py',
        'biliup/plugins/bilibili.py',
        'biliup/plugins/bili_chromeup.py',
        'biliup/plugins/bili_webup.py',
        'biliup/plugins/bili_webup_sync.py',
        'biliup/plugins/cc.py',
        'biliup/plugins/douyin.py',
        'biliup/plugins/douyu.py',
        'biliup/plugins/general.py',
        'biliup/plugins/huya.py',
        'biliup/plugins/inke.py',
        'biliup/plugins/kilakila.py',
        'biliup/plugins/kuaishou.py',
        'biliup/plugins/missevan.py',
        'biliup/plugins/ttinglive.py',
        'biliup/plugins/twitcasting.py',
        'biliup/plugins/twitch.py',
        'biliup/plugins/huya_wup/packet/__util.py',
    ]
    
    total_fixes = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            total_fixes += fix_file_properly(filepath)
        else:
            print(f"⚠️  文件不存在: {filepath}")
    
    print(f"\n总计修复: {total_fixes} 个文件")
