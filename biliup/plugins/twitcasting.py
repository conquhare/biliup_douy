import hashlib

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
        self.twitcasting_password = config.get('user', {}).get('twitcasting_password')
        self.twitcasting_quality = config.get('twitcasting_quality')
        self.twitcasting_cookie = config.get('user', {}).get('twitcasting_cookie')
        self.fake_headers['referer'] = "https://twitcasting.tv/"

        # TODO: _movie_id 在 acheck_stream 中获取后传递给弹幕客户端，考虑优化为更简洁的上下文传递方式
        self._movie_id = None

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
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 直播间需要密码")
            return False

        # 尺寸不合适
        # self.live_cover_url = match1(room_html, r'<meta property="og:image" content="([^"]*)"')
        self.room_title = match1(room_html, r'<meta name="twitter:title" content="([^"]*)"')
        uploader_id = match1(room_html, r'<meta name="twitter:creator" content="([^"]*)"')

        response = await biliup.common.util.client.get(
            f'https://twitcasting.tv/streamserver.php?target={uploader_id}&mode=client&player=pc_web',
            headers=self.fake_headers)
        if response.status_code != 200:
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 获取错误，本次跳过")
            return False
        stream_info = response.json()
        if not stream_info:
            logger.warning(f"{Twitcasting.__name__}: {self.url}: 直播间地址错误")
            return False
        if not stream_info['movie']['live']:
            logger.debug(f"{Twitcasting.__name__}: {self.url}: 未开播")
            return False

        self._movie_id = stream_info['movie']['id']

        if not stream_info.get("tc-hls", {}).get("streams"):
            logger.error(f"{Twitcasting.__name__}: {self.url}: 未获取到到直播流 => {stream_info}")
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
            logger.error(f"{Twitcasting.__name__}: {self.url}: 未查找到直播流 => {stream_info}")
            return False

        self.raw_stream_url = stream_url

        return True

    def danmaku_init(self):
        if self.twitcasting_danmaku:
            self.danmaku = DanmakuClient(self.url, self.gen_download_filename(), {
                'movie_id': self._movie_id,
                'password': self.twitcasting_password,
            })

