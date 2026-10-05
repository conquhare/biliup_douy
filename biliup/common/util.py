import asyncio
import json
import os

import httpx
from datetime import datetime, timezone
import logging
from typing import Optional

try:
    import ssl
    import truststore # type: ignore
except ImportError:
    ssl = None
    truststore = None
    _ssl_context = True
else:
    _ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

DEFAULT_TIMEOUT = httpx.Timeout(
    connect=15.0,
    read=60.0,
    write=60.0,
    pool=15.0,
)
DEFAULT_MAX_RETRIES = 2
DEFAULT_CONNECTION_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=100)

def get_proxy_url() -> Optional[str]:
    """获取统一的代理地址（优先 https，其次 http）

    供 requests / websockets 等需要显式指定代理的客户端使用。
    websockets 库不读取系统代理环境变量，必须显式传入 proxy 参数。

    ⚠️ 不要试图 from biliup.config import config ——
    biliup/config.py 只在源码开发时由插件机制提供，Nuitka 编译出的 exe 里
    **不存在该文件**（已实测：exe 运行目录无 config.py，import 报
    PackageNotFoundError），import 必然失败。exe 场景下代理只能来自环境变量，
    或由插件侧显式下发。
    """
    proxy = (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
             or os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or '').strip()
    if proxy:
        return proxy

    # 回退：扫描已加载模块，找 Rust 注入到插件模块 globals 的 config
    cfg = _find_injected_config()
    if cfg is not None:
        try:
            return (cfg.get('https_proxy') or cfg.get('http_proxy') or '').strip() or None
        except Exception:
            return None
    return None


def _find_injected_config():
    """在 sys.modules 中查找被注入到插件模块全局的 config 对象

    Rust 侧把配置以 `config` 为名注入各插件模块的 globals（download.py 里的
    裸 `config` 即来源于此），而不是提供一个可 import 的 biliup.config 模块。
    """
    import sys as _sys
    cfg = globals().get('config')
    if cfg is not None:
        return cfg
    for mod in list(_sys.modules.values()):
        if mod is None:
            continue
        try:
            cfg = getattr(mod, 'config', None)
        except Exception:
            continue
        if isinstance(cfg, dict) and ('https_proxy' in cfg or 'http_proxy' in cfg
                                       or 'streamers' in cfg):
            return cfg
    return None

def _get_proxy_config():
    """从环境变量获取代理设置

    ⚠️ biliup/config.py 在 Nuitka 编译的 exe 中不存在，这里只依赖环境变量。
    若 exe 需要走代理，用启动脚本注入 HTTP_PROXY/HTTPS_PROXY。
    """
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    cfg = globals().get('config')
    if (not http_proxy or not https_proxy) and cfg is not None:
        try:
            if not http_proxy:
                http_proxy = cfg.get('http_proxy')
            if not https_proxy:
                https_proxy = cfg.get('https_proxy')
        except Exception:
            pass

    mounts = {}
    if http_proxy:
        mounts["http://"] = httpx.AsyncHTTPTransport(proxy=http_proxy)
    if https_proxy:
        mounts["https://"] = httpx.AsyncHTTPTransport(proxy=https_proxy)

    return mounts

client = httpx.AsyncClient(
    http2=False,  # HTTP/2 uses asyncio.locks.Event which binds to event loop, causing RuntimeError across loops
    follow_redirects=True,
    timeout=DEFAULT_TIMEOUT,
    limits=DEFAULT_CONNECTION_LIMITS,
    verify=_ssl_context,
    mounts=_get_proxy_config()
)
loop = asyncio.get_running_loop()
logger = logging.getLogger('biliup')


def update_client_proxy():
    """更新HTTP客户端的代理配置（在配置变更后调用）"""
    global client
    mounts = _get_proxy_config()
    if mounts:
        client = httpx.AsyncClient(
            http2=False,  # HTTP/2 uses asyncio.locks.Event which binds to event loop, causing RuntimeError across loops
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_CONNECTION_LIMITS,
            verify=_ssl_context,
            mounts=mounts
        )
        logger.info(f"HTTP客户端代理配置已更新: {mounts}")


def check_timerange(name):
    try:
        from biliup.config import config
    except ImportError:
        return True
    
    try:
        time_range_str = config['streamers'].get(name, {}).get('time_range')
        if not time_range_str:
            return True
        time_range = json.loads(time_range_str)
        if not isinstance(time_range, (list, tuple)) or len(time_range) != 2:
            return True

        start = datetime.fromisoformat(time_range[0].replace('Z', '+00:00')).time()
        end   = datetime.fromisoformat(time_range[1].replace('Z', '+00:00')).time()
    except Exception as e:
        logger.error(f'parsing time range {e}')
        return True

    now = datetime.now(timezone.utc).time()

    if start <= end:
        return start <= now <= end
