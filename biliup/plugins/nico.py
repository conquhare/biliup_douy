import random
import re
import subprocess
import time

import biliup.common.util
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from ..plugins import logger


@Plugin.download(regexp=r'(?:https?://)?(?:(?:www|m|live)\.)?nicovideo\.jp')
class Nico(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)

    async def acheck_stream(self, is_check=False):
        try:
            response = await biliup.common.util.client.get(self.url, timeout=5)
            # 姝ｅ垯琛ㄨ揪寮?
            pattern = r'"name":"(.*?)","description":"(.*?)"'
            # 鎵ц鍖归厤
            matches = re.findall(pattern, response.text)[0]
            self.room_title = matches[0]
        except:
            logger.info("鑾峰彇鏍囬澶辫触")
        port = random.randint(1025, 65535)
        stream_shell = [
            "streamlink",
            "--player-external-http",  # 涓哄閮ㄧ▼搴忔彁渚涙祦濯掍綋鏁版嵁
            "--player-external-http-port", str(port),  # 瀵瑰閮ㄨ緭鍑烘祦鐨勭鍙?
            self.url, "best"  # 娴侀摼鎺?
        ]
        if self.config.get('user', {}).get('niconico-email') is not None:
            niconico_email = "--niconico-email " + self.config.get('user', {}).get('niconico-email')
            stream_shell.insert(1, niconico_email)
        if self.config.get('user', {}).get('niconico-password') is not None:
            niconico_password = "--niconico-password " + self.config.get('user', {}).get('niconico-password')
            stream_shell.insert(1, niconico_password)
        if self.config.get('user', {}).get('niconico-user-session') is not None:
            niconico_user_session = "--niconico-user-session " + self.config.get('user', {}).get('niconico-user-session')
            stream_shell.insert(1, niconico_user_session)
        if self.config.get('user', {}).get('niconico-purge-credentials') is not None:
            niconico_purge_credentials = "--niconico-purge-credentials " + self.config.get('user', {}).get('niconico-purge-credentials')
            stream_shell.insert(1, niconico_purge_credentials)
        self.proc = subprocess.Popen(stream_shell)
        self.raw_stream_url = f"http://localhost:{port}"
        i = 0
        while i < 5:
            if not (self.proc.poll() is None):
                return
            time.sleep(1)
            i += 1
        return True

    def close(self):
        try:
            if self.proc is not None:
                self.proc.terminate()
        except:
            logger.exception(f'terminate {self.fname} failed')
