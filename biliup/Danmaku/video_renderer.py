# 弹幕视频合成器
# 使用 FFmpeg 将 ASS 字幕渲染到视频上

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger('biliup')


class DanmakuVideoRenderer:
    """弹幕视频合成器"""

    def __init__(self,
                 ffmpeg_path: str = "ffmpeg",
                 use_gpu: bool = False,
                 gpu_encoder: str = "h264_nvenc"):
        """
        初始化视频合成器

        Args:
            ffmpeg_path: FFmpeg 可执行文件路径
            use_gpu: 是否使用 GPU 加速（NVIDIA NVENC）
            gpu_encoder: GPU 编码器名称
        """
        self.ffmpeg_path = ffmpeg_path
        self.use_gpu = use_gpu
        self.gpu_encoder = gpu_encoder

    def render(self,
               video_file: str,
               ass_file: str,
               output_file: str = None,
               **kwargs) -> str:
        """
        将弹幕渲染到视频

        Args:
            video_file: 输入视频文件路径
            ass_file: ASS 字幕文件路径
            output_file: 输出文件路径，默认为视频文件名加上 _danmaku 后缀
            **kwargs: 其他参数
                - video_codec: 视频编码器（默认根据 use_gpu 决定）
                - audio_codec: 音频编码器（默认 copy）
                - video_bitrate: 视频码率
                - audio_bitrate: 音频码率
                - preset: 编码预设
                - crf: 质量因子（CPU编码时有效）

        Returns:
            输出文件路径
        """
        if not os.path.exists(video_file):
            logger.error(f'视频文件不存在: {video_file}')
            return None

        if not os.path.exists(ass_file):
            logger.error(f'字幕文件不存在: {ass_file}')
            return None

        if output_file is None:
            video_path = Path(video_file)
            output_file = str(video_path.parent / f"{video_path.stem}_danmaku{video_path.suffix}")

        # 构建 FFmpeg 命令
        cmd = self._build_ffmpeg_cmd(video_file, ass_file, output_file, kwargs)

        try:
            logger.info(f'开始渲染弹幕视频: {output_file}')
            logger.debug(f'FFmpeg 命令: {" ".join(cmd)}')

            # 执行 FFmpeg 命令
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            if result.returncode != 0:
                logger.error(f'FFmpeg 错误: {result.stderr}')
                return None

            logger.info(f'弹幕视频渲染完成: {output_file}')
            return output_file

        except Exception as e:
            logger.exception(f'渲染弹幕视频失败: {e}')
            return None

    def _build_ffmpeg_cmd(self,
                         video_file: str,
                         ass_file: str,
                         output_file: str,
                         kwargs: Dict[str, Any]) -> list:
        """构建 FFmpeg 命令"""
        cmd = [self.ffmpeg_path, '-y']  # -y 表示覆盖输出文件

        # 输入视频
        cmd.extend(['-i', video_file])

        # 视频滤镜：添加 ASS 字幕
        # 使用双引号包裹字幕文件路径，处理可能包含空格的路径
        ass_filter = f"ass='{ass_file}'"
        cmd.extend(['-vf', ass_filter])

        # 视频编码器
        video_codec = kwargs.get('video_codec')
        if video_codec:
            cmd.extend(['-c:v', video_codec])
        elif self.use_gpu:
            cmd.extend(['-c:v', self.gpu_encoder])
        else:
            cmd.extend(['-c:v', 'libx264'])

        # 音频编码器（默认直接复制）
        audio_codec = kwargs.get('audio_codec', 'copy')
        cmd.extend(['-c:a', audio_codec])

        # 视频码率
        video_bitrate = kwargs.get('video_bitrate')
        if video_bitrate:
            cmd.extend(['-b:v', str(video_bitrate)])

        # 音频码率
        audio_bitrate = kwargs.get('audio_bitrate')
        if audio_bitrate:
            cmd.extend(['-b:a', str(audio_bitrate)])

        # 编码预设
        preset = kwargs.get('preset')
        if preset:
            cmd.extend(['-preset', preset])

        # 质量因子（CPU编码时有效）
        crf = kwargs.get('crf')
        if crf and not self.use_gpu:
            cmd.extend(['-crf', str(crf)])

        # GPU 编码器特定参数
        if self.use_gpu:
            cmd.extend(['-pix_fmt', 'yuv420p'])

        # 输出文件
        cmd.append(output_file)

        return cmd

    def check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def check_gpu_support(self) -> bool:
        """检查是否支持 GPU 加速"""
        if not self.check_ffmpeg():
            return False

        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return self.gpu_encoder in result.stdout
        except:
            return False

    def generate_energy_bar(self,
                           video_file: str,
                           energy_regions: List[Dict[str, Any]],
                           output_file: str = None,
                           bar_height: int = 10,
                           bar_color: str = "FF0000",
                           position: str = "bottom") -> str:
        """
        生成带有高能进度条的视频

        Args:
            video_file: 输入视频文件路径
            energy_regions: 高能区域列表，每个元素包含 start, end, density 等
            output_file: 输出文件路径
            bar_height: 进度条高度（像素）
            bar_color: 进度条颜色（十六进制，如 FF0000 表示红色）
            position: 进度条位置，'top' 或 'bottom'

        Returns:
            输出文件路径
        """
        if not os.path.exists(video_file):
            logger.error(f'视频文件不存在: {video_file}')
            return None

        if not energy_regions:
            logger.warning('没有高能区域数据，跳过进度条生成')
            return None

        if output_file is None:
            video_path = Path(video_file)
            output_file = str(video_path.parent / f"{video_path.stem}_energy_bar{video_path.suffix}")

        try:
            video_duration = self._get_video_duration(video_file)
            if not video_duration:
                logger.error('无法获取视频时长')
                return None

            draw_filter = self._build_energy_bar_filter(
                video_duration=video_duration,
                energy_regions=energy_regions,
                bar_height=bar_height,
                bar_color=bar_color,
                position=position
            )

            cmd = [
                self.ffmpeg_path, '-y',
                '-i', video_file,
                '-vf', draw_filter,
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                output_file
            ]

            logger.info(f'开始生成高能进度条视频: {output_file}')
            logger.debug(f'FFmpeg 命令: {" ".join(cmd)}')

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            if result.returncode != 0:
                logger.error(f'FFmpeg 错误: {result.stderr}')
                return None

            logger.info(f'高能进度条视频生成完成: {output_file}')
            return output_file

        except Exception as e:
            logger.exception(f'生成高能进度条视频失败: {e}')
            return None

    def _get_video_duration(self, video_file: str) -> Optional[float]:
        """获取视频时长（秒）"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_file,
                '-hide_banner',
                '-f', 'null',
                '-'
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            import re
            duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.?\d*)', result.stderr)
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = float(duration_match.group(3))
                return hours * 3600 + minutes * 60 + seconds
        except Exception as e:
            logger.debug(f'获取视频时长失败: {e}')
        return None

    def _build_energy_bar_filter(self,
                                video_duration: float,
                                energy_regions: List[Dict[str, Any]],
                                bar_height: int,
                                bar_color: str,
                                position: str) -> str:
        """
        构建高能进度条 FFmpeg 滤镜

        使用 drawbox 滤镜绘制背景条和高能区域
        """
        bar_y = f"0" if position == "top" else f"h-{bar_height}"

        filter_parts = []

        filter_parts.append(f"drawbox=y={bar_y}:width=iw:height={bar_height}:color=0x333333@0.8:t=fill")

        for region in energy_regions:
            start = region.get('start', 0)
            end = region.get('end', 0)

            start_ratio = start / video_duration if video_duration > 0 else 0
            end_ratio = end / video_duration if video_duration > 0 else 1

            enable_start = start
            enable_end = end

            filter_parts.append(
                f"drawbox=y={bar_y}:width=iw*{end_ratio-start_ratio:.4f}:height={bar_height}:"
                f"color=0x{bar_color}@0.9:t=fill:enable='between(t,{enable_start},{enable_end})'"
            )

        return ",".join(filter_parts)


def render_danmaku_video(video_file: str,
                        danmaku_file: str,
                        output_file: str = None,
                        use_gpu: bool = False,
                        **kwargs) -> str:
    """
    将弹幕文件渲染到视频

    Args:
        video_file: 输入视频文件路径
        danmaku_file: 弹幕文件路径（XML 或 JSON，会自动转换为 ASS）
        output_file: 输出文件路径
        use_gpu: 是否使用 GPU 加速
        **kwargs: 其他参数

    Returns:
        输出文件路径
    """
    from .ass_generator import convert_danmaku_to_ass

    # 如果是 XML 或 JSON 文件，先转换为 ASS
    if danmaku_file.endswith(('.xml', '.json')):
        ass_file = danmaku_file.rsplit('.', 1)[0] + '.ass'
        if not os.path.exists(ass_file):
            ass_file = convert_danmaku_to_ass(danmaku_file, **kwargs)
            if not ass_file:
                return None
    elif danmaku_file.endswith('.ass'):
        ass_file = danmaku_file
    else:
        logger.error(f'不支持的弹幕文件格式: {danmaku_file}')
        return None

    # 渲染视频
    renderer = DanmakuVideoRenderer(use_gpu=use_gpu)
    return renderer.render(video_file, ass_file, output_file, **kwargs)
