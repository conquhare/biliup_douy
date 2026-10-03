# 抖音的弹幕录制参考了 https://github.com/LyzenX/DouyinLiveRecorder ?https://github.com/YunzhiYike/live-tool
# 2023.07.14：KNaiFen：这部分代码参了https://github.com/SmallPeaches/DanmakuRender
# 2024.06.22: 添加来自 https://github.com/hua0512/stream-rec 俔后的 webmssdk.js，以计算 signature

import gzip
import logging
import time

import aiohttp

from .danmaku_client import BaseDanmakuClient

# 延迟导入 protobuf 相关模块，避免 Nuitka 编译时内存不足
def _get_protobuf_modules():
    from google.protobuf import json_format
    from .douyin_util.dy_pb2 import ChatMessage, PushFrame, Response
    return json_format, ChatMessage, PushFrame, Response

logger = logging.getLogger('biliup')


class Douyin:

    heartbeat = b':\x02hb'

    heartbeatInterval = 10

    # 最近一次 get_ws_info 构造的握手请求头，由基类 _run() 取用
    last_ws_headers: dict = {}



    @staticmethod

    async def get_ws_info(url, context):

        headers = {

            # 'user-agent': random_user_agent(),

            'Referer': 'https://live.douyin.com/',

            'Cookie': context.get('config', {}).get('user', {}).get('douyin_cookie', '')

        }

        async with aiohttp.ClientSession() as session:

            from biliup.plugins.douyin import DouyinUtils

            from .douyin_util import DouyinDanmakuUtils

            headers['user-agent'] = DouyinUtils.DOUYIN_USER_AGENT



            if "ttwid" not in headers['Cookie']:

                headers['Cookie'] = f'ttwid={DouyinUtils.get_ttwid()};{headers["Cookie"]}'



            USER_UNIQUE_ID = DouyinDanmakuUtils.get_user_unique_id()

            VERSION_CODE = 180800 # https://lf-cdn-tos.bytescm.com/obj/static/webcast/douyin_live/7697.782665f8.js -> a.ry

            WEBCAST_SDK_VERSION = "1.0.14-beta.0" # https://lf-cdn-tos.bytescm.com/obj/static/webcast/douyin_live/7697.782665f8.js -> ee.VERSION

            # logger.info(f"user_unique_id: {USER_UNIQUE_ID}")

            sig_params = {

                "live_id": "1",

                "aid": "6383",

                "version_code": VERSION_CODE,

                "webcast_sdk_version": WEBCAST_SDK_VERSION,

                "room_id": context.get('room_id', ''),

                "sub_room_id": "",

                "sub_channel_id": "",

                "did_rule": "3",

                "user_unique_id": USER_UNIQUE_ID,

                "device_platform": "web",

                "device_type": "",

                "ac": "",

                "identity": "audience"

            }

            signature = DouyinDanmakuUtils.get_signature(DouyinDanmakuUtils.get_x_ms_stub(sig_params))

            # logger.info(f"signature: {signature}")

            # 参数集与端点对齐上游活跃实现（LiukerSun/DouyinDanmu v2.3.1 / 2026-09-30）：
            # 抖音已把 app_name / browser_* / cursor / im_path / internal_ext / tz_name
            # 等字段列为握手必需项，缺失时 WSS 端点直接返回 200 而非 101。
            webcast5_params = {

                "aid": "6383",

                "app_name": "douyin_web",

                "room_id": context.get('room_id', ''),

                "compress": 'gzip',

                "version_code": VERSION_CODE,

                "webcast_sdk_version": WEBCAST_SDK_VERSION,

                "update_version_code": WEBCAST_SDK_VERSION,

                "cookie_enabled": "true",

                "screen_width": "1536",

                "screen_height": "864",

                "browser_online": "true",

                "browser_language": "zh-CN",

                "browser_name": "Mozilla",

                "browser_platform": "Win32",

                "browser_version": "5.0 (Windows NT 10.0; Win64; x64)",

                "tz_name": "Asia/Shanghai",

                # cursor 需随 user_unique_id 与时间戳动态生成
                "cursor": f"d-1_u-1_fh-{USER_UNIQUE_ID}_t-{int(time.time() * 1000)}_r-1",

                "internal_ext": (
                    f"internal_src:dim|wss_push_room_id:{context.get('room_id', '')}"
                    f"|wss_push_did:{USER_UNIQUE_ID}"
                ),

                "host": "https://live.douyin.com",

                "live_id": "1",

                "did_rule": "3",

                "endpoint": "live_pc",

                "support_wrds": "1",

                "user_unique_id": USER_UNIQUE_ID,

                "im_path": "/webcast/im/fetch/",

                "identity": "audience",

                "need_persist_msg_count": "15",

                "heartbeatDuration": "0",

                "device_platform": "web",

                "device_type": "",

                "sub_channel_id": "",

                "sub_room_id": "",

                "signature": signature,

            }

            wss_url = f"wss://webcast100-ws-web-lq.douyin.com/webcast/im/push/v2/?{'&'.join([f'{k}={v}' for k, v in webcast5_params.items()])}"

            url = DouyinUtils.build_request_url(wss_url)

            # 把握手请求头交回给基类：websockets.connect() 必须显式收到 Cookie，
            # 否则抖音服务端拒绝升级连接（返回 200 而非 101）。
            Douyin.last_ws_headers = headers

            return url, []



    @staticmethod

    def decode_msg(data):
        # 运行时动态导入 protobuf 模块
        json_format, ChatMessage, PushFrame, Response = _get_protobuf_modules()

        wss_package = PushFrame()

        wss_package.ParseFromString(data)

        log_id = wss_package.logId

        decompressed = gzip.decompress(wss_package.payload)

        payload_package = Response()

        payload_package.ParseFromString(decompressed)



        ack = None

        if payload_package.needAck:

            obj = PushFrame()

            obj.payloadType = 'ack'

            obj.logId = log_id

            obj.payloadType = payload_package.internalExt

            ack = obj.SerializeToString()



        msgs = []
        for msg in payload_package.messagesList:
            if msg.method == 'WebcastChatMessage':
                chat_message = ChatMessage()
                chat_message.ParseFromString(msg.payload)
                data = json_format.MessageToDict(chat_message, preserving_proto_field_name=True)
                # name = data['user']['nickName']
                content = data['content']
                # print(content)
                # msg_dict = {"time": now, "name": name, "content": content, "msg_type": "danmaku", "color": "ffffff"}
                msg_dict = {"content": content, "msg_type": "danmaku"}
                msgs.append(msg_dict)

        return msgs, ack


class DanmakuClient(BaseDanmakuClient):
    """抖音弹幕客户端"""

    def __init__(self, url: str, filename: str, context: dict = None):
        super().__init__(url, filename, context)
        self.heartbeat = Douyin.heartbeat
        self.heartbeatInterval = Douyin.heartbeatInterval

    async def get_ws_info(self, url: str, context: dict) -> tuple:
        """获取 WebSocket 连接信息"""
        ws_url, reg_datas = await Douyin.get_ws_info(url, context)
        # 把握手请求头（Cookie / UA / Referer）绑定到当前实例，
        # 供基类 _run() 调用 websockets.connect(additional_headers=...) 使用。
        # 缺失 Cookie 时抖音返回 200 而非 101，连接必然失败。
        self.ws_headers = dict(Douyin.last_ws_headers or {})
        return ws_url, reg_datas

    def decode_msg(self, data: bytes) -> tuple:
        """解码弹幕消息"""
        return Douyin.decode_msg(data)

