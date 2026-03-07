# 閮ㄥ垎寮瑰箷鍔熻兘浠ｇ爜鏉ヨ嚜椤圭洰锛歨ttps://github.com/IsoaSFlus/danmaku锛屾劅璋㈠ぇ浣?
# 蹇墜寮瑰箷浠ｇ爜鏉ユ簮鍙婃€濊矾锛歨ttps://github.com/py-wuhao/ks_barrage锛屾劅璋㈠ぇ浣?
# 閮ㄥ垎鏂楅奔褰曟挱淇浠ｇ爜涓庢€濊矾鏉ユ簮浜庯細https://github.com/SmallPeaches/DanmakuRender锛屾劅璋㈠ぇ浣?
# 浠呮姄鍙栫敤鎴峰脊骞曪紝涓嶅寘鎷叆鍦烘彁閱掋€佺ぜ鐗╄禒閫佺瓑銆?

import asyncio
import logging
import os
import re
import ssl
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp
import lxml.etree as etree

from biliup.Danmaku.bilibili import Bilibili
from biliup.Danmaku.douyin import Douyin
from biliup.Danmaku.douyu import Douyu
from biliup.Danmaku.huya import Huya
from biliup.Danmaku.twitcasting import Twitcasting
from biliup.Danmaku.twitch import Twitch

logger = logging.getLogger('biliup')


class IDanmakuClient(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def save(self, file_name: Optional[str] = None):
        pass


class DanmakuClient(IDanmakuClient):
    class WebsocketErrorException(Exception):
        pass

    def __init__(self, url, file_name, content=None):
        # TODO 褰曞埗浠诲姟浜х敓鐨勪笂涓嬫枃淇℃伅 浼犻€掑お楹荤儲浜?闇€瑕佹敼
        self.__content = content if content is not None else {}
        self.__file_name = file_name
        self.__fmt_file_name = None
        self.__url = ''
        self.__site = None
        self.__hs = None
        self.__ws = None
        self.__dm_queue: Optional[asyncio.Queue] = None
        self.__record_task: Optional[asyncio.Task] = None
        self.__print_task: Optional[asyncio.Task] = None
        self.__danmaku_types: Optional[list] = None  # 寮瑰箷绫诲瀷绛涢€?
        self.__initial_danmaku_buffer: list = []  # 鍒濆寮瑰箷缂撳啿鍖猴紙鐢ㄤ簬寮€濮嬪綍鍒舵椂鎵撳嵃锛?
        self.__buffer_start_time: float = 0  # 缂撳啿鍖哄紑濮嬫椂闂?

        if 'http://' == url[:7] or 'https://' == url[:8]:
            self.__url = url
        else:
            self.__url = 'http://' + url
        for u, s in {'douyu.com': Douyu,
                     'huya.com': Huya,
                     'live.bilibili.com': Bilibili,
                     'twitch.tv': Twitch,
                     'douyin.com': Douyin,
                     'twitcasting.tv': Twitcasting
                     }.items():
            if re.match(r'^(?:http[s]?://)?.*?%s/(.+?)$' % u, url):
                self.__site = s
                self.__u = u
                break

        if self.__site is None:
            # 鎶涘嚭寮傚父鐢卞閮ㄥ鐞?exit()浼氬鑷磋繘绋嬮€€鍑?
            raise Exception(f"{DanmakuClient.__name__}:{self.__url}: 涓嶆敮鎸佸綍鍒跺脊骞?)
        
        # 鑾峰彇寮瑰箷绫诲瀷绛涢€夐厤缃?
        self.__danmaku_types = self.__content.get('danmaku_types')

    async def __init_ws(self):
        try:
            ws_url, reg_datas = await self.__site.get_ws_info(self.__url, self.__content)
            ctx = ssl.create_default_context()
            ctx.set_ciphers('DEFAULT')
            self.__ws = await self.__hs.ws_connect(ws_url, ssl_context=ctx, headers=getattr(self.__site, 'headers', {}))
            for reg_data in reg_datas:
                if type(reg_data) == str:
                    await self.__ws.send_str(reg_data)
                else:
                    await self.__ws.send_bytes(reg_data)
        except asyncio.CancelledError:
            raise
        except:
            raise self.WebsocketErrorException()

    async def __heartbeats(self):
        if self.__site.heartbeat is not None or hasattr(self.__site, 'get_heartbeat'):
            while True:
                # 姣忛殧杩欎箞闀挎椂闂村彂閫佷竴娆″績璺冲寘
                await asyncio.sleep(self.__site.heartbeatInterval)
                # 鍙戦€佸績璺冲寘
                heartbeat = self.__site.heartbeat
                # 濡傛灉绔欑偣鏈夊姩鎬佸績璺冲寘鐢熸垚鏂规硶锛屼娇鐢ㄨ鏂规硶
                if hasattr(self.__site, 'get_heartbeat'):
                    heartbeat = self.__site.get_heartbeat()
                if heartbeat is None:
                    continue
                if type(heartbeat) == str:
                    await self.__ws.send_str(heartbeat)
                else:
                    await self.__ws.send_bytes(heartbeat)

    async def __fetch_danmaku(self):
        while True:
            # 浣跨敤 async for msg in self.__ws
            # 浼氬鑷村湪杩炴帴鏂紑鏃?闇€瑕佸緢闀挎椂闂?5min鎴栬€呮洿澶氭墠鑳芥娴嬪埌
            msg = await self.__ws.receive()

            if msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                # 杩炴帴鍏抽棴鐨勫紓甯?浼氬埌澶栧眰缁熶竴澶勭悊
                raise self.WebsocketErrorException()

            try:
                result = self.__site.decode_msg(msg.data)

                if isinstance(result, tuple):
                    ms, ack = result
                    if ack is not None:
                        # 鍙戦€乤ck鍖?
                        if type(ack) == str:
                            await self.__ws.send_str(ack)
                        else:
                            await self.__ws.send_bytes(ack)
                else:
                    ms = result

                for m in ms:
                    await self.__dm_queue.put(m)
            except asyncio.CancelledError:
                raise
            except:
                logger.exception(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷鎺ユ敹寮傚父")
                continue
                # await asyncio.sleep(10) 鏃犻渶绛夊緟 鐩存帴鑾峰彇涓嬩竴鏉ebsocket娑堟伅
                # 杩欓噷鍑虹幇寮傚父鍙細鏄?decode_msg 鐨勯棶棰?

    def _should_record_danmaku(self, msg_type: str) -> bool:
        """
        妫€鏌ユ槸鍚﹀簲璇ュ綍鍒惰绫诲瀷鐨勫脊骞?
        
        Args:
            msg_type: 娑堟伅绫诲瀷
            
        Returns:
            bool: 鏄惁搴旇褰曞埗
        """
        # 濡傛灉娌℃湁閰嶇疆绫诲瀷绛涢€夛紝鍒欏綍鍒舵墍鏈夌被鍨?
        if not self.__danmaku_types:
            return True
        # 妫€鏌ユ秷鎭被鍨嬫槸鍚﹀湪閰嶇疆鐨勫垪琛ㄤ腑
        return msg_type in self.__danmaku_types

    async def __print_danmaku(self):
        def write_file(filename):
            try:
                if filename and msg_i > 0:
                    tree.write(filename, encoding="UTF-8", xml_declaration=True, pretty_print=True)
            except:
                logger.warning(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷鍐欏叆寮傚父", exc_info=True)

        while True:
            root = etree.Element("i")
            etree.indent(root, "\t")
            tree = etree.ElementTree(root, parser=etree.XMLParser(recover=True))
            start_time = time.time()
            self.__buffer_start_time = start_time  # 璁板綍缂撳啿鍖哄紑濮嬫椂闂?
            fmt_file_name = time.strftime(self.__file_name.encode("unicode-escape").decode()).encode().decode(
                "unicode-escape") + '.xml'
            msg_i = 0
            self.__initial_danmaku_buffer = []  # 娓呯┖鍒濆寮瑰箷缂撳啿鍖?
            initial_buffer_logged = False  # 鏄惁宸茶褰曞垵濮嬪脊骞?

            # 璁剧疆寮瑰箷鑷姩淇濆瓨鏃堕棿
            last_save_time = int(start_time)
            if self.__content.get("raw", False):
                save_interval = 300
            else:
                save_interval = 10

            try:
                while True:
                    try:
                        # 鏃犲脊骞曟椂鏇村揩鍒嗘缁撴潫
                        m = await asyncio.wait_for(self.__dm_queue.get(), timeout=1)
                    except asyncio.TimeoutError:
                        continue

                    msg_type = m.get("msg_type")
                    msg_time = time.time()
                    logger.debug(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷queue-{msg_type}")
                    
                    # 妫€鏌ユ槸鍚﹂渶瑕佽褰曞垵濮嬪脊骞曪紙寮€濮嬪悗5绉掑唴锛?
                    if not initial_buffer_logged and msg_time - start_time <= 5:
                        if msg_type not in ['save', 'stop']:
                            self.__initial_danmaku_buffer.append(m)
                    elif not initial_buffer_logged and msg_time - start_time > 5:
                        # 瓒呰繃5绉掞紝璁板綍鍒濆寮瑰箷
                        if self.__initial_danmaku_buffer:
                            danmaku_summary = []
                            for dm in self.__initial_danmaku_buffer[:10]:  # 鏈€澶氭樉绀?0鏉?
                                dm_type = dm.get('msg_type', 'unknown')
                                dm_name = dm.get('name', '鏈煡鐢ㄦ埛')
                                dm_content = dm.get('content', '')
                                if len(dm_content) > 20:
                                    dm_content = dm_content[:20] + '...'
                                danmaku_summary.append(f"[{dm_type}]{dm_name}: {dm_content}")
                            logger.info(f"{DanmakuClient.__name__}:{self.__url}: 鍒濆寮瑰箷璁板綍 ({len(self.__initial_danmaku_buffer)}鏉?: " + 
                                      " | ".join(danmaku_summary))
                        initial_buffer_logged = True
                    
                    # 闈炲脊骞?
                    if msg_type == "save":
                        if 'file_name' in m and fmt_file_name != m['file_name']:
                            try:
                                if os.path.exists(m['file_name']):
                                    os.remove(m['file_name'])
                                if os.path.exists(fmt_file_name):
                                    os.rename(fmt_file_name, m.get('file_name'))
                                    logger.info(
                                        f"{DanmakuClient.__name__}:{self.__url}: 鏇村悕 {fmt_file_name} 涓?{m['file_name']}")
                            except:
                                logger.exception(
                                    f"{DanmakuClient.__name__}:{self.__url}: 鏇村悕 {fmt_file_name} 涓?{m['file_name']}澶辫触")
                            fmt_file_name = m['file_name']

                        if callable(m.get('callback')):
                            m['callback']()
                        break
                    elif msg_type == "stop":
                        try:
                            os.remove(fmt_file_name)
                        except:
                            pass
                        fmt_file_name = None
                        self.__record_task.cancel()
                        return
                    else: # 姝ｅ父寮瑰箷
                        # 妫€鏌ュ脊骞曠被鍨嬫槸鍚﹂渶瑕佸綍鍒?
                        if not self._should_record_danmaku(msg_type):
                            continue
                        
                        # 瀹屾暣寮瑰箷璁板綍
                        if self.__content.get("raw", False):
                            try:
                                o = etree.SubElement(root, 'o')
                                o.set('timestamp', str(int(msg_time)))
                                o.text = m.get("raw_data")
                            except:
                                logger.warning(f"{DanmakuClient.__name__}:{self.__url}:寮瑰箷澶勭悊寮傚父", exc_info=True)
                                continue

                        # 姝ｅ父寮瑰箷璁板綍
                        if msg_type == 'danmaku': # 鏂囧瓧寮瑰箷
                            try:
                                if m.get('color'):
                                    color = m["color"]
                                else:
                                    color = '16777215'
                                msg_time_since_start = format(msg_time - start_time, '.3f')
                                # 璁板綍寮瑰箷棰濆淇℃伅
                                timestamp = str(int(msg_time))
                                uid = str(m.get("uid",0))
                                d = etree.SubElement(root, 'd')
                                '''
                                寮瑰箷閮ㄥ垎鐨勫弬鏁板吋瀹筨ilibili涓荤珯寮瑰箷 XML 鏂囦欢锛屾寜椤哄簭鍚箟鍒嗗埆涓猴細
                                1.寮瑰箷鍑虹幇鏃堕棿 (绉?
                                2.寮瑰箷绫诲瀷
                                3.瀛楀彿
                                4.棰滆壊
                                5.鍙戦€佹椂闂存埑
                                6.鍥哄畾涓?0 (涓荤珯寮瑰箷 XML 涓哄脊骞曟睜 ID)
                                7.鍙戦€佽€?UID (涓荤珯寮瑰箷 XML 涓哄彂閫佺敤鎴?ID 鐨?CRC32)
                                8.鍥哄畾涓?0 (涓荤珯寮瑰箷 XML 涓哄脊骞曠殑鏁版嵁搴?ID)
                                '''
                                d.set('p', f"{msg_time_since_start},1,25,{color},{timestamp},0,{uid},0")
                                if self.__content.get("detail", False):
                                    d.set('timestamp', timestamp)
                                    d.set('uid',uid)
                                    #鍏煎DanmakuFactory鐢ㄦ埛鍚嶈瘑鍒?
                                    d.set('user', m.get("name",""))
                                d.text = m["content"]
                            except:
                                logger.warning(f"{DanmakuClient.__name__}:{self.__url}:寮瑰箷澶勭悊寮傚父", exc_info=True)
                                # 寮傚父鍚庣暐杩囨湰娆″脊骞?
                                continue
                        # 绀肩墿淇℃伅璁板綍锛屾敮鎸佷笂鑸般€丼C銆佺ぜ鐗╋紝鐩墠浠呭湪B绔欏紑鍚?
                        elif self.__u == 'live.bilibili.com' and msg_type in ['gift', 'super_chat' , 'guard_buy']:
                            if not self.__content.get("detail", False):
                                continue
                            try:
                                s = etree.SubElement(root, 's')
                                s.set('timestamp', str(int(msg_time)))
                                s.set('uid', str(m.get("uid")))
                                s.set('username', m.get("name",""))
                                s.set('price', str(m.get("price")))
                                s.set('type', msg_type)
                                # 绀肩墿鍚嶇О
                                s.set('num', str(m.get('num')))
                                s.set('giftname', m.get('gift_name'))
                                s.text = m["content"]
                            except:
                                logger.warning(f"{DanmakuClient.__name__}:{self.__url}:寮瑰箷澶勭悊寮傚父", exc_info=True)
                                # 寮傚父鍚庣暐杩囨湰娆″脊骞?
                                continue
                        else:
                            # 濡傛灉鏈紑鍚簡鍘熷寮瑰箷锛屽垯璺宠繃鏈寰幆
                            if not self.__content.get("raw", False):
                                continue
                        msg_i += 1

                    # 姣忛殧鎸囧畾鏃堕棿鎺ュ叆涓€娆″脊骞?
                    time_since_last_save = int(msg_time) - last_save_time
                    if msg_i > 0 and time_since_last_save >= save_interval:
                        logger.debug(f'{DanmakuClient.__name__}:{self.__url}: 鍐欏叆寮瑰箷')
                        write_file(fmt_file_name)
                        last_save_time = int(msg_time)
                        msg_i = 0
                    # else: # 寮瑰箷鏈啓鍏ュ師鍥?
                    #     print(f"time_since_last_save: {time_since_last_save}, msg_i: {msg_i}")
            finally:
                # 鍙戠敓寮傚父(琚彇娑?鏃跺啓鍏?閬垮厤涓㈠け鏈啓鍏?
                logger.debug(f'{DanmakuClient.__name__}:{self.__url}:寮瑰箷淇濆簳鍐欏叆')
                write_file(fmt_file_name)

    def start(self):
        init_event = threading.Event()

        async def __init():
            logger.info(f'寮€濮嬪脊骞曞綍鍒? {self.__url}')
            self.__record_task = asyncio.create_task(self.__run())
            init_event.set()
            try:
                await self.__record_task
            except asyncio.CancelledError:
                pass
            self.__record_task = None
            logger.info(f'缁撴潫寮瑰箷褰曞埗: {self.__url}')

        threading.Thread(target=asyncio.run, args=(__init(),)).start()
        # 绛夊緟鍒濆鍖栧畬鎴愰伩鍏嶆湭鍒濆鍖栧畬鎴愮殑鏃跺€欏氨鍋滄浠诲姟
        init_event.wait()

    def save(self, file_name: Optional[str] = None):
        if self.__record_task:
            logger.debug(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷save")
            init_event = threading.Event()
            self.__dm_queue.put_nowait({
                "msg_type": "save",
                "file_name": file_name,
                "callback": lambda: init_event.set()
            })
            init_event.wait()

    def stop(self):
        if self.__record_task:
            logger.info(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷stop")
            self.__dm_queue.put_nowait({
                "msg_type": "stop",
            })

    async def __run(self):
        try:
            self.__dm_queue = asyncio.Queue()
            self.__hs = aiohttp.ClientSession()
            self.__print_task = asyncio.create_task(self.__print_danmaku())
            while True:
                danmaku_tasks = []
                try:
                    await self.__init_ws()
                    danmaku_tasks = [asyncio.create_task(self.__heartbeats()),
                                     asyncio.create_task(self.__fetch_danmaku())]
                    await asyncio.gather(*danmaku_tasks)
                except asyncio.CancelledError:
                    raise
                except self.WebsocketErrorException:
                    # 杩炴帴鏂紑绛?0绉掗噸杩?
                    # 鍦ㄥ叧闂箣鍓嶄竴鐩撮噸璇?
                    if self.__u == 'live.bilibili.com' and self.__content['uid'] != 0:
                        self.__content['uid'] = 0
                        logger.warning(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷杩炴帴寮傚父,闄嶇骇鑷抽潪瀹屾暣寮瑰箷")
                        continue
                    logger.warning(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷杩炴帴寮傚父,灏嗗湪 30 绉掑悗閲嶈瘯", exc_info=True)
                except:
                    # 璁板綍寮傚父涓嶅埌澶栭儴澶勭悊
                    logger.exception(f"{DanmakuClient.__name__}:{self.__url}: 寮瑰箷寮傚父,灏嗗湪 30 绉掑悗閲嶈瘯")
                finally:
                    if danmaku_tasks:
                        for danmaku_task in danmaku_tasks:
                            danmaku_task.cancel()
                        await asyncio.wait(danmaku_tasks)
                    if self.__ws is not None and not self.__ws.closed:
                        await self.__ws.close()
                await asyncio.sleep(30)
        finally:
            if self.__print_task:
                self.__print_task.cancel()
                await asyncio.wait([self.__print_task])
            if self.__hs:
                await self.__hs.close()

# 铏庣墮鐩存挱锛歨ttps://www.huya.com/lpl
# 鏂楅奔鐩存挱锛歨ttps://www.douyu.com/9999

