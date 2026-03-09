# 部分弹幕功能代码来自项目：https://github.com/IsoaSFlus/danmaku，感谢大佬
# 快手弹幕代码来源及思路：https://github.com/py-wuhao/ks_barrage，感谢大佬
# 部分斗鱼录播修复代码与思路来源于：https://github.com/SmallPeaches/DanmakuRender，感谢大佬
# 仅抓取用户弹幕，不包括入场提醒、礼物赠送等。

import asyncio
import logging
import os
import re
import ssl

from biliup.config import config

logger = logging.getLogger('biliup')

# 导出弹幕相关功能
from .danmaku_client import BaseDanmakuClient, IDanmakuClient
from .ass_generator import AssGenerator, convert_danmaku_to_ass
from .video_renderer import DanmakuVideoRenderer, render_danmaku_video
from .danmaku_processor import DanmakuProcessor, DanmakuConfig, create_processor_from_config

__all__ = [
    'DanmakuClient',
    'BaseDanmakuClient',
    'IDanmakuClient',
    'AssGenerator',
    'convert_danmaku_to_ass',
    'DanmakuVideoRenderer',
    'render_danmaku_video',
    'DanmakuProcessor',
    'DanmakuConfig',
    'create_processor_from_config',
]


class DanmakuClient:
    def __init__(self, url, filename):
        self.__url = url
        self.__filename = filename
        self.__plugin = None

    async def start(self):
        try:
            from . import huya, douyu, bilibili, douyin, twitch, youtube, twitcasting
        except Exception as e:
            logger.exception(f'导入弹幕库失败: {e}')
            return
        try:
            if 'huya.com' in self.__url:
                self.__plugin = huya.DanmakuClient(self.__url, self.__filename)
            elif 'douyu.com' in self.__url:
                self.__plugin = douyu.DanmakuClient(self.__url, self.__filename)
            elif 'bilibili.com' in self.__url or 'live.bilibili.com' in self.__url:
                self.__plugin = bilibili.DanmakuClient(self.__url, self.__filename)
            elif 'douyin.com' in self.__url:
                self.__plugin = douyin.DanmakuClient(self.__url, self.__filename)
            elif 'twitch.tv' in self.__url:
                self.__plugin = twitch.DanmakuClient(self.__url, self.__filename)
            elif 'youtube.com' in self.__url or 'youtu.be' in self.__url:
                self.__plugin = youtube.DanmakuClient(self.__url, self.__filename)
            elif 'twitcasting.tv' in self.__url:
                self.__plugin = twitcasting.DanmakuClient(self.__url, self.__filename)
            else:
                logger.error(f'不支持的弹幕平台: {self.__url}')
                return
            await self.__plugin.start()
        except Exception as e:
            logger.exception(f'弹幕启动失败: {e}')

    async def stop(self):
        if self.__plugin:
            await self.__plugin.stop()

    def save(self, filename: str):
        """保存弹幕到文件"""
        if self.__plugin:
            self.__plugin.save(filename)
        else:
            logger.warning('弹幕插件未初始化，无法保存')
