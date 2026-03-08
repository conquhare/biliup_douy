锘縡rom typing import Optional
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
        self.douyin_danmaku_types = config.get('douyin_danmaku_types', None)  # 瀵懓绠风被鍨嬬粵娑⑩偓?
        self.fake_headers['cookie'] = config.get('user', {}).get('douyin_cookie', '')
        self.__web_rd = None # 缃戦〉绔埧闂村彿 閹?鎶栭煶閸?
        self.__room_d = None # 閸楁洖婧€鐩存挱閻ㄥ嫮娲块幘顓熷煣闂?
        self.__sec_ud = None

    async def acheck_stream(self, is_check=False):

        self.fake_headers['user-agent'] = DouyinUtils.DOUYIN_USER_AGENT
        self.fake_headers['referer'] = "https://live.douyin.com/"

        if self.fake_headers['cookie'] != "" and not self.fake_headers['cookie'].endswith(';'):
            self.fake_headers['cookie'] += ";"
        if "ttwd" not in self.fake_headers['cookie']:
            self.fake_headers['cookie'] += f'ttwd={DouyinUtils.get_ttwd()};'
        if 'odin_ttd=' not in self.fake_headers['cookie']:
            self.fake_headers['cookie'] += f"odin_ttd={DouyinUtils.generate_odin_ttd()};"
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
                    self.__sec_ud = match1(next_url, r"sec_user_d=(.*?)&")
                    self.__room_d = match1(next_url.split("?")[0], r"(\d+)")
                elif "isedouyin.com/share/user" in next_url:
                    self.__sec_ud = match1(next_url, r"sec_ud=(.*?)&")
                else:
                    raise
            except:
                logger.error(f"{self.plugin_msg}: 娑撳秵鏁幐浣烘畱闁剧偓甯?)
                return False
        elif "/user/" in self.url:
            sec_ud = self.url.split("user/")[1].split("?")[0]
            if len(sec_ud) in {55, 76}:
                self.__sec_ud = sec_ud
            else:
                try:
                    user_page = (await client.get(self.url, headers=self.fake_headers)).text
                    user_page_data = unquote(
                        user_page.split('<script d="RENDER_DATA" type="application/json">')[1].split('</script>')[0])
                    web_rd = match1(user_page_data, r'"web_rd":"([^"]+)"')
                    if not web_rd:
                        logger.debug(f"{self.plugin_msg}: 鏈紑閹?)
                        return False
                    self.__web_rd = web_rd
                except (KeyError, IndexError):
                    logger.error(f"{self.plugin_msg}: 閹村潡妫块崣鐤箯閸欐牕銇戠拹銉礉鐠囬攱顥呴弻顧塷okie璁剧疆")
                    return False
                except:
                    logger.exception(f"{self.plugin_msg}: 閹村潡妫块崣鐤箯閸欐牕銇戠拹?)
                    return False
        else:
            web_rd = self.url.split('douyin.com/')[1].split('/')[0].split('?')[0]
            if web_rd[0] == "+":
                web_rd = web_rd[1:]
            self.__web_rd = web_rd

        try:
            _room_info = {}
            if self.__web_rd:
                _room_info = await self.get_web_room_info(self.__web_rd)
                if _room_info:
                    if not _room_info['data'].get('user'):
                        if _room_info['data'].get('prompts', '') == '鐩存挱宸茬粨閺?:
                            return False
                        # 鍙兘閺勵垳鏁ら幋鐤潶鐏忎胶顩?
                        raise Exception(f"{str(_room_info)}")
                    self.__sec_ud = _room_info['data']['user']['sec_ud']
            # PCWeb 缁旑垱妫ゅù?閹?娌℃湁鎻愪緵 web_rd
            if not _room_info.get('data', {}).get('data'):
                _room_info = await self.get_h5_room_info(self.__sec_ud, self.__room_d)
                if _room_info['data'].get('room', {}).get('owner'):
                    self.__web_rd = _room_info['data']['room']['owner']['web_rd']
            try:
                # 鍑虹幇瀵倸鐖舵稉宥囨暏閹绘劗銇氶敍宀€娲块幒銉ュ煂 绉诲姩缃戦〉 缁旑垵骞忛崣?
                room_info = _room_info['data']['data'][0]
            except (KeyError, IndexError):
                # 濡傛灉 绉诲姩缃戦〉 缁旑垯绡冩病鏈夋暟鎹敍灞界秼閸嬫碍婀鈧幘顓烆槱閻?
                room_info = _room_info['data'].get('room', {})
                # 瑜版挸浠涙湭寮€閹绢厼顦╅悶?
                # if not room_info:
                #     logger.info(f"{self.plugin_msg}: 鑾峰彇鐩存挱闂傜繝淇婇幁顖氥亼鐠?{_room_info}")
            if room_info.get('status') != 2:
                logger.debug(f"{self.plugin_msg}: 鏈紑閹?)
                return False
            self.__room_d = room_info['d_str']
            self.room_title = room_info['title']
        except:
            logger.exception(f"{self.plugin_msg}: 鑾峰彇鐩存挱闂傜繝淇婇幁顖氥亼鐠?)
            return False

        if is_check:
            return True
        else:
            # 娓呯悊娑撳﹣绔村▎陇骞忛崣鏍畱鐩存挱濞?
            self.raw_stream_url = ""

        try:
            pull_data = room_info['stream_url']['live_core_sdk_data']['pull_data']
            if room_info['stream_url'].get('pull_datas') and self.douyin_double_screen:
                pull_data = next(iter(room_info['stream_url']['pull_datas'].values()))
            stream_data = json_loads(pull_data['stream_data'])['data']
        except:
            logger.exception(f"{self.plugin_msg}: 閸旂姾娴囩洿鎾ù浣搞亼鐠?)
            logger.debug(f"{self.plugin_msg}: room_info {room_info}")
            return False

        # 鎶栭煶FLV閻喎甯悽?
        if (
            self.douyin_true_origin  # 瀵偓閸氼垳婀￠崢鐔烘暰
            and
            self.douyin_quality == 'origin' # 璇锋眰閸樼喓鏁?
            and
            self.douyin_protocol == 'flv' # 璇锋眰FLV
            # and
            # self.raw_stream_url.find('_or4.flv') != -1 # or4(origin)
        ):
            try:
                self.raw_stream_url = stream_data['ao']['main']['flv'].replace('&only_audio=1', '')
            except KeyError:
                logger.debug(f"{self.plugin_msg}: 閺堫亝澹橀崚?ao 濞?{stream_data}")

        if not self.raw_stream_url:
            # 閸樼喓鏁緊rigin 閽冩繂鍘渦hd 鐡掑懏绔籬d 妤傛ɑ绔籹d 閺嶅洦绔籰d 濞翠胶鏅爉d 娴犲懘鐓舵０鎱硂
            quality_items = ['origin', 'uhd', 'hd', 'sd', 'ld', 'md']
            quality = self.douyin_quality
            if quality not in quality_items:
                quality = quality_items[0]
            try:
                # 濡傛灉娌℃湁鏉╂瑤閲滈悽鏄忓窛閸掓瑥褰囬惄姝岀箮閻?浼樺厛娴ｅ孩绔婚弲鏉垮
                if quality not in stream_data:
                    # 閸欘垶鈧娈戝〒鍛珰鎼?閸氼偉鍤滈煬?
                    optional_quality_items = [x for x in quality_items if x in stream_data.keys() or x == quality]
                    # 閼奉亣闊╅崷銊ュ讲闁绔婚弲鏉垮閻ㄥ嫪缍呯純?
                    optional_quality_index = optional_quality_items.index(quality)
                    # 閼奉亣闊╅崷銊﹀閺堝绔婚弲鏉垮閻ㄥ嫪缍呯純?
                    quality_index = quality_items.index(quality)
                    # 妤傛ɑ绔婚弲鏉垮閸嬪繒些
                    quality_left_offset = None
                    # 娴ｅ孩绔婚弲鏉垮閸嬪繒些
                    quality_right_offset = None

                    if optional_quality_index + 1 < len(optional_quality_items):
                        quality_right_offset = quality_items.index(
                            optional_quality_items[optional_quality_index + 1]) - quality_index

                    if optional_quality_index - 1 >= 0:
                        quality_left_offset = quality_index - quality_items.index(
                            optional_quality_items[optional_quality_index - 1])

                    # 閸欐牜娴夐柇鑽ゆ畱濞撳懏娅氭惔?
                    if quality_right_offset <= quality_left_offset:
                        quality = optional_quality_items[optional_quality_index + 1]
                    else:
                        quality = optional_quality_items[optional_quality_index - 1]

                protocol = 'hls' if self.douyin_protocol == 'hls' else 'flv'
                self.raw_stream_url = stream_data[quality]['main'][protocol]
            except:
                logger.exception(f"{self.plugin_msg}: 鐎电粯澹樺〒鍛珰鎼达箑銇戠拹?)
                return False

        self.raw_stream_url = self.raw_stream_url.replace('http://', 'https://')
        return True

    def danmaku_init(self):
        if self.douyin_danmaku:
            if (js_runable := test_jsengine()):
                content = {
                    'web_rd': self.__web_rd,
                    'sec_ud': self.__sec_ud,
                    'room_d': self.__room_d,
                    'config': self.config,
                    'danmaku_types': self.douyin_danmaku_types  # 娴肩娀鈧帒鑴婇獮鏇犺閸ㄥ鐡柅澶愬帳缂?
                }
                self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), content)
            else:
                logger.error(f"婵″倿娓惰ぐ鏇炲煑鎶栭煶瀵懓绠烽敍宀冾嚞閼峰啿鐨€瑰顥婃稉鈧稉?Javascript 鐟欙綁鍣撮崳銊ｂ偓鍌氼洤 pip install quickjs")

    async def get_web_room_info(self, web_rd: str) -> dict:
        query = {
            'app_name': 'douyin_web',
            # 'enter_from': random.choice(['link_share', 'web_live']),
            'enter_from': 'web_live',
            'live_d': '1',
            'web_rd': web_rd,
            'is_need_double_stream': "false"
        }
        target_url = DouyinUtils.build_request_url(f"https://live.douyin.com/webcast/room/web/enter/", query)
        logger.debug(f"{self.plugin_msg}: get_web_room_info {target_url}")
        web_info = await client.get(target_url, headers=self.fake_headers)
        web_info = json_loads(web_info.text)
        logger.debug(f"{self.plugin_msg}: get_web_room_info {web_info}")
        return web_info

    async def get_h5_room_info(self, sec_user_d: str, room_d: str) -> dict:
        '''
        Mobile web 閻?API 淇℃伅閿涘本鎹ｆ径鏍у讲閼虫垝绗夐崗浣筋啅浣跨敤
        '''
        if not sec_user_d:
            raise ValueError("sec_user_d is None")
        query = {
            'type_d': 0,
            'live_d': 1,
            'version_code': '99.99.99',
            'app_d': 1128,
            'room_d': room_d if room_d else 2, # 韫囧懓顩︽担鍡曠瑝閺嶏繝鐛?
            'sec_user_d': sec_user_d
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
    # 鎶栭煶ttwd
    _douyin_ttwd: Optional[str] = None
    # DOUYIN_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
    DOUYIN_USER_AGENT = random_user_agent()
    DOUYIN_HTTP_HEADERS = {
        'user-agent': DOUYIN_USER_AGENT
    }
    CHARSET = "abcdef0123456789"
    LONG_CHATSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"

    @staticmethod
    def get_ttwd() -> Optional[str]:
            if not DouyinUtils._douyin_ttwd:
                page = requests.get("https://live.douyin.com/1-2-3-4-5-6-7-8-9-0", timeout=15)
                DouyinUtils._douyin_ttwd = page.cookies.get("ttwd")
            return DouyinUtils._douyin_ttwd


    @staticmethod
    def generate_ms_token() -> str:
        '''閻㈢喐鍨氶梾蹇旀簚 msToken'''
        return ''.join(random.choice(DouyinUtils.LONG_CHATSET) for _ in range(184))


    @staticmethod
    def generate_nonce() -> str:
        """閻㈢喐鍨?21 娴ｅ秹娈㈤張鍝勫磩閸忣叀绻橀崚璺虹毈閸?nonce"""
        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(21))


    @staticmethod
    def generate_odin_ttd() -> str:
        """閻㈢喐鍨?160 娴ｅ秹娈㈤張鍝勫磩閸忣叀绻橀崚璺虹毈閸?odin_ttd"""
        return ''.join(random.choice(DouyinUtils.CHARSET) for _ in range(160))


    @staticmethod
    def build_request_url(url: str, query: Optional[dict] = None) -> str:
        # NOTE: 娑撳秷鍏橀崷銊ц缁狙冨焼閸掓繂顫愰崠鏍电礉閸氾箑鍨棃鐐侯浕濞嗭紕鏁撻幋鎰畱 abogus 閺堝妫舵０姗堢礉閸樼喎娲滈張顏嗙叀
        abogus = ABogus(user_agent=DouyinUtils.DOUYIN_USER_AGENT)
        parsed_url = urlparse(url)
        existing_params = query or parse_qs(parsed_url.query)
        existing_params['ad'] = ['6383']
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
