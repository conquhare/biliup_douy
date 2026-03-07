# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = [('biliup/Danmaku/douyin_util/', 'biliup/Danmaku/douyin_util/')]
binaries = []
hiddenimports = [
    'biliup.Danmaku',
    'biliup.Danmaku.bilibili',
    'biliup.Danmaku.douyin',
    'biliup.Danmaku.douyu',
    'biliup.Danmaku.huya',
    'biliup.Danmaku.twitcasting',
    'biliup.Danmaku.twitch',
    'biliup.Danmaku.youtube',
    'biliup.engine.download',
    'biliup.engine.upload',
    'biliup.engine.decorators',
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
    a.binaries,
    a.datas,
    [],
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
    onefile=True,  # 单文件模式
)