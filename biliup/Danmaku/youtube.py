import re, traceback, datetime, base64
import asyncio
import logging
from biliup.plugins import random_user_agent
from .danmaku_client import BaseDanmakuClient

# The core codes for YouTube support are basically from taizan-hokuto/pytchat

logger = logging.getLogger('biliup')

headers = {
    'user-agent': random_user_agent(),
}


class Youtube:
    q = None
    url = ""
    vid = ""
    ctn = ""
    client = None
    stop = False

    @classmethod
    async def run(cls, url, q, client, **kargs):
        from .paramgen import liveparam

        cls.q = q
        cls.url = url
        cls.client = client
        cls.stop = False
        cls.key = "eW91dHViZWkvdjEvbGl2ZV9jaGF0L2dldF9saXZlX2NoYXQ/a2V5PUFJemFTeUFPX0ZKMlNscVU4UTRTVEVITEdDaWx3X1k5XzExcWNXOA=="
        await cls.get_url()
        while cls.stop == False:
            try:
                await cls.get_room_info()
                cls.ctn = liveparam.getparam(cls.vid, cls.cid, 1)
                await cls.get_chat()
            except:
                traceback.print_exc()
                await asyncio.sleep(1)

    @classmethod
    async def stop(cls):
        cls.stop = True

    @classmethod
    async def get_url(cls):
        a = re.search(r"youtube.com/channel/([^/?]+)", cls.url)
        try:
            cid = a.group(1)
            cls.cid = cid
            cls.url = f"https://www.youtube.com/channel/{cid}/videos"
        except:
            a = re.search(r"youtube.com/watch\?v=([^/?]+)", cls.url)
            async with cls.client.request(
                "get", f"https://www.youtube.com/embed/{a.group(1)}"
            ) as resp:
                b = re.search(r'\\"channelId\\":\\"(.{24})\\"', await resp.text())
                cls.cid = b.group(1)
                cls.url = f"https://www.youtube.com/channel/{cls.cid}/videos"

    @classmethod
    async def get_room_info(cls):
        async with cls.client.request("get", cls.url) as resp:
            t = re.search(
                r'"gridVideoRenderer"((.(?!"gridVideoRenderer"))(?!"style":"UPCOMING"))+"label":"(LIVE|LIVE NOW|PREMIERING NOW)"([\s\S](?!"style":"UPCOMING"))+?("gridVideoRenderer"|</script>)',
                await resp.text(),
            ).group(0)
            cls.vid = re.search(r'"gridVideoRenderer".+?"videoId":"(.+?)"', t).group(1)
            # print(cls.vid)

    @classmethod
    async def get_chat_single(cls):
        msgs = []
        data = {
            "context": {
                "client": {
                    "visitorData": "",
                    "userAgent": headers["user-agent"],
                    "clientName": "WEB",
                    "clientVersion": "".join(
                        (
                            "2.",
                            (datetime.datetime.today() - datetime.timedelta(days=1)).strftime(
                                "%Y%m%d"
                            ),
                            ".01.00",
                        )
                    ),
                },
            },
            "continuation": cls.ctn,
        }
        u = f'https://www.youtube.com/{base64.b64decode(cls.key).decode("utf-8")}'
        async with cls.client.request("post", u, headers=headers, json=data) as resp:
            # print(await resp.text())
            j = await resp.json()
            j = j["continuationContents"]
            cont = j["liveChatContinuation"]["continuations"][0]
            if cont is None:
                raise Exception("No Continuation")
            metadata = (
                cont.get("invalidationContinuationData")
                or cont.get("timedContinuationData")
                or cont.get("reloadContinuationData")
                or cont.get("liveChatReplayContinuationData")
            )
            cls.ctn = metadata["continuation"]
            # print(j['liveChatContinuation'].get('actions'))
            for action in j["liveChatContinuation"].get("actions", []):
                try:
                    renderer = action["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]
                    msg = {}
                    msg["name"] = renderer["authorName"]["simpleText"]
                    message = ""
                    runs = renderer["message"].get("runs")
                    for r in runs:
                        if r.get("emoji"):
                            message += r["emoji"].get("shortcuts", [""])[0]
                        else:
                            message += r.get("text", "")
                    msg["content"] = message
                    msg["msg_type"] = "danmaku"
                    msg["color"] = "16777215"
                    msgs.append(msg)
                except:
                    pass

        return msgs

    @classmethod
    async def get_chat(cls):
        while cls.stop == False:
            ms = await cls.get_chat_single()
            if len(ms) != 0:
                interval = 1 / len(ms)
            else:
                await asyncio.sleep(1)
            for m in ms:
                await cls.q.put(m)
                await asyncio.sleep(interval)


class DanmakuClient(BaseDanmakuClient):
    """YouTube弹幕客户端 - 使用轮询方式获取弹幕"""

    def __init__(self, url: str, filename: str):
        super().__init__(url, filename)
        self.heartbeat = None
        self.heartbeatInterval = 30
        self._youtube_task = None
        self._queue = None

    async def start(self):
        """启动YouTube弹幕录制"""
        if self._running:
            return
        self._running = True
        self.start_time = time.time()
        self._queue = asyncio.Queue()

        # 启动YouTube轮询任务
        self._youtube_task = asyncio.create_task(self._run_youtube())

        # 启动消息处理任务
        self._task = asyncio.create_task(self._process_messages())
        logger.info(f'YouTube弹幕录制启动: {self.url}')

    async def stop(self):
        """停止YouTube弹幕录制"""
        self._running = False
        Youtube.stop()
        if self._youtube_task:
            self._youtube_task.cancel()
            try:
                await self._youtube_task
            except asyncio.CancelledError:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f'YouTube弹幕录制停止: {self.url}, 共录制 {len(self.danmaku_list)} 条弹幕')

    async def _run_youtube(self):
        """运行YouTube弹幕获取"""
        import aiohttp
        async with aiohttp.ClientSession() as client:
            await Youtube.run(self.url, self._queue, client)

    async def _process_messages(self):
        """处理从队列获取的弹幕消息"""
        try:
            while self._running:
                try:
                    msg = await asyncio.wait_for(self._queue.get(), timeout=1)
                    await self._process_message(msg)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.exception(f'处理弹幕消息错误: {e}')
        except Exception as e:
            logger.exception(f'弹幕处理循环错误: {e}')

    async def get_ws_info(self, url: str, context: dict) -> tuple:
        """YouTube不使用WebSocket，返回空"""
        return "", []

    def decode_msg(self, data: bytes) -> tuple:
        """YouTube不使用此方式解码"""
        return [], None
