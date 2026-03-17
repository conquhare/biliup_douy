#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

if hasattr(sys, 'frozen'):
    import types
    
    def _get_cert_path():
        base_path = os.path.dirname(sys.executable)
        possible_paths = [
            os.path.join(base_path, 'certifi', 'cacert.pem'),
            os.path.join(base_path, 'cacert.pem'),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return ''
    
    _certifi_stub = types.ModuleType('certifi')
    _certifi_stub.__file__ = '<certifi_stub>'
    _certifi_stub.where = _get_cert_path
    _certifi_stub.contents = lambda: open(_get_cert_path(), 'r', encoding='ascii').read() if _get_cert_path() else ''
    sys.modules['certifi'] = _certifi_stub
    
    _core_stub = types.ModuleType('certifi.core')
    _core_stub.where = _get_cert_path
    _core_stub.contents = _certifi_stub.contents
    sys.modules['certifi.core'] = _core_stub
    
    _cert_path = _get_cert_path()
    if _cert_path:
        os.environ['SSL_CERT_FILE'] = _cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = _cert_path

import biliup.common.certifi_patch

import argparse
import asyncio
import logging.config
import shutil

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
