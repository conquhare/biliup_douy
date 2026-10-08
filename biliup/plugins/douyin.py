import os
import time
from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse

import requests
import random

from ..common.util import client
from ..Danmaku import DanmakuClient, create_processor_from_config
from ..common.abogus import ABogus
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from . import logger, match1, random_user_agent, json_loads, test_jsengine





@Plugin.download(regexp=r'https?://(?:(?:www|m|live|v)\.)?douyin\.com')
class Douyin(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.douyin_danmaku = config.get('douyin_danmaku', False)
        self.douyin_quality = config.get('douyin_quality', 'origin')
        self.douyin_protocol = config.get('douyin_protocol', 'flv')
        self.douyin_double_screen = config.get('douyin_double_screen', False)
        self.douyin_true_origin = config.get('douyin_true_origin', False)
        self.fake_headers['cookie'] = config.get('user', {}).get('douyin_cookie', '')
        self.__web_rid = None
        self.__room_id = None
        self.__sec_uid = None
        # 弹幕处理器
        self.danmaku_processor = None
        if self.douyin_danmaku:
            self.danmaku_processor = create_processor_from_config(config)



    async def acheck_stream(self, is_check=False):



        self.fake_headers['user-agent'] = DouyinUtils.DOUYIN_USER_AGENT

        self.fake_headers['referer'] = "https://live.douyin.com/"



        if self.fake_headers['cookie'] != "" and not self.fake_headers['cookie'].endswith(';'):

            self.fake_headers['cookie'] += ";"

        if "ttwid" not in self.fake_headers['cookie']:

            self.fake_headers['cookie'] += f'ttwid={DouyinUtils.get_ttwid()};'

        if 'odin_ttid=' not in self.fake_headers['cookie']:

            self.fake_headers['cookie'] += f"odin_ttid={DouyinUtils.generate_odin_ttid()};"

        if '__ac_nonce=' not in self.fake_headers['cookie']:

            self.fake_headers['cookie'] += f"__ac_nonce={DouyinUtils.generate_nonce()};"





        if "v.douyin" in self.url:

            try:

                resp = await client.get(self.url, headers=self.fake_headers, follow_redirects=False)

            except:

                return False

            try:

                if resp.status_code not in {301, 302}:

                    raise

                next_url = str(resp.next_request.url)

                if "webcast.amemv" in next_url:

                    self.__sec_uid = match1(next_url, r"sec_user_id=(.*?)&")

                    self.__room_id = match1(next_url.split("?")[0], r"(\d+)")

                elif "isedouyin.com/share/user" in next_url:

                    self.__sec_uid = match1(next_url, r"sec_uid=(.*?)&")

                    # ⚠️ 该分支原先只取 sec_uid，room_id 一直是 None。
                    # 弹幕 WSS 的 room_id 参数为空 → 服务端不推送任何消息，
                    # 表现为「弹幕录制已启动」但 10 分钟内 0 条、无任何报错。
                    # 重定向 URL 里带 room_id，一并提取。
                    rid = match1(next_url, r"room_id=(\d+)") or match1(next_url, r"/(\d{6,})")
                    if rid:
                        self.__room_id = rid

                else:

                    raise

            except:

                logger.error(f"{self.plugin_msg}: ֵ֧")

                return False

        elif "/user/" in self.url:

            sec_uid = self.url.split("user/")[1].split("?")[0]

            if len(sec_uid) in {55, 76}:

                self.__sec_uid = sec_uid

            else:

                try:

                    user_page = (await client.get(self.url, headers=self.fake_headers)).text

                    user_page_data = unquote(

                        user_page.split('<script id="RENDER_DATA" type="application/json">')[1].split('</script>')[0])

                    web_rid = match1(user_page_data, r'"web_rid":"([^"]+)"')

                    if not web_rid:

                        logger.debug(f"{self.plugin_msg}: δ")

                        return False

                    self.__web_rid = web_rid

                except (KeyError, IndexError):

                    logger.error(f"{self.plugin_msg}: ŻȡʧܣCookie")

                    return False

                except:

                    logger.warning(f"[抖音非报错状态日志] {self.plugin_msg}: 获取stream信息失败")

                    return False

        else:

            web_rid = self.url.split('douyin.com/')[1].split('/')[0].split('?')[0]

            if web_rid[0] == "+":

                web_rid = web_rid[1:]

            self.__web_rid = web_rid



        try:

            _room_info = {}

            if self.__web_rid:

                _room_info = await self.get_web_room_info(self.__web_rid)

                if _room_info:

                    if not _room_info['data'].get('user'):

                        if _room_info['data'].get('prompts', '') == 'ֱѽ':

                            return False

                        # û

                        raise Exception(f"{str(_room_info)}")

                    self.__sec_uid = _room_info['data']['user']['sec_uid']

            # PCWeb   ûṩ web_rid

            if not _room_info.get('data', {}).get('data'):

                _room_info = await self.get_h5_room_info(self.__sec_uid, self.__room_id)

                if _room_info['data'].get('room', {}).get('owner'):

                    self.__web_rid = _room_info['data']['room']['owner']['web_rid']

            try:

                # 쳣ʾֱӵ ƶҳ ˻ȡ

                room_info = _room_info['data']['data'][0]

            except (KeyError, IndexError):

                #  ƶҳ Ҳûݣδ

                room_info = _room_info['data'].get('room', {})

                # δ

                # if not room_info:

                #     logger.info(f"{self.plugin_msg}: ȡֱϢʧ {_room_info}")

            if room_info.get('status') != 2:

                logger.debug(f"{self.plugin_msg}: δ")

                return False

            self.__room_id = room_info['id_str']

            self.room_title = room_info['title']

            # ⚠️ 抖音插件此前从不设置 live_cover_url，导致全局 use_live_cover=true
            # 对抖音完全无效且无任何日志（用户以为开了封面，实际从未下载）。
            # 抖音房间信息里封面字段是 cover（dict）或 cover_url。
            cover_info = room_info.get('cover') or {}
            if isinstance(cover_info, dict):
                cover_url = cover_info.get('url_list') or cover_info.get('url')
                if isinstance(cover_url, list) and cover_url:
                    cover_url = cover_url[0]
            else:
                cover_url = room_info.get('cover_url')
            if isinstance(cover_url, str) and cover_url:
                self.live_cover_url = cover_url

        except:

            logger.warning(f"[抖音非报错状态日志] {self.plugin_msg}: 获取直播信息失败 (开播检测中的正常网络波动)")

            return False



        if is_check:

            return True

        else:

            # һλȡֱ

            self.raw_stream_url = ""



        try:

            pull_data = room_info['stream_url']['live_core_sdk_data']['pull_data']

            if room_info['stream_url'].get('pull_datas') and self.douyin_double_screen:

                pull_data = next(iter(room_info['stream_url']['pull_datas'].values()))

            stream_data = json_loads(pull_data['stream_data'])['data']

        except:

            logger.warning(f"[抖音非报错状态日志] {self.plugin_msg}: 直播失败 (服务端返回或网络问题)")

            logger.debug(f"{self.plugin_msg}: room_info {room_info}")

            return False



        # FLVԭ

        if (

            self.douyin_true_origin  # ԭ

            and

            self.douyin_quality == 'origin' # ԭ

            and

            self.douyin_protocol == 'flv' # FLV

            # and

            # self.raw_stream_url.find('_or4.flv') != -1 # or4(origin)

        ):

            try:

                self.raw_stream_url = stream_data['ao']['main']['flv'].replace('&only_audio=1', '')

            except KeyError:

                logger.debug(f"{self.plugin_msg}: δҵ ao  {stream_data}")



        if not self.raw_stream_url:

            # ԭorigin uhd hd sd ld md Ƶao

            quality_items = ['origin', 'uhd', 'hd', 'sd', 'ld', 'md']

            quality = self.douyin_quality

            if quality not in quality_items:

                quality = quality_items[0]

            try:

                # ûȡ ȵ

                if quality not in stream_data:

                    # ѡ

                    optional_quality_items = [x for x in quality_items if x in stream_data.keys() or x == quality]

                    # ڿѡȵλ

                    optional_quality_index = optional_quality_items.index(quality)

                    # ȵλ

                    quality_index = quality_items.index(quality)

                    # ƫ

                    quality_left_offset = None

                    # ƫ

                    quality_right_offset = None



                    if optional_quality_index + 1 < len(optional_quality_items):

                        quality_right_offset = quality_items.index(

                            optional_quality_items[optional_quality_index + 1]) - quality_index



                    if optional_quality_index - 1 >= 0:

                        quality_left_offset = quality_index - quality_items.index(

                            optional_quality_items[optional_quality_index - 1])



                    # ȡڵ

                    if quality_right_offset <= quality_left_offset:

                        quality = optional_quality_items[optional_quality_index + 1]

                    else:

                        quality = optional_quality_items[optional_quality_index - 1]



                protocol = 'hls' if self.douyin_protocol == 'hls' else 'flv'

                self.raw_stream_url = stream_data[quality]['main'][protocol]

            except:

                logger.warning(f"[抖音非报错状态日志] {self.plugin_msg}: 寻找路径失败 (未开播或页面变动)")

                return False



        self.raw_stream_url = self.raw_stream_url.replace('http://', 'https://')

        return True



    def danmaku_init(self):

        if self.douyin_danmaku:

            if (js_runable := test_jsengine()):

                content = {

                    'web_rid': self.__web_rid,

                    'sec_uid': self.__sec_uid,

                    'room_id': self.__room_id,

                    'config': self.config

                }

                # sec_uid 格式房间（douyin.com/user/xxx）的 room_id 在各条解析分支中
                # 都可能缺失，导致弹幕 WSS 的 room_id 参数为空 → 服务端不推消息。
                # 现象：日志显示「弹幕录制已启动」，但长时间 0 条且无任何报错。
                if not self._Douyin__room_id and self._Douyin__sec_uid:
                    self._Douyin__room_id = self._resolve_room_id()

                if not self._Douyin__room_id:
                    logger.warning(
                        f"{self.plugin_msg}: 无法确定 room_id，弹幕可能收不到数据"
                    )

                self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), content)

            else:

                logger.error(f"¼ƶĻٰװһ Javascript  pip install quickjs")

    def _resolve_room_id(self) -> Optional[str]:

        '''通过 H5 接口补齐 room_id（sec_uid 格式房间必需）

        实测：web 接口（/webcast/room/web/enter/）不接受 sec_uid 作 web_rid，
        会返回 {"data":{"message":...,"prompts":...}} 而没有房间信息；
        H5 接口（/webcast/room/reflow/info/）才是按 sec_user_id 定位的正确入口。
        '''

        sec_uid = getattr(self, '_Douyin__sec_uid', None)
        if not sec_uid:
            return None

        loop = asyncio.get_event_loop()

        # H5 接口：room_id 传空，靠 sec_user_id 定位
        try:
            info = loop.run_until_complete(self.get_h5_room_info(sec_uid, ''))
            data = (info or {}).get('data') or {}
            room = data.get('room') or {}
            rid = data.get('room_id') or room.get('id_str')
            if rid:
                logger.debug(f"{self.plugin_msg}: H5 解析到 room_id={rid}")
                return str(rid)
        except Exception as e:
            logger.debug(f"{self.plugin_msg}: H5 接口获取 room_id 失败: {e}")

        # 兜底：web 接口（部分 sec_uid 形态可能有效）
        try:
            info = loop.run_until_complete(self.get_web_room_info(sec_uid))
            data = (info or {}).get('data') or {}
            rid = data.get('room_id') or (data.get('room') or {}).get('id_str')
            if rid:
                return str(rid)
        except Exception as e:
            logger.debug(f"{self.plugin_msg}: web 接口获取 room_id 失败: {e}")

        return None

    def download(self):
        """覆写父类 download 方法，添加直播流地址过期重试机制。
        当 stream_gears 因 403/连接错误等原因下载失败时，自动重新获取流地址并重试。
        """
        max_retries = 2
        import asyncio, time as _time
        for attempt in range(max_retries + 1):
            try:
                return super().download()
            except Exception as e:
                logger.warning(
                    f"{self.plugin_msg}: 下载异常 ({attempt + 1}/{max_retries + 1}): {e}"
                )
                if attempt < max_retries:
                    logger.info(f"{self.plugin_msg}: 重试获取直播流地址...")
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        refreshed = loop.run_until_complete(self.acheck_stream())
                        loop.close()
                        if not refreshed:
                            logger.error(f"{self.plugin_msg}: 获取流地址失败")
                            break
                        logger.info(f"{self.plugin_msg}: 流地址已刷新，3秒后重试")
                    except Exception as re:
                        logger.error(f"{self.plugin_msg}: 刷新流异常: {re}")
                        break
                    _time.sleep(3)
        return False

    def _download_segment_callback(self, file_name: str):
        """
        分段后触发，处理弹幕保存和后续处理
        """

        # 先调用父类的保存弹幕方法

        super()._download_segment_callback(file_name)



        # 如果启用了弹幕处理，进行后续处理

        if self.danmaku_processor and self.douyin_danmaku:

            danmaku_file = os.path.splitext(file_name)[0] + '.xml'

            video_file = file_name

            # ⚠️ 边录边传（sync-downloader）模式下视频不落盘，file_name 恒不存在，
            # 于是 render_video 永远被跳过 —— 而配置里 danmaku_render_video=true，
            # 用户会以为开了功能，实际静默不执行（连一条日志都没有）。
            # 这里显式判断并告知，避免"功能没生效"伪装成"功能不存在"。
            has_video = os.path.exists(video_file)
            if not has_video and getattr(self, 'downloader', None) == 'sync-downloader':
                logger.info(
                    f"{self.plugin_msg}: 边录边传模式视频不落盘，"
                    f"跳过弹幕视频合成（danmaku_render_video 对该模式无效）")

            if os.path.exists(danmaku_file):

                try:

                    logger.info(f"{self.plugin_msg}: 开始处理弹幕文件: {danmaku_file}")

                    results = self.danmaku_processor.process(

                        danmaku_file=danmaku_file,

                        video_file=video_file if has_video else None,

                        progress_callback=self._danmaku_progress_callback

                    )



                    # 记录处理结果

                    if results:

                        if 'ass_file' in results:

                            logger.info(f"{self.plugin_msg}: ASS字幕生成完成: {results['ass_file']}")

                        if 'video_file' in results:

                            logger.info(f"{self.plugin_msg}: 弹幕视频合成完成: {results['video_file']}")

                        if 'energy_file' in results:

                            logger.info(f"{self.plugin_msg}: 高能区域检测完成: {results['energy_file']}")

                except Exception as e:

                    logger.exception(f"{self.plugin_msg}: 弹幕处理失败: {e}")



    def _danmaku_progress_callback(self, stage: str, progress: float):

        """

        弹幕处理进度回调

        """

        if progress < 0:

            logger.error(f"{self.plugin_msg}: 弹幕处理阶段 '{stage}' 失败")

        elif progress == 0:

            logger.info(f"{self.plugin_msg}: 开始弹幕处理阶段: {stage}")

        elif progress == 1:

            logger.info(f"{self.plugin_msg}: 弹幕处理阶段 '{stage}' 完成")

        else:

            logger.debug(f"{self.plugin_msg}: 弹幕处理阶段 '{stage}' 进度: {progress:.1%}")



    async def get_web_room_info(self, web_rid: str) -> dict:

        query = {

            'app_name': 'douyin_web',

            # 'enter_from': random.choice(['link_share', 'web_live']),

            'enter_from': 'web_live',

            'live_id': '1',

            'web_rid': web_rid,

            'is_need_double_stream': "false"

        }

        target_url = DouyinUtils.build_request_url(f"https://live.douyin.com/webcast/room/web/enter/", query)

        logger.debug(f"{self.plugin_msg}: get_web_room_info {target_url}")

        web_info = await client.get(target_url, headers=self.fake_headers)

        web_info = json_loads(web_info.text)

        logger.debug(f"{self.plugin_msg}: get_web_room_info {web_info}")

        return web_info



    async def get_h5_room_info(self, sec_user_id: str, room_id: str) -> dict:

        '''

        Mobile web  API Ϣܲʹ

        '''

        if not sec_user_id:

            raise ValueError("sec_user_id is None")

        query = {

            'type_id': 0,

            'live_id': 1,

            'version_code': '99.99.99',

            'app_id': 1128,

            'room_id': room_id if room_id else 2, # ҪУ

            'sec_user_id': sec_user_id

        }

        abogus = ABogus(user_agent=DouyinUtils.DOUYIN_USER_AGENT)

        query_str, _, _, _ = abogus.generate_abogus(params=urlencode(query, doseq=True), body="")

        # target_url = DouyinUtils.build_request_url(f"https://live.douyin.com/webcast/room/web/enter/", query)

        info = await client.get(

            f"https://webcast.amemv.com/webcast/room/reflow/info/?{query_str}",

            headers=self.fake_headers

        )

        info = json_loads(info.text)

        logger.debug(f"{self.plugin_msg}: get_h5_room_info {info}")

        return info







class DouyinUtils:

    # ttwid

    _douyin_ttwid: Optional[str] = None

    # DOUYIN_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'

    DOUYIN_USER_AGENT = random_user_agent()

    DOUYIN_HTTP_HEADERS = {

        'user-agent': DOUYIN_USER_AGENT

    }

    CHARSET = "abcdef0123456789"

    LONG_CHATSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"



    @staticmethod

    def get_ttwid() -> Optional[str]:

            if DouyinUtils._douyin_ttwid:

                return DouyinUtils._douyin_ttwid

            # ttwid 是抖音下发的访客凭据，WebSocket 握手缺少它会被拒绝升级
            # （服务端返回 200 而非 101）。这里必须带浏览器 UA，并复用全局代理，
            # 否则在需要代理的网络环境下会超时拿不到。
            ua = DouyinUtils.DOUYIN_USER_AGENT

            proxies = DouyinUtils.get_proxies()

            for attempt in range(3):

                try:

                    page = requests.get(

                        "https://live.douyin.com/1-2-3-4-5-6-7-8-9-0",

                        timeout=15,

                        headers={'User-Agent': ua, 'Accept': 'text/html,*/*;q=0.8'},

                        proxies=proxies,

                    )

                    ttwid = page.cookies.get("ttwid")

                    if ttwid:

                        DouyinUtils._douyin_ttwid = ttwid

                        return ttwid

                    logger.warning('[抖音] 未获取到 ttwid，Cookie 缺失将导致弹幕握手失败')

                    return None

                except Exception as e:

                    logger.warning(f'[抖音] 获取 ttwid 失败 (第 {attempt + 1}/3 次): {e}')

                    if attempt < 2:

                        time.sleep(1)

            return None

    @staticmethod

    def get_proxies() -> Optional[dict]:

            '''从全局配置读取代理设置，供 requests 使用

            注意：不要用 from biliup.common.config import global_config ——
            该模块在源码树和 Nuitka 产物中都不存在，会被 except 静默吞掉，
            导致代理始终为 None（表现为 ttwid 获取 / 握手 Read timed out）。
            可靠来源依次为：
              1) 环境变量（启动脚本注入）
              2) stream_gears 注入的模块级 config
            '''

            # 1) 环境变量
            proxy = (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
                     or os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or '').strip()

            # 2) Rust 注入到插件模块全局的 config（download.py 用的就是它）
            if not proxy:

                from biliup.common.util import get_proxy_url

                try:

                    proxy = (get_proxy_url() or '').strip()

                except Exception:

                    proxy = ''

            if not proxy:

                return None

            return {'http': proxy, 'https': proxy}





    @staticmethod

    def generate_ms_token() -> str:

        ''' msToken'''

        return ''.join(random.choice(DouyinUtils.LONG_CHATSET) for _ in range(184))





    @staticmethod

    def generate_nonce() -> str:

        """ 21 λʮСд nonce"""

        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(21))





    @staticmethod

    def generate_odin_ttid() -> str:

        """ 160 λʮСд odin_ttid"""

        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(160))





    @staticmethod

    def build_request_url(url: str, query: Optional[dict] = None) -> str:

        # NOTE: ༶ʼ״ɵ abogus ⣬ԭδ֪

        abogus = ABogus(user_agent=DouyinUtils.DOUYIN_USER_AGENT)

        parsed_url = urlparse(url)

        existing_params = query or parse_qs(parsed_url.query)

        existing_params['aid'] = ['6383']

        existing_params['compress'] = ['gzip']

        existing_params['device_platform'] = ['web']

        existing_params['browser_language'] = ['zh-CN']

        existing_params['browser_platform'] = ['Win32']

        existing_params['browser_name'] = [DouyinUtils.DOUYIN_USER_AGENT.split('/')[0]]

        existing_params['browser_version'] = [DouyinUtils.DOUYIN_USER_AGENT.split(existing_params['browser_name'][0])[-1][1:]]

        if 'msToken' not in existing_params:

            existing_params['msToken'] = [DouyinUtils.generate_ms_token()]

        new_query_string = urlencode(existing_params, doseq=True)

        signed_query_string, _, _, _ = abogus.generate_abogus(params=new_query_string, body="")

        new_url = urlunparse((

            parsed_url.scheme,

            parsed_url.netloc,

            parsed_url.path,

            parsed_url.params,

            signed_query_string,

            parsed_url.fragment

        ))

        return new_url

