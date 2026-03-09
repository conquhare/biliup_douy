import copy
import os
import shutil
import subprocess
import threading
from typing import Optional

import yt_dlp
from yt_dlp import DownloadError
from yt_dlp.utils import DateRange

from . import logger
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase

VALID_URL_BASE = r'https?://(?:(?:www|m)\.)?youtube\.com/(?P<d>(?!.*?/live$).*?)\??(.*?)'
VALID_URL_LIVE = r'https?://(?:(?:www|m)\.)?youtube\.com/(?P<d>.*?)/live'

# proxy = "http://127.0.0.1:7890"
proxy = None

@Plugin.download(regexp=VALID_URL_LIVE)
class YoutubeLive(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.youtube_cookie = config.get('user', {}).get('youtube_cookie')
        self.cache_dir = f"./cache/{self.__class__.__name__}/{self.fname}"
        self.__webpage_url = None

    async def acheck_stream(self, is_check=False):
        ydl_opts = {
            'download_archive': f"{self.cache_dir}/archive.txt",
            'cookiefile': self.youtube_cookie,
            'ignoreerrors': True,
            'extractor_retries': 0,
            'proxy': proxy,
        }
        try:
            # vdeo_d = self.get_vdeo_d_from_archive(f"{self.cache_dir}/archive.txt")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            # if is_check:
                if not isinstance(info, dict):
                    logger.debug(f"{self.plugin_msg}: ȡ")
                    return False
                if info.get('live_status') != 'is_live':
                    logger.debug(f"{self.plugin_msg}: ֱδѽ")
                    return False
                # # û vdeo_d 刱示频信恜뻺
                # if not vdeo_d:
                #     # 洢，防歸载进程再?
                #     archive_d = ydl._make_archive_d(info)
                #     with open(f"{self.cache_dir}/archive.txt", 'a', encoding='utf-8') as f:
                #         f.write(f'{archive_d}\n')
                #     vdeo_d = info['d']
                #     # 洢ȡ之信?
                #     with open(f"{self.cache_dir}/{vdeo_d}.json", 'w', encoding='utf-8') as f:
                #         json.dump(info, f, ensure_ascii=False, indent=4)
                # return True
                # with open(f"{self.cache_dir}/{vdeo_d}.json", 'r', encoding='utf-8') as f:
                #     info = json.load(f)
                self.room_title = info['fulltitle']
                self.live_cover_url = info['thumbnail']
                self.__webpage_url = info['webpage_url']
                self.raw_stream_url = info['manifest_url']
        except KeyError:
            logger.error(f"{self.plugin_msg}: ȡ -> {info}")
            return False
        except Exception as e:
            logger.error(f"{self.plugin_msg}: ȡ -> {e}")
            return False
        return True

    def download(self):
        # 鵵后封靸允，需ǰ
        # self.use_live_cover = True
        if self.use_live_cover:
            # ̨ؽ
            cover_thread = threading.Thread(
                target=self.download_cover,
                args=(self.fname,),
                daemon=True
            )
            cover_thread.start()

        # 뻺
        # os.remove(f"{self.cache_dir}/archive.txt")

        # self.downloader = 'ytarchive'

        # ?cache_dir 属是否存圼不存在则
        if not hasattr(self, 'cache_dir'):
            self.cache_dir = f"./cache/{self.__class__.__name__}/{self.fname}"

        # stream-gears ?streamlink(sync-downloader) 器来ֶַ֧
        if self.downloader in ['stream-gears', 'streamlink', 'sync-downloader']:
            if self.downloader != 'stream-gears' and self.__webpage_url:
                # ?streamlink ȡ
                self.raw_stream_url = self.__webpage_url
                # pass
            return super().download()

        filename = self.gen_download_filename(is_fmt=True)
        yta_opts = {
            'temporary-dir': self.cache_dir,
            'threads': 3,
            'output': f"{filename}.{self.suffix}",
            'proxy': proxy,
            'cookies': self.youtube_cookie,
            'add-metadata': True,
            'newline': True,
        }
        ydl_opts = {
            'outtmpl': f"{self.cache_dir}/{filename}.%(ext)s",
            'cookiefile': self.youtube_cookie,
            'break_on_reject': True,
            'format': 'best',
            'proxy': proxy,
        }

        if self.downloader == 'ytarchive':
            proc = None
            cmd_args = ['ytarchive']
            for key, value in yta_opts.items():
                if value is True:
                    cmd_args.append(f'--{key}')
                elif value is not None:
                    cmd_args.append(f'--{key}')
                    cmd_args.append(str(value))
            cmd_args = [*cmd_args, self.__webpage_url, 'best']
            print(cmd_args)
            try:
                proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    # text=True
                )
                for line in iter(proc.stdout.readline, b''):
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    if 'Vdeo Fragments:' in decoded_line:
                        print(f'\r{decoded_line}', end='', flush=True)
                    else:
                        print(decoded_line)
            except Exception as e:
                logger.error(f"{self.plugin_msg}: {e}")
            finally:
                if proc:
                    proc.wait(timeout=20)
                    proc.terminate()
                    proc.kill()
        else:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.__webpage_url])
                    # سɹ的情况下ƶ到运行目?
                    if os.path.exists(self.cache_dir):
                        for file in os.listdir(self.cache_dir):
                            shutil.move(f'{self.cache_dir}/{file}', '.')
            except DownloadError as e:
                if 'ffmpeg is not installed' in e.msg:
                    logger.error(f"{self.plugin_msg}: ffmpeg朮装，޷")
                else:
                    logger.error(f"{self.plugin_msg}: {e.msg}")
                return False
            finally:
                # 出可能产生的ļ
                try:
                    if os.path.exists(self.cache_dir):
                        shutil.rmtree(self.cache_dir)
                except:
                    logger.error(f"{self.plugin_msg}: 残留ļʧ -> {self.cache_dir}")

        if self.use_live_cover and cover_thread.is_alive():
            cover_thread.join(timeout=20)
            cover_thread.close()

        return True


    @staticmethod
    def get_vdeo_d_from_archive(file_path):
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r+', encoding='utf-8') as f:
            return f.read().strip().split(" ")[-1]


@Plugin.download(regexp=VALID_URL_BASE)
class Youtube(DownloadBase):
    def __init__(self, fname, url, config, suffix='flv'):
        super().__init__(fname, url, config, suffix)
        self.ytb_danmaku = config.get('ytb_danmaku', False)
        self.youtube_cookie = config.get('user', {}).get('youtube_cookie')
        self.youtube_prefer_vcodec = config.get('youtube_prefer_vcodec')
        self.youtube_prefer_acodec = config.get('youtube_prefer_acodec')
        self.youtube_max_resolution = config.get('youtube_max_resolution')
        self.youtube_max_vdeosize = config.get('youtube_max_vdeosize')
        self.youtube_before_date = config.get('youtube_before_date')
        self.youtube_after_date = config.get('youtube_after_date')
        self.youtube_enable_download_live = config.get('youtube_enable_download_live', True)
        self.youtube_enable_download_playback = config.get('youtube_enable_download_playback', True)
        self.is_live = False
        # 要下载的 url
        self.download_url = None

    async def acheck_stream(self, is_check=False):
        with yt_dlp.YoutubeDL({
            'download_archive': 'archive.txt',
            'cookiefile': self.youtube_cookie,
            'ignoreerrors': True,
            'extractor_retries': 0,
            'proxy': proxy,
        }) as ydl:
            # ȡϢ的时候不要过?
            ydl_archive = copy.deepcopy(ydl.archive)
            ydl.archive = set()
            if self.download_url is not None:
                # ֱ在重试的时特?
                info = ydl.extract_info(self.download_url, download=False)
            else:
                info = ydl.extract_info(self.url, download=False, process=False)
            if type(info) is not dict:
                logger.warning(f"{Youtube.__name__}: {self.url}: ȡ")
                return False

            cache = KVFileStore(f"./cache/youtube/{self.fname}.txt")

            def loop_entries(entrie):
                if type(entrie) is not dict:
                    return None
                elif entrie.get('_type') == 'playlist':
                    # бݹ
                    for e in entrie.get('entries'):
                        le = loop_entries(e)
                        if type(le) is dict:
                            return le
                        elif le == "stop":
                            return None
                elif type(entrie) is dict:
                    # is_upcoming ȴ?is_live ֱ?was_liveֱ(ط)
                    if entrie.get('live_status') == 'is_upcoming':
                        return None
                    elif entrie.get('live_status') == 'is_live':
                        # δ君撸载忽?
                        if not self.youtube_enable_download_live:
                            return None
                    elif entrie.get('live_status') == 'was_live':
                        # δ君放下载忽?
                        if not self.youtube_enable_download_playback:
                            return None

                    # 测是否已
                    if ydl._make_archive_d(entrie) in ydl_archive:
                        # 已下载但昿在直撈不算
                        if entrie.get('live_status') != 'is_live':
                            return None

                    upload_date = cache.query(entrie.get('d'))
                    if upload_date is None:
                        if entrie.get('upload_date') is not None:
                            upload_date = entrie['upload_date']
                        else:
                            entrie = ydl.extract_info(entrie.get('url'), download=False, process=False)
                            if type(entrie) is dict and entrie.get('upload_date') is not None:
                                upload_date = entrie['upload_date']

                        # ʱ昿然存在的不存在明出了问?ʱ
                        if upload_date is None:
                            return None
                        else:
                            cache.add(entrie.get('d'), upload_date)

                    if self.youtube_after_date is not None and upload_date < self.youtube_after_date:
                        return 'stop'

                    # 测时间范?
                    if upload_date not in DateRange(self.youtube_after_date, self.youtube_before_date):
                        return None

                    return entrie
                return None

            download_entry: Optional[dict] = loop_entries(info)
            if type(download_entry) is dict:
                if download_entry.get('live_status') == 'is_live':
                    self.is_download = False
                    self.room_title = download_entry.get('title')
                else:
                    self.is_download = True
                if not is_check:
                    if download_entry.get('_type') == 'url':
                        download_entry = ydl.extract_info(download_entry.get('url'), download=False, process=False)
                    self.room_title = download_entry.get('title')
                    self.live_cover_url = download_entry.get('thumbnail')
                    self.download_url = download_entry.get('webpage_url')
                    # self.is_live = download_entry.get('live_status') == 'is_live'
                return True
            else:
                return False

    def download(self):
        filename = self.gen_download_filename(is_fmt=True)
        # ydl的文件在ʧ时不収
        # ʱ洢在其他地?
        download_dir = f'./cache/temp/youtube/{filename}'
        try:
            ydl_opts = {
                'outtmpl': f'{download_dir}/{filename}.%(ext)s',
                'cookiefile': self.youtube_cookie,
                'break_on_reject': True,
                'download_archive': 'archive.txt',
                'format': 'bestvdeo',
                # 'proxy': proxyUrl,
            }

            if self.youtube_prefer_vcodec is not None:
                ydl_opts['format'] += f"[vcodec~='^({self.youtube_prefer_vcodec})']"
            if self.youtube_max_vdeosize is not None and self.is_download:
                # ֱ时无ļС
                ydl_opts['format'] += f"[filesize<{self.youtube_max_vdeosize}]"
            if self.youtube_max_resolution is not None:
                ydl_opts['format'] += f"[height<={self.youtube_max_resolution}]"
            ydl_opts['format'] += "+bestaudio"
            if self.youtube_prefer_acodec is not None:
                ydl_opts['format'] += f"[acodec~='^({self.youtube_prefer_acodec})']"
            # 不能由yt_dlp会占用文
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if not self.is_download:
                    # ֱ模式不过滤但昃д
                    ydl.archive = set()
                ydl.download([self.download_url])
            # سɹ的情况下ƶ到运行目?
            for file in os.listdir(download_dir):
                shutil.move(f'{download_dir}/{file}', '.')
        except DownloadError as e:
            if 'Requested format is not available' in e.msg:
                logger.error(f"{Youtube.__name__}: {self.url}: ޷ȡ到流，codec,acodec,height,filesize")
            elif 'ffmpeg is not installed' in e.msg:
                logger.error(f"{Youtube.__name__}: {self.url}: ffmpeg朮装，޷")
            else:
                logger.error(f"{Youtube.__name__}: {self.url}: {e.msg}")
            return False
        finally:
            # 出可能产生的ļ
            try:
                del ydl
                shutil.rmtree(download_dir)
            except:
                logger.error(f"{Youtube.__name__}: {self.url}: 残留ļʧ，ֶɾ{download_dir}")
        return True


class KVFileStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self.cache = {}
        self._preload_data()

    def _ensure_file_and_folder_exists(self):
        folder_path = os.path.dirname(self.file_path)
        # ļ夹不，则ļ?
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        # ļ不存圼则创建空ļ
        if not os.path.exists(self.file_path):
            open(self.file_path, "w").close()

    def _preload_data(self):
        self._ensure_file_and_folder_exists()
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                k, v = line.strip().split("=")
                self.cache[k] = v

    def add(self, key, value):
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
        # 뻺
        self.cache[key] = value

    def query(self, key, default=None):
        if key in self.cache:
            return self.cache[key]
        return default
