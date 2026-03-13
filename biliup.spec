# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata
import certifi

datas = [
    ('biliup/Danmaku/douyin_util/', 'biliup/Danmaku/douyin_util/'),
    # 包含 certifi 的证书文件
    (certifi.where(), 'certifi'),
]
binaries = []
hiddenimports = [
    # Danmaku 模块
    'biliup.Danmaku',
    'biliup.Danmaku.bilibili',
    'biliup.Danmaku.douyin',
    'biliup.Danmaku.douyu',
    'biliup.Danmaku.huya',
    'biliup.Danmaku.twitcasting',
    'biliup.Danmaku.twitch',
    'biliup.Danmaku.youtube',
    'biliup.Danmaku.paramgen',
    'biliup.Danmaku.paramgen.liveparam',
    'biliup.Danmaku.paramgen.arcparam',
    'biliup.Danmaku.paramgen.enc',
    # Engine 模块
    'biliup.engine',
    'biliup.engine.download',
    'biliup.engine.upload',
    'biliup.engine.decorators',
    'biliup.engine.sync_downloader',
    # Common 模块
    'biliup.common',
    'biliup.common.util',
    'biliup.common.log',
    'biliup.common.reload',
    'biliup.common.abogus',
    'biliup.common.Daemon',
    'biliup.common.certifi_patch',
    # Tars 模块
    'biliup.common.tars',
    'biliup.common.tars.core',
    'biliup.common.tars.exception',
    'biliup.common.tars.EndpointF',
    'biliup.common.tars.QueryF',
    # Asyncio 模块 (Windows 需要)
    'asyncio',
    'asyncio.windows_events',
    'asyncio.windows_utils',
    'asyncio.proactor_events',
    'asyncio.base_subprocess',
    # 第三方库
    'lxml.etree',
    'aiohttp',
    'charset_normalizer',
    'chardet',
    'certifi',
    'httpcore',
    'httpx',
    'requests',
]
tmp_ret = collect_all('biliup.plugins')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# datas += copy_metadata('biliup')

a = Analysis(
    ['biliup\\__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,  # 启用字节码优化
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='biliup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 去除符号表，减小体积
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['public\\logo.png'],
    # onefile=False,  # 文件夹模式（解决 DLL 加载问题）
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='biliup',
)
