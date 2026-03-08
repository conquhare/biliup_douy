锘縤mport hashlib
import time
import httpx
import asyncio
from urllib.parse import parse_qs, urlencode, quote
from async_lru import alru_cache
from typing import Union, Any, Optional


from ..common.util import client
from ..Danmaku import DanmakuClient
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger, match1, random_user_agent, json_loads, test_jsengine


DOUYU_DEFAULT_DID = "10000000000000000000000000001501"
DOUYU_WEB_DOMAIN = "www.douyu.com"
DOUYU_PLAY_DOMAIN = "playweb.douyucdn.cn"
DOUYU_MOBILE_DOMAIN = "m.douyu.com"


@Plugin.download(regexp=r'https?://(?:(?:www|m)\.)?douyu\.com')
class Douyu(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.room_d: str = ""
        self.douyu_danmaku = config.get('douyu_danmaku', False)
        self.douyu_disable_interactive_game = config.get('douyu_disable_interactive_game', False)
        self.douyu_cdn = config.get('douyu_cdn', 'hw-h5')
        self.douyu_rate = config.get('douyu_rate', 0)
        # 閺傛澘顤冮敍姘Ц閸氾箑宸遍崚鑸电€?hs-h5 闁剧偓甯撮敍鍫濆祮娴?play_info 杩斿洖閻?rtmp_cdn 瀹歌尙绮￠弰?hs-h5閿?
        self.douyu_force_hs = config.get('douyu_force_hs', False)
        self.__js_runable = test_jsengine()


    async def acheck_stream(self, is_check=False):
        if len(self.url.split("douyu.com/")) < 2:
            logger.error(f"{self.plugin_msg}: 鐩存挱闂村湴鍧€閿欒")
            return False

        self.fake_headers['referer'] = f"https://{DOUYU_WEB_DOMAIN}"

        try:
            self.room_d = str(match1(self.url, r'rd=(\d+)'))
            if not self.room_d.isdigit():
                self.room_d = await get_real_rd(self.url)
        except:
            logger.exception(f"{self.plugin_msg}: 鑾峰彇閹村潡妫块崣鐑芥晩鐠?)
            return False

        for _ in range(3): # 缂傛捁袙 #1376 濞村嘲顦昏姹傚け璐ラ棶棰?
            try:
                room_info = await client.get(
                    f"https://{DOUYU_WEB_DOMAIN}/betard/{self.room_d}",
                    headers=self.fake_headers
                )
                room_info.raise_for_status()
            except httpx.RequestError as e:
                logger.debug(f"{self.plugin_msg}: {e}", exc_info=True)
                continue
            except:
                logger.exception(f"{self.plugin_msg}: 鑾峰彇鐩存挱闂傜繝淇婇幁顖炴晩鐠?)
                return False
            else:
                break
        else:
            logger.error(f"{self.plugin_msg}: 鑾峰彇鐩存挱闂傜繝淇婇幁顖氥亼鐠?)
            return False
        room_info = json_loads(room_info.text)['room']

        if room_info['show_status'] != 1:
            logger.debug(f"{self.plugin_msg}: 鏈紑閹?)
            return False
        if room_info['vdeoLoop'] != 0:
            logger.debug(f"{self.plugin_msg}: 濮濓絽婀弨鎯х秿閹?)
            return False
        if self.douyu_disable_interactive_game:
            gift_info = (
                await client.get(
                    f"https://{DOUYU_WEB_DOMAIN}/api/interactive/web/v2/list?rd={self.room_d}",
                    headers=self.fake_headers
            )).json().get('data', {})
            if gift_info:
                logger.debug(f"{self.plugin_msg}: 濮濓絽婀繍琛屾禍鎺戝З濞撳憡鍨?)
                return False
        self.room_title = room_info['room_name']
        if room_info['isVip'] == 1:
            print(f"isVip: {self.room_d}")
            async with DouyuUtils._lock:
                DouyuUtils.VipRoom.add(self.room_d)

        if is_check:
            return True

        # 閹绘劕鍩?self 娴犮儰绶?hack 鍔熻兘浣跨敤
        self.__req_query = {
            'cdn': self.douyu_cdn,
            'rate': str(self.douyu_rate),
            'ver': 'Douyu_new',
            'iar': '0', # ispreload? 1: 韫囩晫鏆?rate 鍙傛暟閿涘奔濞囬悽銊╃帛鐠併倗鏁剧拹?
            'ive': '0', # rate? 0~19 閺冭翰鈧?9~24 閺冩儼顕Ч鍌涙殶 >=3 娑撹櫣婀?
            'rd': self.room_d,
            'hevc': '0',
            'fa': '0', # isaudio
            'sov': '0', # use wasm?
        }

        for _ in range(2): # 閸忎浇顔忓閲嶈瘯涓€娆′互鍓旈櫎 scdn
            # self.__js_runable = False
            try:
                play_info = await self.aget_web_play_info(self.room_d, self.__req_query)
                if play_info['rtmp_cdn'].startswith('scdn'):
                    new_cdn = play_info['cdnsWithName'][-1]['cdn']
                    logger.debug(f"{self.plugin_msg}: 閸ョ偤浼?scdn 娑?{new_cdn}")
                    self.__req_query['cdn'] = new_cdn
                    continue
            except (RuntimeError, ValueError) as e:
                logger.warning(f"{self.plugin_msg}: {e}")
            except httpx.RequestError as e:
                logger.debug(f"{self.plugin_msg}: {e}", exc_info=True)
            except Exception as e:
                logger.exception(f"{self.plugin_msg}: 閺堫亜顦╅悶鍡欐畱閿欒 {e}閿涘矁鍤滈崝銊╁櫢鐠?)
            else:
                break
        else:
            # Unknown Error
            logger.error(f"{self.plugin_msg}: 鑾峰彇鎾斁淇℃伅澶辫触")
            return False

        self.raw_stream_url = f"{play_info['rtmp_url']}/{play_info['rtmp_live']}"

        return True


    def danmaku_init(self):
        if self.douyu_danmaku:
            content = {
                'room_d': self.room_d,
            }
            self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), content)


    async def aclac_sign(self, rd: Union[str, int]) -> dict[str, Any]:
        '''
        :param rd: 閹村潡妫块崣?
        :return: sign dict
        '''
        if not self.__js_runable:
            raise RuntimeError("jsengine not found")
        try:
            import jsengine
            ctx = jsengine.jsengine()
            h5enc_url = f"https://{DOUYU_WEB_DOMAIN}/swf_api/homeH5Enc?rds={rd}"
            js_enc = (
                await client.get(h5enc_url, headers=self.fake_headers)
            ).json()['data'][f'room{rd}']
            js_enc = js_enc.replace('return eval', 'return [strc, vdwdae325w_64we];')

            sign_fun, sign_v = ctx.eval(f'{js_enc};ub98484234();') # type: ignore

            tt = str(int(time.time()))
            dd = hashlib.md5(tt.encode('utf-8')).hexdigest()
            rb = hashlib.md5(f"{rd}{dd}{tt}{sign_v}".encode('utf-8')).hexdigest()
            sign_fun = sign_fun.rstrip(';').replace("CryptoJS.MD5(cb).toString()", f'"{rb}"')
            sign_fun += f'("{rd}","{dd}","{tt}");'

            params = parse_qs(ctx.eval(sign_fun))

        except Exception as e:
            logger.exception(f"{self.plugin_msg}: 鑾峰彇缁涙儳鎮曞弬鏁板鍌氱埗")
            raise e
        return params


    async def aget_web_play_info(
        self,
        room_d: Union[str, int],
        req_query: dict[str, Any],
        dd: str = DOUYU_DEFAULT_DID,
    ) -> dict[str, Any]:
        '''
        :param room_d: 閹村潡妫块崣?
        :param req_query: 璇锋眰鍙傛暟
        :param dd: douyud
        :return: PlayInfo
        '''
        if type(room_d) == int:
            room_d = str(room_d)

        if self.__js_runable and room_d in DouyuUtils.VipRoom:
            s = await self.aclac_sign(room_d)
            logger.debug(f"{self.plugin_msg}: JSEngine 缁涙儳鎮曞弬鏁?{s}")
            req_query = {
                **req_query,
                **s
            }
            url = f"https://{DOUYU_PLAY_DOMAIN}/lapi/live/getH5Play/{room_d}"
            rsp = await client.get(
                url,
                headers=self.fake_headers,
                params=req_query
            )
        else:
            s = await DouyuUtils.sign(sign_type="stream", ts=int(time.time()), dd=dd, rd=room_d)
            logger.debug(f"{self.plugin_msg}: 閸?JSEngine 缁涙儳鎮曞弬鏁?{s}")
            auth_param = {
                "enc_data": s['key']['enc_data'],
                "tt": s['ts'],
                "dd": dd,
                "auth": s['auth'],
            }
            req_query = {
                **req_query,
                **auth_param,
            }
            url = f"https://{DOUYU_WEB_DOMAIN}/lapi/live/getH5PlayV1/{room_d}"
            rsp = await client.post(
                url,
                headers={**self.fake_headers, 'user-agent': DouyuUtils.UserAgent},
                # params=req_query, # V1 閹恒儱褰涢棁鈧娇鐢ㄩ弻銉嚄鍙傛暟
                data=req_query # 閸樼喐甯撮崣锝夋付浣跨敤璇锋眰娴?
            )

        rsp.raise_for_status()
        play_data = json_loads(rsp.text)
        if not play_data:
            raise RuntimeError(f"鑾峰彇鎾斁淇℃伅澶辫触 {rsp}")
        if (err := play_data['error']) != 0 or not play_data.get('data', {}):
            msg = play_data.get('msg', '')
            if err == -5:
                raise RuntimeError("[closeRoom] 娑撶粯鎸辨湭寮€閹?)
            elif err == -9:
                raise RuntimeError("[room_bus_checksevertime] 鐢ㄦ埛閺堫剚婧€鏃堕棿閹村厖绗夌€?)
            elif err == 126:
                raise RuntimeError(f"閻楀牊娼堥崢鐔锋礈閿涘矁顕氶崷鏉跨厵娑撳秴鍘戠拋鍛婃尡閺€鎾呯窗{msg}")
            else:
                raise RuntimeError(f"鑾峰彇鎾斁淇℃伅閿欒: code={err}, msg={msg}, raw_obj={play_data}")
        return play_data['data']


class DouyuUtils:
    '''
    闁棗鎮滃疄鐜?//shark2.douyucdn.cn/front-publish/live-master/js/player_first_preload_stream/player_first_preload_stream_6cd7aab.js
    鏇存柊    //shark2.douyucdn.cn/front-publish/douyu-web-first-stream-master/web-encrypt-57bbddd0.js
    '''
    WhiteEncryptKey: dict = dict()
    VipRoom: set = set()
    # enc_data 娴兼碍鐗庢?UA
    UserAgent: str = ""
    # 闃叉楠炶泛褰傜拋鍧楁６
    _lock: asyncio.Lock = asyncio.Lock()
    _update_key_event: Optional[asyncio.Event] = None

    @staticmethod
    def is_key_vald(sign_type: str = "stream") -> bool:
        if not DouyuUtils.WhiteEncryptKey:
            return False
        if sign_type == "stream":
            expire_at = DouyuUtils.WhiteEncryptKey.get('expire_at', 0)
        else:
            expire_at = DouyuUtils.WhiteEncryptKey.get('cpp', {}).get('expire_at', 0)
        return expire_at > int(time.time())

    @staticmethod
    async def update_key(
        domain: str = DOUYU_WEB_DOMAIN,
        dd: str = DOUYU_DEFAULT_DID
    ) -> bool:
        # single-flight
        async with DouyuUtils._lock:
            if DouyuUtils._update_key_event is not None:
                evt = DouyuUtils._update_key_event
                leader = False
            else:
                DouyuUtils._update_key_event = asyncio.Event()
                evt = DouyuUtils._update_key_event
                leader = True
        if not leader:
            await evt.wait()
            return DouyuUtils.is_key_vald()

        try:
            DouyuUtils.UserAgent = random_user_agent() # 闂冩煡顥撻幒褝绱濆В蹇旑偧鏇存柊闂呭繑婧€ UA
            rsp = await client.get(
                f"https://{domain}/wgapi/livenc/liveweb/websec/getEncryption",
                params={"dd": dd},
                headers={
                    "User-Agent": DouyuUtils.UserAgent
                },
            )
            rsp.raise_for_status()
            data = json_loads(rsp.text)
            if data['error'] != 0:
                raise RuntimeError(f'getEncryption error: code={data["error"]}, msg={data["msg"]}')
            data['data']['cpp']['expire_at'] = int(time.time()) + 86400

            async with DouyuUtils._lock:
                DouyuUtils.WhiteEncryptKey = data['data']
            return True
        except Exception:
            logger.exception(f"{DouyuUtils.__name__}: 鑾峰彇鍔犲瘑鐎靛棝鎸滃け璐?)
            return False
        finally:
            async with DouyuUtils._lock:
                DouyuUtils._update_key_event.set()
                DouyuUtils._update_key_event = None


    @staticmethod
    async def sign(
        sign_type: str,
        ts: int,
        dd: str,
        rd: Union[str, int],
    ) -> dict[str, Any]:
        '''
        :param sign_type: 缁涙儳鎮曠被鍨嬮敍灞藉讲闁?stream / login / heartbeat
        :param ts: 10娴ｅ硨nix鏃堕棿閹?
        :param dd: douyud
        :param rd: 閹村潡妫块崣?
        '''
        if not rd:
            raise ValueError("rd is None")
        if not sign_type:
            sign_type = "stream"
        if not ts:
            ts = int(time.time())
        if not dd:
            dd = DOUYU_DEFAULT_DID

        # 绾喕绻氱€靛棝鎸滈張澶嬫櫏
        for _ in range(2):
            if DouyuUtils.is_key_vald(sign_type) or await DouyuUtils.update_key():
                break
        else:
            raise RuntimeError("鑾峰彇鍔犲瘑鐎靛棝鎸滃け璐?)

        rand_str = DouyuUtils.WhiteEncryptKey['rand_str']
        enc_time = DouyuUtils.WhiteEncryptKey['enc_time']
        key_data = {k: v for k, v in DouyuUtils.WhiteEncryptKey.items() if k != "cpp"}

        _CPP_SECTION = {"login": "danmu", "heartbeat": "heartbeat"}

        if sign_type == "stream":
            salt = "" if DouyuUtils.WhiteEncryptKey['is_special'] == 1 else f"{rd}{ts}"
            key = DouyuUtils.WhiteEncryptKey['key']
            key_ver = ""
        elif cpp_section := _CPP_SECTION.get(sign_type):
            cpp = DouyuUtils.WhiteEncryptKey['cpp'][cpp_section]
            salt = f"{rd}{dd}{ts}"
            key, key_ver = cpp['key'], cpp['key_ver']
        else:
            raise ValueError(f"wrong sign type: {sign_type}")

        secret = rand_str
        for _ in range(enc_time):
            secret = hashlib.md5(f"{secret}{key}".encode('utf-8')).hexdigest()
        auth = hashlib.md5(f"{secret}{key}{salt}".encode('utf-8')).hexdigest()

        return {
            'key': key_data,
            'alg_ver': "1.0",
            'key_ver': key_ver,
            'auth': auth,
            'ts': ts,
        }


@alru_cache(maxsize=None)
async def get_real_rd(url: str) -> str:
    rd = url.split('douyu.com/')[1].split('/')[0].split('?')[0] or match1(url, r'douyu.com/(\d+)')
    resp = await client.get(f"https://{DOUYU_MOBILE_DOMAIN}/{rd}", headers={
        "User-Agent": random_user_agent('mobile')
    })
    real_rd = match1(resp.text, r'roomInfo":{"rd":(\d+)')
    return str(real_rd)
