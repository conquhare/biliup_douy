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
    """
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    proxy = https_proxy or http_proxy
    if not proxy:
        try:
            from biliup.config import config
            proxy = config.get('https_proxy') or config.get('http_proxy')
        except Exception:
            proxy = None
    return proxy or None

def _get_proxy_config():
    """从环境变量或配置中获取代理设置"""
    # 优先使用环境变量
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    # 各自独立回退到配置文件：原先用 `if not http_proxy or not https_proxy`
    # 会在只设置了其中一个环境变量时，漏掉另一个配置项
    try:
        from biliup.config import config
        if not http_proxy:
            http_proxy = config.get('http_proxy')
        if not https_proxy:
            https_proxy = config.get('https_proxy')
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
