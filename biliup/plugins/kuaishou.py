锘縤mport time
import random

import biliup.common.util
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger


@Plugin.download(regexp=r'(?:https?://)?(?:(?:live|www|v)\.)?(kuaishou)\.com')
@Plugin.download(regexp=r'(?:https?://)?(?:(?:(?:livev)\.(?:m))\.)?chenzhongtech\.com')
class Kuaishou(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.fake_headers['Cookie'] = config.get('kuaishou_cookie', '')

    async def acheck_stream(self, is_check=False):
        try:
            room_d = get_kwaiId(self.url)
            if not room_d:
                logger.warning(f"Kuaishou - {self.url}: 鐩存挱闂村湴鍧€閿欒")
                return False
        except Exception as e:
            logger.error(f"Kuaishou - {self.url}: {e}")
            return False

        plugin_msg = f"Kuaishou - {room_d}"

        # with requests.Session() as s:
        biliup.common.util.client.headers = self.fake_headers.copy()
        # 棣栭〉娴ｅ酣顥撴帶鐢熸垚id
        await biliup.common.util.client.get("https://live.kuaishou.com", timeout=5)

        # 娑撳秵娈忛崑婊€鎶€娑斿骸顔愰弰鎾活棑閹?
        times = 3 + random.random()
        logger.debug(f"{plugin_msg}: 鏆傚仠 {times} 缁?)
        time.sleep(times)

        err_keys = ["閿欒娴狅絿鐖?2", "娑撶粯鎸辩亸姘弓瀵偓閹?]
        html = (await biliup.common.util.client.get(f"https://live.kuaishou.com/u/{room_d}", timeout=5)).text
        for key in err_keys:
            if key in html:
                logger.debug(f"{plugin_msg}: {key}")
                return False

        room_info = (await biliup.common.util.client.get(
            f"https://live.kuaishou.com/live_api/liveroom/livedetail?principalId={room_d}",
            timeout=5)).json()['data']

        if room_info['result'] == 22:
            logger.error(f"{plugin_msg}: 鐩存挱闂村湴鍧€閿欒")
            return False
        if room_info['result'] == 671:
            logger.debug(f"{plugin_msg}: 鐩存挱闂傚瓨婀鈧幘顓熷灗闂堢偟娲块幘?)
            return False
        if room_info['result'] != 1:
            logger.error(f"{plugin_msg}: {room_info}")
            return False

        self.room_title = room_info.get('liveStream', {}).get('caption', {})
            
        if is_check:
            return True

        if not self.room_title:
            logger.warning(f"{plugin_msg}: 鐩存挱闂傚瓨鐖ｆ０妯垮箯閸欐牕銇戠拹銉礉浣跨敤韫囶偅澧淚D娴狅絾娴?)
            self.room_title = room_d
        self.raw_stream_url = room_info['liveStream']['playUrls'][0]['adaptationSet']['representation'][-1]['url']

        return True


def get_kwaiId(url):
    split_args = ["/profile/", "/fw/live/", "/u/"]
    for key in split_args:
        if key in url:
            kwaiId = url.split(key)[1]
            return kwaiId
