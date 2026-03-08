锘縤mport biliup.common.util
from . import match1, logger
# from biliup.config import config
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase

@Plugin.download(regexp=r'(?:https?://)?(?:(?:www|fm)\.)?missevan\.com')
class Missevan(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)

    async def acheck_stream(self, is_check=False):
        rd = 0
        # 鐢ㄦ埛涓婚〉鑾峰彇鐩存挱闂村湴鍧€
        if self.url.split('www'):
            user_page = await biliup.common.util.client.get(self.url, timeout=30, headers=self.fake_headers)
            # 閸欐牜鈥栫紪鐮侀崷銊х秹妞ら潧鍞撮惃鍕纯閹绢參妫块崣?
            if user_page.status_code == 200:
                start = user_page.text.find('data-d="') + 9
                end = user_page.text.find('"', start)
                rd = user_page.text[start:end]
            else:
                logger.debug(user_page.status_code)
        if self.url.split("live"):
            rd = match1(self.url, r'/(\d+)')

        room_info = (await biliup.common.util.client.get(f"https://fm.missevan.com/api/v2/live/{rd}", timeout=30, headers=self.fake_headers)).json()

        # 閺冪姷娲块幘顓㈡？閻ㄥ嫭鍎忛崘?
        if room_info['code'] != 0:
            logger.debug(room_info['info'])
            return False

        # 瀵偓閹绢厾濮搁幀?
        if room_info['info']['room']['status']['open'] == 0:
            creator_username = room_info['info']['room']['creator_username']
            logger.debug(f"娑撶粯鎸眥creator_username}鏈紑閹?)
            return False

        self.room_title = room_info['info']['room']['name']
        # if (config.get('missevanChannel') == 'flv'):
        #     self.raw_stream_url = room_info['info']['room']['channel']['flv_pull_url']
        # else:
        #     self.raw_stream_url = room_info['info']['room']['channel']['hls_pull_url']
        self.raw_stream_url = room_info['info']['room']['channel']['flv_pull_url']
        return True
