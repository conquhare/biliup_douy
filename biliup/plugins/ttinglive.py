锘縤mport biliup.common.util
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger, match1


@Plugin.download(regexp=r'(?:https?://)?www\.ttinglive\.com')
class TTingLive(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)

    async def acheck_stream(self, is_check=False):
        room_d = match1(self.url, r"/channels/(\d+)/live")
        if not room_d:
            logger.warning(f"{TTingLive.__name__}: {self.url}: 鐩存挱闂村湴鍧€閿欒")
        response = await biliup.common.util.client.get(f"https://api.ttinglive.com/api/channels/{room_d}/stream?option=all",
                                                       timeout=5,
                                                       headers=self.fake_headers)
        if response.status_code != 200:
            if response.status_code == 400:
                logger.debug(f"{TTingLive.__name__}: {self.url}: 鏈紑閹绢厽鍨ㄧ洿鎾梻缈犵瑝瀛樺湪")
                return False
            else:
                logger.warning(f"{TTingLive.__name__}: {self.url}: 鑾峰彇閿欒閿涘本婀版璺虫潻?)
                return False

        room_info = response.json()
        self.room_title = room_info['title']
        self.live_cover_url = room_info['thumbUrl']
        if is_check:
            return True

        m3u8_content = (await biliup.common.util.client.get(room_info['sources'][0]['url'], timeout=5, headers=self.fake_headers)).text
        import m3u8
        m3u8_obj = m3u8.loads(m3u8_content)
        if m3u8_obj.is_variant:
            # 閸欐牜鐖滈悳鍥ㄦ付婢堆呮畱濞?
            max_ratio_stream = max(m3u8_obj.playlists, key=lambda x: x.stream_info.bandwdth)
            self.raw_stream_url = max_ratio_stream.uri
        else:
            logger.warning(f"{TTingLive.__name__}: {self.url}: 瑙ｆ瀽閿欒")
            return False

        return True
