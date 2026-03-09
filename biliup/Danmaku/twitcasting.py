import json

import aiohttp

from biliup.plugins import random_user_agent
from .danmaku_client import BaseDanmakuClient


class Twitcasting:
    heartbeat = None
    fake_headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://twitcasting.tv/",
        "User-Agent": random_user_agent()
    }

    @staticmethod
    async def get_ws_info(url, context):
        async with aiohttp.ClientSession(headers=Twitcasting.fake_headers) as session:
            async with session.post(
                    url="https://twitcasting.tv/eventpubsuburl.php",
                    data={
                        'movie_id': context['movie_id'],
                        'password': context['password']
                    },
                    timeout=5
            ) as resp:
                r_obj = await resp.json()
                url = r_obj['url']
                return url, []

    @staticmethod
    def decode_msg(data):
        msgs = []
        if data is not None:
            for d in data.splitlines():
                if len(d) == 0:
                    continue
                try:
                    d = json.loads(d)[0]
                    msg = {
                        "content": d['message'],
                        "msg_type": "danmaku"
                    }
                    msgs.append(msg)
                except:
                    pass
        return msgs


class DanmakuClient(BaseDanmakuClient):
    """Twitcasting弹幕客户端"""

    def __init__(self, url: str, filename: str):
        super().__init__(url, filename)
        self.heartbeat = None
        self.heartbeatInterval = 30

    async def get_ws_info(self, url: str, context: dict) -> tuple:
        """获取WebSocket连接信息"""
        return await Twitcasting.get_ws_info(url, context)

    def decode_msg(self, data: bytes) -> tuple:
        """解码弹幕消息"""
        return Twitcasting.decode_msg(data.decode('utf-8')), None
