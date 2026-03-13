#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 首先导入 certifi 补丁（必须在导入 httpx 之前）
import biliup.common.certifi_patch

import argparse
import asyncio
import logging.config
import shutil
import sys

import stream_gears

import biliup.common.reload
# from biliup.config import config
from biliup import __version__, IS_FROZEN, LOG_CONF
from biliup.common.Daemon import Daemon
from biliup.common.log import DebugLevelFilter


def arg_parser():
    logging.config.dictConfig(LOG_CONF)
    logging.getLogger('httpx').addFilter(DebugLevelFilter())

    # Windows PyInstaller 打包后的 asyncio 兼容处理
    if sys.platform == 'win32' and IS_FROZEN:
        # 使用 SelectorEventLoop 替代 ProactorEventLoop 避免 WinError 10022
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())


async def main():
    # from biliup.app import event_manager

    # event_manager.start()

    # 启动时删除临时文件夹
    shutil.rmtree('./cache/temp', ignore_errors=True)
    from biliup.common.util import loop

    await loop.run_in_executor(None, stream_gears.main_loop)



class GracefulExit(SystemExit):
    code = 1


if __name__ == '__main__':
    arg_parser()
