from typing import Optional
from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse

import requests
import random

from ..common.util import client
from ..Danmaku import DanmakuClient
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
        self.douyin_danmaku_types = config.get('douyin_danmaku_types', None)  # 寮瑰箷类型绛涢€?
        self.fake_headers['cookie'] = config.get('user', {}).get('douyin_cookie', '')
        self.__web_rid = None # 缃戦〉绔埧闂村彿 鎴?鎶栭煶鍙?
        self.__room_id = None # 鍗曞満直播鐨勭洿鎾埧闂?
        self.__sec_uid = None

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
                else:
                    raise
            except:
                logger.error(f"{self.plugin_msg}: 涓嶆敮鎸佺殑閾炬帴")
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
                        logger.debug(f"{self.plugin_msg}: 未开鎾?)
                        return False
                    self.__web_rid = web_rid
                except (KeyError, IndexError):
                    logger.error(f"{self.plugin_msg}: 鎴块棿鍙疯幏鍙栧け璐ワ紝璇锋鏌ookie设置")
                    return False
                except:
                    logger.exception(f"{self.plugin_msg}: 鎴块棿鍙疯幏鍙栧け璐?)
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
                        if _room_info['data'].get('prompts', '') == '直播已结鏉?:
                            return False
                        # 可能鏄敤鎴疯灏佺
                        raise Exception(f"{str(_room_info)}")
                    self.__sec_uid = _room_info['data']['user']['sec_uid']
            # PCWeb 绔棤娴?鎴?没有鎻愪緵 web_rid
            if not _room_info.get('data', {}).get('data'):
                _room_info = await self.get_h5_room_info(self.__sec_uid, self.__room_id)
                if _room_info['data'].get('room', {}).get('owner'):
                    self.__web_rid = _room_info['data']['room']['owner']['web_rid']
            try:
                # 鍑虹幇寮傚父涓嶇敤鎻愮ず锛岀洿鎺ュ埌 移动缃戦〉 绔幏鍙?
                room_info = _room_info['data']['data'][0]
            except (KeyError, IndexError):
                # 濡傛灉 移动缃戦〉 绔篃没有数据锛屽綋鍋氭湭寮€鎾鐞?
                room_info = _room_info['data'].get('room', {})
                # 褰撳仛未开鎾鐞?
                # if not room_info:
                #     logger.info(f"{self.plugin_msg}: 获取直播闂翠俊鎭け璐?{_room_info}")
            if room_info.get('status') != 2:
                logger.debug(f"{self.plugin_msg}: 未开鎾?)
                return False
            self.__room_id = room_info['id_str']
            self.room_title = room_info['title']
        except:
            logger.exception(f"{self.plugin_msg}: 获取直播闂翠俊鎭け璐?)
            return False

        if is_check:
            return True
        else:
            # 清理涓婁竴娆¤幏鍙栫殑直播娴?
            self.raw_stream_url = ""

        try:
            pull_data = room_info['stream_url']['live_core_sdk_data']['pull_data']
            if room_info['stream_url'].get('pull_datas') and self.douyin_double_screen:
                pull_data = next(iter(room_info['stream_url']['pull_datas'].values()))
            stream_data = json_loads(pull_data['stream_data'])['data']
        except:
            logger.exception(f"{self.plugin_msg}: 鍔犺浇直播娴佸け璐?)
            logger.debug(f"{self.plugin_msg}: room_info {room_info}")
            return False

        # 鎶栭煶FLV鐪熷師鐢?
        if (
            self.douyin_true_origin  # 寮€鍚湡鍘熺敾
            and
            self.douyin_quality == 'origin' # 璇锋眰鍘熺敾
            and
            self.douyin_protocol == 'flv' # 璇锋眰FLV
            # and
            # self.raw_stream_url.find('_or4.flv') != -1 # or4(origin)
        ):
            try:
                self.raw_stream_url = stream_data['ao']['main']['flv'].replace('&only_audio=1', '')
            except KeyError:
                logger.debug(f"{self.plugin_msg}: 鏈壘鍒?ao 娴?{stream_data}")

        if not self.raw_stream_url:
            # 鍘熺敾origin 钃濆厜uhd 瓒呮竻hd 楂樻竻sd 鏍囨竻ld 娴佺晠md 浠呴煶棰慳o
            quality_items = ['origin', 'uhd', 'hd', 'sd', 'ld', 'md']
            quality = self.douyin_quality
            if quality not in quality_items:
                quality = quality_items[0]
            try:
                # 濡傛灉没有杩欎釜鐢昏川鍒欏彇鐩歌繎鐨?浼樺厛浣庢竻鏅板害
                if quality not in stream_data:
                    # 鍙€夌殑娓呮櫚搴?鍚嚜韬?
                    optional_quality_items = [x for x in quality_items if x in stream_data.keys() or x == quality]
                    # 鑷韩鍦ㄥ彲閫夋竻鏅板害鐨勪綅缃?
                    optional_quality_index = optional_quality_items.index(quality)
                    # 鑷韩鍦ㄦ墍鏈夋竻鏅板害鐨勪綅缃?
                    quality_index = quality_items.index(quality)
                    # 楂樻竻鏅板害鍋忕Щ
                    quality_left_offset = None
                    # 浣庢竻鏅板害鍋忕Щ
                    quality_right_offset = None

                    if optional_quality_index + 1 < len(optional_quality_items):
                        quality_right_offset = quality_items.index(
                            optional_quality_items[optional_quality_index + 1]) - quality_index

                    if optional_quality_index - 1 >= 0:
                        quality_left_offset = quality_index - quality_items.index(
                            optional_quality_items[optional_quality_index - 1])

                    # 鍙栫浉閭荤殑娓呮櫚搴?
                    if quality_right_offset <= quality_left_offset:
                        quality = optional_quality_items[optional_quality_index + 1]
                    else:
                        quality = optional_quality_items[optional_quality_index - 1]

                protocol = 'hls' if self.douyin_protocol == 'hls' else 'flv'
                self.raw_stream_url = stream_data[quality]['main'][protocol]
            except:
                logger.exception(f"{self.plugin_msg}: 瀵绘壘娓呮櫚搴﹀け璐?)
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
                    'config': self.config,
                    'danmaku_types': self.douyin_danmaku_types  # 浼犻€掑脊骞曠被鍨嬬瓫閫夐厤缃?
                }
                self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), content)
            else:
                logger.error(f"濡傞渶褰曞埗鎶栭煶寮瑰箷锛岃鑷冲皯瀹夎涓€涓?Javascript 瑙ｉ噴鍣ㄣ€傚 pip install quickjs")

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
        Mobile web 鐨?API 信息锛屾捣澶栧彲鑳戒笉鍏佽浣跨敤
        '''
        if not sec_user_id:
            raise ValueError("sec_user_id is None")
        query = {
            'type_id': 0,
            'live_id': 1,
            'version_code': '99.99.99',
            'app_id': 1128,
            'room_id': room_id if room_id else 2, # 蹇呰浣嗕笉鏍￠獙
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
    # 鎶栭煶ttwid
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
            if not DouyinUtils._douyin_ttwid:
                page = requests.get("https://live.douyin.com/1-2-3-4-5-6-7-8-9-0", timeout=15)
                DouyinUtils._douyin_ttwid = page.cookies.get("ttwid")
            return DouyinUtils._douyin_ttwid


    @staticmethod
    def generate_ms_token() -> str:
        '''鐢熸垚闅忔満 msToken'''
        return ''.join(random.choice(DouyinUtils.LONG_CHATSET) for _ in range(184))


    @staticmethod
    def generate_nonce() -> str:
        """鐢熸垚 21 浣嶉殢鏈哄崄鍏繘鍒跺皬鍐?nonce"""
        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(21))


    @staticmethod
    def generate_odin_ttid() -> str:
        """鐢熸垚 160 浣嶉殢鏈哄崄鍏繘鍒跺皬鍐?odin_ttid"""
        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(160))


    @staticmethod
    def build_request_url(url: str, query: Optional[dict] = None) -> str:
        # NOTE: 涓嶈兘鍦ㄧ被绾у埆鍒濆鍖栵紝鍚﹀垯闈為娆＄敓鎴愮殑 abogus 鏈夐棶棰橈紝鍘熷洜鏈煡
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
