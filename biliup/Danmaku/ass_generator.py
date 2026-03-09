# 弹幕转 ASS 字幕生成器
# 支持将 XML/JSON 格式的弹幕转换为 ASS 字幕文件

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger('biliup')


class AssGenerator:
    """ASS 字幕生成器"""

    # ASS 文件头部模板
    ASS_HEADER = """[Script Info]
Title: {title}
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H{color},&H{color},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,1,10,10,10,1
Style: Danmaku,{font_name},{font_size},&H{color},&H{color},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def __init__(self,
                 font_name: str = "Microsoft YaHei",
                 font_size: int = 25,
                 color: str = "00FFFFFF",  # BGR格式，白色
                 play_res_x: int = 1920,
                 play_res_y: int = 1080,
                 danmaku_speed: int = 8,  # 弹幕速度（像素/帧）
                 line_count: int = 12,    # 弹幕行数
                 bottom_margin: int = 50):  # 底部边距
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.play_res_x = play_res_x
        self.play_res_y = play_res_y
        self.danmaku_speed = danmaku_speed
        self.line_count = line_count
        self.bottom_margin = bottom_margin
        self.line_height = font_size + 4

    def generate_from_xml(self, xml_file: str, output_file: str, title: str = "Danmaku"):
        """从 XML 文件生成 ASS 字幕"""
        if not os.path.exists(xml_file):
            logger.error(f'XML 文件不存在: {xml_file}')
            return

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            danmaku_list = []
            for d in root.findall('d'):
                p_attr = d.get('p', '')
                content = d.text or ''

                # 解析 p 属性: 时间,模式,字号,颜色,发送时间,池,用户ID,rowID
                p_parts = p_attr.split(',')
                if len(p_parts) >= 4:
                    timestamp = float(p_parts[0])
                    color = p_parts[3]
                    danmaku_list.append({
                        'timestamp': timestamp,
                        'content': content,
                        'color': color
                    })

            self._generate_ass(danmaku_list, output_file, title)
            logger.info(f'ASS 字幕已生成: {output_file} ({len(danmaku_list)} 条弹幕)')

        except Exception as e:
            logger.exception(f'生成 ASS 字幕失败: {e}')

    def generate_from_json(self, json_file: str, output_file: str, title: str = "Danmaku"):
        """从 JSON 文件生成 ASS 字幕"""
        if not os.path.exists(json_file):
            logger.error(f'JSON 文件不存在: {json_file}')
            return

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            danmaku_list = data.get('danmaku_list', [])
            self._generate_ass(danmaku_list, output_file, title)
            logger.info(f'ASS 字幕已生成: {output_file} ({len(danmaku_list)} 条弹幕)')

        except Exception as e:
            logger.exception(f'生成 ASS 字幕失败: {e}')

    def _generate_ass(self, danmaku_list: List[Dict[str, Any]], output_file: str, title: str):
        """生成 ASS 文件"""
        # 按时间排序
        danmaku_list = sorted(danmaku_list, key=lambda x: x.get('timestamp', 0))

        # 写入头部
        header = self.ASS_HEADER.format(
            title=title,
            font_name=self.font_name,
            font_size=self.font_size,
            color=self.color,
            play_res_x=self.play_res_x,
            play_res_y=self.play_res_y
        )

        # 计算弹幕位置
        lines = [[] for _ in range(self.line_count)]  # 每行的弹幕结束时间

        events = []
        for danmaku in danmaku_list:
            timestamp = danmaku.get('timestamp', 0)
            content = danmaku.get('content', '')
            color = danmaku.get('color', '16777215')

            # 转换颜色格式
            ass_color = self._convert_color(color)

            # 计算弹幕宽度（估算）
            text_width = len(content) * self.font_size

            # 计算弹幕持续时间（根据宽度和速度）
            duration = (self.play_res_x + text_width) / (self.danmaku_speed * 60)  # 60fps

            # 找到可用的行
            line_idx = self._find_available_line(lines, timestamp, duration)
            if line_idx is None:
                continue  # 没有可用行，跳过这条弹幕

            # 计算位置
            start_x = self.play_res_x
            end_x = -text_width
            y_pos = self.line_height * line_idx + self.bottom_margin

            # 转换时间格式
            start_time = self._format_time(timestamp)
            end_time = self._format_time(timestamp + duration)

            # 创建移动效果
            effect = f"{{\\move({start_x},{y_pos},{end_x},{y_pos})\\c&H{ass_color}&}}"

            # 转义特殊字符
            content = self._escape_ass_text(content)

            # 创建事件行
            event = f"Dialogue: 0,{start_time},{end_time},Danmaku,,0,0,0,,{effect}{content}"
            events.append(event)

            # 更新该行的结束时间
            lines[line_idx].append(timestamp + duration)

        # 写入文件
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write('\n'.join(events))

    def _find_available_line(self, lines: List[List[float]], timestamp: float, duration: float) -> Optional[int]:
        """找到可用的弹幕行"""
        for i, line in enumerate(lines):
            # 清理已经过去的弹幕
            lines[i] = [end_time for end_time in line if end_time > timestamp]

            # 检查该行是否可用
            if not lines[i]:
                return i

            # 检查是否有足够的空间
            last_end_time = max(lines[i])
            if timestamp >= last_end_time - 0.5:  # 留出0.5秒的缓冲
                return i

        return None

    def _format_time(self, seconds: float) -> str:
        """将秒数转换为 ASS 时间格式 H:MM:SS.cc"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        centisecs = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _convert_color(self, color: str) -> str:
        """将颜色转换为 ASS 格式（BGR）"""
        try:
            # 移除可能的前缀
            color = color.replace('#', '').replace('0x', '')

            # 如果是十进制，转换为十六进制
            if color.isdigit():
                color = hex(int(color))[2:].zfill(6)

            # 确保是6位十六进制
            color = color.zfill(6)

            # 转换为 BGR 格式
            r = color[0:2]
            g = color[2:4]
            b = color[4:6]
            return f"{b}{g}{r}"
        except:
            return "FFFFFF"  # 默认白色

    def _escape_ass_text(self, text: str) -> str:
        """转义 ASS 特殊字符"""
        text = text.replace('\\', '\\\\')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        text = text.replace('\n', '\\N')
        text = text.replace('\r', '')
        return text


def convert_danmaku_to_ass(input_file: str, output_file: str = None, **kwargs) -> str:
    """
    将弹幕文件转换为 ASS 字幕

    Args:
        input_file: 输入文件路径（XML 或 JSON）
        output_file: 输出文件路径，默认为输入文件同名的 .ass 文件
        **kwargs: 传递给 AssGenerator 的参数

    Returns:
        输出文件路径
    """
    if output_file is None:
        output_file = input_file.rsplit('.', 1)[0] + '.ass'

    generator = AssGenerator(**kwargs)

    if input_file.endswith('.xml'):
        generator.generate_from_xml(input_file, output_file)
    elif input_file.endswith('.json'):
        generator.generate_from_json(input_file, output_file)
    else:
        logger.error(f'不支持的文件格式: {input_file}')
        return None

    return output_file
