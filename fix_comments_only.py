#!/usr/bin/env python3
"""
只修复注释中的乱码，保留代码逻辑
"""

import re
import subprocess

def get_correct_file_from_git(filepath, commit="3c9cc3f"):
    """从 Git 获取正确版本的文件"""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{filepath}"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def extract_comments(line):
    """提取行中的注释"""
    # 匹配 // 注释
    if '//' in line:
        code_part = line.split('//')[0]
        comment_part = '//' + '//'.join(line.split('//')[1:])
        return code_part, comment_part
    return line, None

def is_mojibake(text):
    """检查是否是乱码"""
    # 检查常见的乱码字符
    mojibake_chars = ['锟', '參', '數', '監', '控', '隊', '列', '庫', '狀', '態', '亯', '亰', '亱', '亲']
    for char in mojibake_chars:
        if char in text:
            return True
    # 检查是否有大量非ASCII字符但不是中文
    non_ascii = [c for c in text if ord(c) > 127]
    if non_ascii:
        chinese = [c for c in non_ascii if '\u4e00' <= c <= '\u9fff']
        if len(chinese) < len(non_ascii) * 0.5:  # 如果中文字符少于一半，可能是乱码
            return True
    return False

def fix_file(filepath):
    """修复文件中的注释乱码"""
    print(f"处理: {filepath}")
    
    # 读取当前文件
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        current_lines = f.readlines()
    
    # 从 Git 获取正确版本
    correct_content = get_correct_file_from_git(filepath)
    if not correct_content:
        print(f"  ✗ 无法从 Git 获取正确版本")
        return False
    
    correct_lines = correct_content.split('\n')
    
    # 逐行处理
    fixed_lines = []
    changes = []
    
    for i, (current_line, correct_line) in enumerate(zip(current_lines, correct_lines)):
        # 提取当前行的注释
        current_code, current_comment = extract_comments(current_line.rstrip())
        correct_code, correct_comment = extract_comments(correct_line.rstrip())
        
        # 如果当前行有乱码注释，且正确版本有正常注释
        if current_comment and is_mojibake(current_comment):
            if correct_comment and not is_mojibake(correct_comment):
                # 使用正确版本的注释
                fixed_line = current_code + correct_comment
                fixed_lines.append(fixed_line + '\n')
                changes.append(f"行 {i+1}: {current_comment.strip()} -> {correct_comment.strip()}")
                continue
        
        # 否则保留当前行
        fixed_lines.append(current_line)
    
    # 处理剩余的行（如果文件长度不同）
    if len(current_lines) > len(correct_lines):
        fixed_lines.extend(current_lines[len(correct_lines):])
    
    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    if changes:
        print(f"  ✓ 修复了 {len(changes)} 处注释")
        for change in changes[:5]:  # 只显示前5处修改
            print(f"    {change}")
        if len(changes) > 5:
            print(f"    ... 还有 {len(changes) - 5} 处")
    else:
        print(f"  ✓ 无需修复")
    
    return True

if __name__ == '__main__':
    files = [
        "crates/biliup-cli/src/server/core/monitor.rs",
        "crates/biliup-cli/src/server/config.rs",
        "crates/biliup-cli/src/server/common/download.rs",
    ]
    
    print("=" * 60)
    print("修复注释乱码（保留代码逻辑）")
    print("=" * 60)
    
    for filepath in files:
        fix_file(filepath)
        print()
