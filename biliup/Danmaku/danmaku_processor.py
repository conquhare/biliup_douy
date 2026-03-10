# 弹幕处理器
# 整合弹幕保存、ASS转换、视频合成、高能检测等功能

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

from .ass_generator import AssGenerator, convert_danmaku_to_ass
from .video_renderer import DanmakuVideoRenderer, render_danmaku_video

logger = logging.getLogger('biliup')


@dataclass
class DanmakuConfig:
    """弹幕功能配置"""
    # 基础功能开关
    enabled: bool = False  # 是否启用弹幕录制
    save_raw: bool = True  # 保存原始弹幕文件(XML/JSON)

    # ASS字幕生成
    generate_ass: bool = False  # 是否生成ASS字幕
    ass_font_name: str = "Microsoft YaHei"  # 字体名称
    ass_font_size: int = 25  # 字体大小
    ass_color: str = "00FFFFFF"  # 弹幕颜色(BGR格式)
    ass_speed: int = 8  # 弹幕速度(像素/帧)
    ass_line_count: int = 12  # 弹幕行数

    # 视频合成
    render_video: bool = False  # 是否合成弹幕视频
    use_gpu: bool = False  # 是否使用GPU加速
    video_codec: str = "libx264"  # 视频编码器
    video_bitrate: Optional[str] = None  # 视频码率
    audio_codec: str = "copy"  # 音频编码器
    preset: str = "medium"  # 编码预设
    crf: int = 23  # 质量因子

    # 高能检测
    detect_high_energy: bool = False  # 是否检测高能区域
    energy_window: int = 30  # 检测窗口大小(秒)
    energy_threshold: float = 0.7  # 高能阈值(0-1)
    min_energy_duration: int = 10  # 最小高能持续时间(秒)

    # 高能进度条
    generate_energy_bar: bool = False  # 是否生成高能进度条
    energy_bar_height: int = 10  # 进度条高度
    energy_bar_color: str = "FF0000"  # 进度条颜色


class DanmakuProcessor:
    """弹幕处理器 - 整合所有弹幕相关功能"""

    def __init__(self, config: DanmakuConfig):
        self.config = config
        self.ass_generator = AssGenerator(
            font_name=config.ass_font_name,
            font_size=config.ass_font_size,
            color=config.ass_color,
            danmaku_speed=config.ass_speed,
            line_count=config.ass_line_count
        )
        self.video_renderer = DanmakuVideoRenderer(
            use_gpu=config.use_gpu,
            gpu_encoder=config.video_codec if config.use_gpu else "h264_nvenc"
        )

    def process(self,
                danmaku_file: str,
                video_file: str = None,
                output_dir: str = None,
                progress_callback = None):
        """
        处理弹幕文件

        Args:
            danmaku_file: 弹幕文件路径(XML/JSON)
            video_file: 视频文件路径(用于合成)
            output_dir: 输出目录
            progress_callback: 进度回调函数(stage, progress)

        Returns:
            处理结果字典，包含生成的文件路径
        """
        results = {}

        if not os.path.exists(danmaku_file):
            logger.error(f'弹幕文件不存在: {danmaku_file}')
            return results

        base_name = Path(danmaku_file).stem
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base_path = os.path.join(output_dir, base_name)
        else:
            base_path = os.path.join(os.path.dirname(danmaku_file), base_name)

        # 1. 生成ASS字幕
        if self.config.generate_ass:
            if progress_callback:
                progress_callback('ass', 0.0)

            ass_file = f"{base_path}.ass"
            try:
                if danmaku_file.endswith('.xml'):
                    self.ass_generator.generate_from_xml(danmaku_file, ass_file)
                elif danmaku_file.endswith('.json'):
                    self.ass_generator.generate_from_json(danmaku_file, ass_file)

                results['ass_file'] = ass_file
                logger.info(f'ASS字幕生成完成: {ass_file}')

                if progress_callback:
                    progress_callback('ass', 1.0)
            except Exception as e:
                logger.exception(f'生成ASS字幕失败: {e}')
                if progress_callback:
                    progress_callback('ass', -1.0)

        # 2. 合成弹幕视频
        if self.config.render_video and video_file and os.path.exists(video_file):
            if progress_callback:
                progress_callback('render', 0.0)

            output_file = f"{base_path}_danmaku.mp4"
            try:
                result = self.video_renderer.render(
                    video_file=video_file,
                    ass_file=results.get('ass_file', f"{base_path}.ass"),
                    output_file=output_file,
                    video_codec=self.config.video_codec,
                    audio_codec=self.config.audio_codec,
                    video_bitrate=self.config.video_bitrate,
                    preset=self.config.preset,
                    crf=self.config.crf
                )

                if result:
                    results['video_file'] = result
                    logger.info(f'弹幕视频合成完成: {result}')

                if progress_callback:
                    progress_callback('render', 1.0)
            except Exception as e:
                logger.exception(f'合成弹幕视频失败: {e}')
                if progress_callback:
                    progress_callback('render', -1.0)

        # 3. 高能检测
        if self.config.detect_high_energy:
            if progress_callback:
                progress_callback('energy', 0.0)

            try:
                energy_regions = self._detect_high_energy_regions(danmaku_file)
                results['energy_regions'] = energy_regions

                # 保存高能区域信息
                energy_file = f"{base_path}_energy.json"
                with open(energy_file, 'w', encoding='utf-8') as f:
                    json.dump(energy_regions, f, ensure_ascii=False, indent=2)
                results['energy_file'] = energy_file

                logger.info(f'高能检测完成，发现 {len(energy_regions)} 个高能区域')

                if progress_callback:
                    progress_callback('energy', 1.0)
            except Exception as e:
                logger.exception(f'高能检测失败: {e}')
                if progress_callback:
                    progress_callback('energy', -1.0)

        # 4. 生成高能进度条视频
        if self.config.generate_energy_bar and video_file and 'energy_regions' in results:
            if progress_callback:
                progress_callback('energy_bar', 0.0)

            try:
                # TODO: 实现高能进度条视频生成
                logger.info('高能进度条功能待实现')

                if progress_callback:
                    progress_callback('energy_bar', 1.0)
            except Exception as e:
                logger.exception(f'生成高能进度条失败: {e}')
                if progress_callback:
                    progress_callback('energy_bar', -1.0)

        return results

    def _detect_high_energy_regions(self, danmaku_file: str):
        """
        检测高能区域

        根据弹幕密度检测直播中的高能时刻
        """
        # 加载弹幕数据
        if danmaku_file.endswith('.xml'):
            danmaku_list = self._load_xml_danmaku(danmaku_file)
        elif danmaku_file.endswith('.json'):
            with open(danmaku_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                danmaku_list = data.get('danmaku_list', [])
        else:
            return []

        if not danmaku_list:
            return []

        # 计算弹幕密度
        window_size = self.config.energy_window
        threshold = self.config.energy_threshold
        min_duration = self.config.min_energy_duration

        # 获取时间范围
        timestamps = [d.get('timestamp', 0) for d in danmaku_list]
        max_time = max(timestamps)

        # 滑动窗口计算密度
        regions = []
        window_start = 0

        while window_start < max_time:
            window_end = window_start + window_size
            count = sum(1 for t in timestamps if window_start <= t < window_end)
            density = count / window_size

            regions.append({
                'start': window_start,
                'end': window_end,
                'count': count,
                'density': density
            })

            window_start += window_size // 2  # 50% 重叠

        # 找出高密度区域
        avg_density = sum(r['density'] for r in regions) / len(regions) if regions else 0
        high_energy_threshold = avg_density * (1 + threshold)

        # 合并相邻的高能区域
        high_energy_regions = []
        current_region = None

        for region in regions:
            if region['density'] >= high_energy_threshold:
                if current_region is None:
                    current_region = {
                        'start': region['start'],
                        'end': region['end'],
                        'count': region['count'],
                        'max_density': region['density']
                    }
                else:
                    current_region['end'] = region['end']
                    current_region['count'] += region['count']
                    current_region['max_density'] = max(current_region['max_density'], region['density'])
            else:
                if current_region is not None:
                    duration = current_region['end'] - current_region['start']
                    if duration >= min_duration:
                        high_energy_regions.append(current_region)
                    current_region = None

        # 处理最后一个区域
        if current_region is not None:
            duration = current_region['end'] - current_region['start']
            if duration >= min_duration:
                high_energy_regions.append(current_region)

        return high_energy_regions

    def _load_xml_danmaku(self, xml_file: str):
        """从XML文件加载弹幕"""
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_file)
        root = tree.getroot()

        danmaku_list = []
        for d in root.findall('d'):
            p_attr = d.get('p', '')
            content = d.text or ''

            p_parts = p_attr.split(',')
            if len(p_parts) >= 4:
                timestamp = float(p_parts[0])
                color = p_parts[3]
                danmaku_list.append({
                    'timestamp': timestamp,
                    'content': content,
                    'color': color
                })

        return danmaku_list


def create_processor_from_config(config: Dict[str, Any]):
    """
    从配置字典创建弹幕处理器

    配置优先级: 主播单独配置 > 平台配置 > 全局配置

    配置项:
    - douyin_danmaku: 是否启用弹幕录制 (平台配置)
    - danmaku_generate_ass: 生成ASS字幕
    - danmaku_render_video: 合成弹幕视频
    - danmaku_use_gpu: 使用GPU加速
    - danmaku_detect_energy: 检测高能区域
    - danmaku_ass_font: ASS字幕字体
    - danmaku_ass_fontsize: 字体大小
    - danmaku_ass_color: 字幕颜色(BGR)
    - danmaku_ass_speed: 弹幕速度
    - danmaku_ass_line_count: 弹幕行数
    - danmaku_video_codec: 视频编码器
    - danmaku_preset: 编码预设
    - danmaku_crf: 质量因子
    - danmaku_energy_window: 检测窗口(秒)
    - danmaku_energy_threshold: 高能阈值
    - danmaku_min_energy_duration: 最小持续时间
    """
    # 检查是否启用弹幕录制
    # 优先检查平台特定配置 (如 douyin_danmaku)
    enabled = config.get('douyin_danmaku', False)

    if not enabled:
        return None

    # 获取配置值，支持主播override配置
    def get_config(key: str, default: Any) -> Any:
        """获取配置值，优先从override获取"""
        # 首先检查override配置
        override = config.get('override', {})
        if isinstance(override, dict):
            if key in override:
                return override[key]
        # 然后检查主配置
        return config.get(key, default)

    danmaku_config = DanmakuConfig(
        enabled=enabled,
        save_raw=get_config('danmaku_save_raw', True),
        generate_ass=get_config('danmaku_generate_ass', False),
        render_video=get_config('danmaku_render_video', False),
        use_gpu=get_config('danmaku_use_gpu', False),
        detect_high_energy=get_config('danmaku_detect_energy', False),
        generate_energy_bar=get_config('danmaku_generate_energy_bar', False),
        ass_font_name=get_config('danmaku_ass_font', 'Microsoft YaHei'),
        ass_font_size=get_config('danmaku_ass_fontsize', 25),
        ass_color=get_config('danmaku_ass_color', '00FFFFFF'),
        danmaku_speed=get_config('danmaku_ass_speed', 8),
        line_count=get_config('danmaku_ass_line_count', 12),
        video_codec=get_config('danmaku_video_codec', 'libx264'),
        preset=get_config('danmaku_preset', 'medium'),
        crf=get_config('danmaku_crf', 23),
        energy_window=get_config('danmaku_energy_window', 30),
        energy_threshold=get_config('danmaku_energy_threshold', 0.7),
        min_energy_duration=get_config('danmaku_min_energy_duration', 10)
    )

    return DanmakuProcessor(danmaku_config)
