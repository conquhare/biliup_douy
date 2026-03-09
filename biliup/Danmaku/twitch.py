import logging
import random
import re

from .danmaku_client import BaseDanmakuClient

logger = logging.getLogger('biliup')


class Twitch:
    heartbeat = "PING"
    heartbeatInterval = 40

    @staticmethod
    async def get_ws_info(url, context):
        reg_datas = []
        room_id = re.search(r"/([^/?]+)[^/]*$", url).group(1)

        reg_datas.append("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership")
        reg_datas.append("PASS SCHMOOPIIE")
        nick = f"justinfan{int(8e4 * random.random() + 1e3)}"
        reg_datas.append(f"NICK {nick}")
        reg_datas.append(f"USER {nick} 8 * :{nick}")
        reg_datas.append(f"JOIN #{room_id}")

        return "wss://irc-ws.chat.twitch.tv", reg_datas

    @staticmethod
    def decode_msg(data):
        msgs = []
        if data is not None:
            for d in data.splitlines():
                msgt = {}
                try:
                    msgt["content"] = re.search(r"PRIVMSG [^:]+:(.+)", d).group(1)
                    msgt["name"] = re.search(r"display-name=([^;]+);", d).group(1)
                    # if msgt["content"][0] == '@': continue # 涓㈡帀琛ㄦ儏绗﹀彿
                    c = re.search(r"color=#([a-zA-Z0-9]{6});", d).group(1)
                    msgt["color"] = int(c, 16)
                    msgt["msg_type"] = "danmaku"
                    # print(msgt)
                    msgs.append(msgt)
                except Exception:
                    pass
        return msgs


class DanmakuClient(BaseDanmakuClient):
    """Twitch弹幕客户端"""

    def __init__(self, url: str, filename: str):
        super().__init__(url, filename)
        self.heartbeat = Twitch.heartbeat.encode() if Twitch.heartbeat else None
        self.heartbeatInterval = Twitch.heartbeatInterval

    async def get_ws_info(self, url: str, context: dict) -> tuple:
        """获取WebSocket连接信息"""
        return await Twitch.get_ws_info(url, context)

    def decode_msg(self, data: bytes) -> tuple:
        """解码弹幕消息"""
        return Twitch.decode_msg(data.decode('utf-8')), None
