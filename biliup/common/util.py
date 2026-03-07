import asyncio
import json
import os

import httpx
from datetime import datetime, timezone
import logging

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

def _get_proxy_config():
    """浠庣幆澧冨彉閲忔垨配置涓幏鍙栦唬鐞嗚缃?""
    # 浼樺厛浣跨敤鐜鍙橀噺
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    # 濡傛灉鐜鍙橀噺鏈缃紝灏濊瘯浠庨厤缃枃浠朵腑璇诲彇
    if not http_proxy or not https_proxy:
        try:
            from biliup.config import config
            http_proxy = http_proxy or config.get('http_proxy')
            https_proxy = https_proxy or config.get('https_proxy')
        except:
            pass
    
    mounts = {}
    if http_proxy:
        mounts["http://"] = httpx.HTTPTransport(proxy=http_proxy)
    if https_proxy:
        mounts["https://"] = httpx.HTTPTransport(proxy=https_proxy)
    
    return mounts

client = httpx.AsyncClient(
    http2=True,
    follow_redirects=True,
    timeout=DEFAULT_TIMEOUT,
    limits=DEFAULT_CONNECTION_LIMITS,
    verify=_ssl_context,
    mounts=_get_proxy_config()
)
loop = asyncio.get_running_loop()
logger = logging.getLogger('biliup')


def update_client_proxy():
    """更新HTTP瀹㈡埛绔殑浠ｇ悊配置锛堝湪配置鍙樻洿鍚庤皟鐢級"""
    global client
    mounts = _get_proxy_config()
    if mounts:
        client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT,
            limits=DEFAULT_CONNECTION_LIMITS,
            verify=_ssl_context,
            mounts=mounts
        )
        logger.info(f"HTTP瀹㈡埛绔唬鐞嗛厤缃凡更新: {mounts}")


def check_timerange(name):
    from biliup.config import config
    
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

    # Normal interval (e.g. 16:00 鈫?20:00)
    if start <= end:
        return start <= now <= end

    # Cross鈥憁idnight (e.g. 23:00 鈫?04:00)
    return now >= start or now <= end
