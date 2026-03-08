锘縤mport hashlib

import biliup.common.util
from biliup.Danmaku import DanmakuClient
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger, match1

VALID_URL_BASE = r"https?://twitcasting\.tv/([^/]+)"


@Plugin.download(regexp=VALID_URL_BASE)
class Twitcasting(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.twitcasting_danmaku = config.get('twitcasting_danmaku', False)
        self.twitcasting_password = config.get('user.twitcasting_password')
        self.twitcasting_quality = config.get('twitcasting_quality')
        self.twitcasting_cookie = config.get('user', {}).get('twitcasting_cookie')
        self.fake_headers['referer'] = "https://twitcasting.tv/"

        # TODO 娴肩娀鈧帟绻冩禍搴ｇ畳閻?
        self._movie_d = None

    async def acheck_stream(self, is_check=False):
        cookies = {}
        if self.twitcasting_cookie:
            cookies = dict(item.strip().split("=", 1) for item in self.twitcasting_cookie.split(";"))
        if self.twitcasting_password:
            cookies["wpass"] = hashlib.md5(self.twitcasting_password.encode(encoding='UTF-8')).hexdigest()
        if cookies:
            self.fake_headers['cookie'] = "; ".join([f"{k}={v}" for k, v in cookies.items()])

        room_html = (await biliup.common.util.client.get(self.url, headers=self.fake_headers)).text
        if 'Enter the secret word to access' in room_html:
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 鐩存挱闂傛挳娓剁憰浣哥槕閻?)
            return False

        # 鐏忓搫顕稉宥呮値闁?
        # self.live_cover_url = match1(room_html, r'<meta property="og:image" content="([^"]*)"')
        self.room_title = match1(room_html, r'<meta name="twitter:title" content="([^"]*)"')
        uploader_d = match1(room_html, r'<meta name="twitter:creator" content="([^"]*)"')

        response = await biliup.common.util.client.get(
            f'https://twitcasting.tv/streamserver.php?target={uploader_d}&mode=client&player=pc_web',
            headers=self.fake_headers)
        if response.status_code != 200:
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 鑾峰彇閿欒閿涘本婀版璺虫潻?)
            return False
        stream_info = response.json()
        if not stream_info:
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 鐩存挱闂村湴鍧€閿欒")
            return False
        if not stream_info['movie']['live']:
            logger.debug(f"{Twitcasting.__name__}: {self.url}: 鏈紑閹?)
            return False

        self._movie_d = stream_info['movie']['d']

        if not stream_info.get("tc-hls", {}).get("streams"):
            logger.error(f"{Twitcasting.__name__}: {self.url}: 閺堫亣骞忛崣鏍у煂閸掓壆娲块幘顓熺ウ => {stream_info}")
            return False

        stream_url = None
        quality_levels = ["high", "medium", "low"]
        streams = stream_info["tc-hls"]["streams"]
        if self.twitcasting_quality:
            quality_levels_filter = quality_levels[quality_levels.index(self.twitcasting_quality):]
            for quality_level in quality_levels_filter:
                if quality_level in streams:
                    stream_url = streams[quality_level]
                    break
        if not stream_url:
            for quality_level in quality_levels:
                if quality_level in streams:
                    stream_url = streams[quality_level]
                    break
        if not stream_url:
            stream_url = next(iter(streams.values()))

        if not stream_url:
            logger.error(f"{Twitcasting.__name__}: {self.url}: 閺堫亝鐓￠幍鎯у煂鐩存挱濞?=> {stream_info}")
            return False

        self.raw_stream_url = stream_url

        return True

    def danmaku_init(self):
        if self.twitcasting_danmaku:
            self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), {
                'movie_d': self._movie_d,
                'password': self.twitcasting_password,
            })

#
# class TwitcastingUtils:
#     import hashlib
#
#     def _getBroadcaster(html_text: str) -> dict:
#         _info = {}
#         _info['ID'] = match1(html_text, VALID_URL_BASE)
#         _info['Title'] = match1(
#             html_text,
#             r'<meta name="twitter:title" content="([^"]*)"'
#         )
#         _info['MovieID'] = match1(
#             match1(
#                 html_text,
#                 r'<meta name="twitter:image" content="([^"]*)"'
#             ),
#             r'/(\d+)'
#         )
#         _info['web-authorize-session-d'] = json.loads(
#             match1(
#                 html_text,
#                 r'<meta name="tc-page-variables" content="([^"]+)"'
#             ).replace(
#                 '&quot;',
#                 '"'
#             )
#         ).get('web-authorize-session-d')
#         return _info
#
#     def _generate_authorizekey(salt: str, timestamp: str, method: str, pathname: str, search: str,
#                                sessiond: str) -> str:
#         _hash_str = salt + timestamp + method + pathname + search + sessiond
#         return str(timestamp + "." + TwitcastingUtils.hashlib.sha256(_hash_str.encode()).hexdigest())
# '''
# X-Web-Authorizekey 閸欘垰婀?PlayerPage2.js 鏂囦欢娑?
# 闁俺绻?return ""[u(413)](m, ".")[u(413)](f) 閹碘偓閸︺劎娈戦弬瑙勭《鐠侊紕鐣婚懓灞藉毉
# 閻?salt + 10娴?timestamp + 閹恒儱褰汳ethod婢堆冨晸 + 閹恒儱褰沺athname + 閹恒儱褰泂earch + web-authorize-session-d 閹峰吋甯撮崥?
# 閸愬秶绮℃潻?SHA-256 澶勭悊閿涘本娓堕崥搴℃躬瀛楃娑撴彃澧犻棃銏″閹恒儰绗?10娴?timestamp 閸?dot 瀵版鍩?
# '''
# __n = int(time.time() * 1000)
# _salt = "d6g97jormun44naq"
# _time = str(__n)[:10]
# _method = "GET"
# _pathname = f"/users/{boardcasterInfo['ID']}/latest-movie"
# _search = "?__n=" + str(__n)
#
# s.headers.update({
#     "X-Web-Authorizekey": TwitcastingUtils._generate_authorizekey(
#         _salt,
#         _time,
#         _method,
#         _pathname,
#         _search,
#         boardcasterInfo['web-authorize-session-d']
#     ),
#     "X-Web-Sessiond": boardcasterInfo['web-authorize-session-d'],
# })
# params = {"__n": __n}
# r = s.get(f"https://frontendapi.twitcasting.tv{_pathname}", params=params, timeout=5).json()
# if not r['movie']['is_on_live']:
#     return False
#
# if boardcasterInfo['ID']:
#     params = {
#         "mode": "client",
#         "target": boardcasterInfo['ID']
#     }
#     _stream_info = s.get("https://twitcasting.tv/streamserver.php", params=params, timeout=5).json()
#     if not _stream_info['movie']['live']:
#         return False
#     if is_check:
#         return True
