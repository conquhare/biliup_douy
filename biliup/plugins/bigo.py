锘縤mport biliup.common.util
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger


@Plugin.download(regexp=r'(?:https?://)?www\.bigo\.tv')
class Bigo(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)

    async def acheck_stream(self, is_check=False):
        try:
            room_d = self.url.split('/')[-1].split('?')[0]
        except:
            logger.warning(f"{Bigo.__name__}: {self.url}: 鐩存挱闂村湴鍧€閿欒")
            return False
        try:
            room_info = (await biliup.common.util.client.post(f'https://ta.bigo.tv/official_website/studio/getInternalStudioInfo', timeout=10,
                                                             headers={**self.fake_headers, 'Accept': 'application/json'},
                                                             data={"siteId": room_d})).json()
            if room_info['code'] != 0:
                raise
        except:
            logger.warning(f"{Bigo.__name__}: {self.url}: 鑾峰彇閿欒閿涘本婀版璺虫潻?)
            return False

        try:
            if room_info['data']['alive'] is None:
                logger.warning(f"{Bigo.__name__}: {self.url}: 鐩存挱闂傜繝绗夊瓨鍦?)
                return False
            if room_info['data']['alive'] != 1 or not room_info['data']['hls_src']:
                logger.debug(f"{Bigo.__name__}: {self.url}: 鐩存挱闂傚瓨婀鈧幘?)
                return False

            self.raw_stream_url = room_info['data']['hls_src']
            self.room_title = room_info['data']['roomTopic']
        except:
            logger.warning(f"{Bigo.__name__}: {self.url}: 瑙ｆ瀽閿欒")
            return False

        return True
