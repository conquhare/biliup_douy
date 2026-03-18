from threading import Event

from ..engine.download import DownloadBase
from . import logger


def _get_ykdl_url_to_module():
    try:
        from ykdl.common import url_to_module
        return url_to_module
    except ImportError:
        return None


def _get_yt_dlp():
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        return None


class YDownload(DownloadBase):
    def __init__(self, fname, url, suffix='flv'):
        super().__init__(fname, url, suffix)
        self.ydl_opts = {}
        self._yt_dlp = None

    async def acheck_stream(self, is_check=False):
        self._yt_dlp = _get_yt_dlp()
        if not self._yt_dlp:
            logger.debug('%s: yt_dlp 不可用' % self.fname)
            return False
        try:
            self.get_sinfo()
            return True
        except self._yt_dlp.utils.DownloadError:
            logger.debug('%s未开播或读取下载信息失败' % self.fname)
            return False

    def get_sinfo(self):
        if not self._yt_dlp:
            return None
        info_list = []
        with self._yt_dlp.YoutubeDL() as ydl:
            if self.url:
                info = ydl.extract_info(self.url, download=False)
            else:
                logger.debug('%s不存在' % self.__class__.__name__)
                return
            for i in info['formats']:
                info_list.append(i['format_id'])
            logger.debug(info_list)
        return info_list

    def download(self):
        if not self._yt_dlp:
            return 1
        try:
            filename = self.gen_download_filename(is_fmt=True) + '.' + self.suffix
            self.ydl_opts = {'outtmpl': filename}
            with self._yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.url])
        except self._yt_dlp.utils.DownloadError:
            return 1
        return 0


class SDownload(DownloadBase):
    def __init__(self, fname, url, suffix='mp4'):
        super().__init__(fname, url, suffix)
        self.stream = None
        self.flag = Event()

    async def acheck_stream(self, is_check=False):
        logger.debug(self.fname)
        import streamlink
        try:
            streams = streamlink.streams(self.url)
            if streams:
                self.stream = streams["best"]
                fd = self.stream.open()
                fd.close()
                # streams.close()
                return True
        except streamlink.StreamlinkError:
            return

    def download(self):
        filename = self.gen_download_filename(is_fmt=True) + '.' + self.suffix
        # fd = stream.open()
        try:
            with self.stream.open() as fd:
                with open(filename + '.part', 'wb') as file:
                    for f in fd:
                        file.write(f)
                        if self.flag.is_set():
                            # self.flag.clear()
                            return 1
                    return 0
        except OSError:
            self.download_file_rename(filename + '.part', filename)
            raise


class Generic(DownloadBase):
    def __init__(self, fname, url, suffix='flv'):
        super().__init__(fname, url, suffix)
        self.handler = self

    async def acheck_stream(self, is_check=False):
        logger.debug(self.fname)
        url_to_module = _get_ykdl_url_to_module()
        if url_to_module:
            try:
                site, url = url_to_module(self.url)
                info = site.parser(url)
                stream_id = info.stream_types[0]
                urls = info.streams[stream_id]['src']
                self.raw_stream_url = urls[0]
                return True
            except:
                pass
        
        handlers = [YDownload(self.fname, self.url, 'mp4'), SDownload(self.fname, self.url, 'flv')]
        for handler in handlers:
            if await handler.acheck_stream():
                self.handler = handler
                self.suffix = handler.suffix
                return True
        return False

    def download(self):
        if self.handler == self:
            return super(Generic, self).download()
        return self.handler.download()


__plugin__ = Generic
