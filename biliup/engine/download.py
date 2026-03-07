import copy
import inspect
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Callable, Optional
from urllib.parse import urlparse

import requests
import stream_gears
from PIL import Image
from httpx import HTTPStatusError
from requests.utils import DEFAULT_ACCEPT_ENCODING

from biliup.Danmaku import IDanmakuClient
from biliup.common.util import client, check_timerange
from biliup.plugins import random_user_agent
from biliup.plugins.bili_webup_sync import BiliWebAsync
from .sync_downloader import SyncDownloader

# from biliup.app import context
logger = logging.getLogger('biliup')


class DownloadBase(ABC):
    def __init__(self, fname, url, config, suffix=None, opt_args=None):
        self.room_title = None
        if opt_args is None:
            opt_args = []
        self.fname = fname
        self.url = url
        # 褰曞埗鍚庝繚瀛樻枃浠舵牸寮忚€岄潪婧愭祦格式 瀵瑰簲鍘熼厤缃枃浠秄ormat 浠協fmpeg鍙妔treamlink鐢熸晥
        if not suffix:
            logger.error(f'检娴嬪埌suffix涓嶅瓨鍦紝璇疯ˉ鍏呭悗缂€')
        else:
            self.suffix = suffix.lower()
        self.live_cover_path = None
        self.database_row_id = 0
        self.downloader = config.get('downloader', 'stream-gears')
        # ffmpeg.exe -i  http://vfile1.grtn.cn/2018/1542/0254/3368/154202543368.ssm/154202543368.m3u8
        # -c copy -bsf:a aac_adtstoasc -movflags +faststart output.mp4
        self.raw_stream_url = None

        # 涓绘挱鍗曠嫭浼犲弬浼氳鐩栧叏灞€设置銆備緥濡傛柊澧炰簡涓€涓叏灞€鐨刦ilename_prefix参数锛屽湪涓嬮潰娣诲姞self.filename_prefix = config.get('filename_prefix'),
        # 鍗冲彲閫氳繃self.filename_prefix鍦ㄤ笅杞芥垨鑰呬笂浼犳椂鍊欎紶閫掍富鎾崟鐙殑设置参数鐢ㄤ簬璋冪敤锛堝鏋滆涓绘挱鏈夎缃崟鐙弬鏁帮紝灏嗕細浼樺厛浣跨敤鍗曠嫭参数锛涘鏃狅紝鍒欎細浼樺厛浣犵敤鍏ㄥ眬参数銆傦級
        self.filename_prefix = config.get('filename_prefix')
        self.use_live_cover = config.get('use_live_cover', False)
        self.opt_args = opt_args
        self.live_cover_url = None
        self.fake_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-encoding': DEFAULT_ACCEPT_ENCODING,
            'accept-language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'user-agent': random_user_agent(),
        }
        self.stream_headers = copy.deepcopy(self.fake_headers)
        self.segment_time = config.get('segment_time', '01:00:00')
        # self.time_range = config.get('time_range')
        # self.excluded_keywords = config.get('excluded_keywords')
        self.file_size = config.get('file_size')

        # 鏄惁鏄笅杞芥ā寮?跳过涓嬫挱检娴?
        self.is_download = False

        # 分段鍚庡鐞?
        # self.segment_processor = config.get('segment_processor')
        self.segment_processor_thread = []
        # 分段鍚庡鐞嗗苟琛?
        self.segment_processor_parallel = config.get('segment_processor_parallel', False)

        # 寮瑰箷瀹㈡埛绔?
        self.danmaku: Optional[IDanmakuClient] = None

        self.platform = self.__class__.__name__
        self.plugin_msg = f"[{self.platform}]{self.fname} - {self.url}"
        self.config = config

    @abstractmethod
    async def acheck_stream(self, is_check=False):
        # is_check 鏄惁鏄娴嬫ā寮?检娴嬫ā寮忓彲浠ュ拷鐣ュ彧鏈変笅杞芥椂闇€瑕佺殑鑰楁椂鎿嶄綔
        raise NotImplementedError()

    def should_record(self):
        # 检鏌ユ埧闂村悕
        keywords = self.config['streamers'].get(self.fname, {}).get('excluded_keywords')
        if self.room_title and keywords:
            if any(k.strip() in self.room_title for k in keywords):
                return False

        # 检鏌ユ椂闂磋寖鍥?
        if not check_timerange(self.fname):
            return False

        return True

    def download(self):
        self.update_headers(self.stream_headers)
        # print(f"{self.plugin_msg}: Plugin settings - {self.__dict__}")
        logger.debug(f"{self.plugin_msg}: Plugin settings - {self.__dict__}")
        # logger.info(f"{self.plugin_msg}: Request headers - {self.fake_headers}")
        logger.info(f"{self.plugin_msg}: Request url - {self.raw_stream_url}")
        # 璋冭瘯浣跨敤杈瑰綍杈逛笂浼犲姛鑳?
        # self.downloader = 'sync-downloader'
        if self.is_download:
            if not shutil.which("ffmpeg"):
                logger.error("鏈畨瑁?FFMpeg 鎴栦笉存在浜?PATH 鍐?)
                logger.info("Current user's PATH is:" + os.getenv("PATH"))
                return False
            else:
                return self.ffmpeg_segment_download()

        parsed_url_path = urlparse(self.raw_stream_url).path
        if self.downloader != 'stream-gears':
            if not shutil.which("ffmpeg"):
                logger.error("鏈畨瑁?FFMpeg 鎴栦笉存在浜?PATH 鍐咃紝鏈下载浣跨敤 stream-gears")
                logger.info("Current user's PATH is:" + os.getenv("PATH"))
            else:
                # 鍚屾下载上传鍣?
                if self.downloader == 'sync-downloader':
                    logger.info(f"{self.plugin_msg}: 浣跨敤鍚屾下载鍣?)
                    stream_info = self.config.get('streamers', {}).get(self.fname, {})
                    stream_info.update({'name': self.fname})
                    min_size = 10 * 1024 * 1024
                    if not self.file_size:
                        self.file_size = 2 * 1024 * 1024 * 1024
                    self.file_size = ((self.file_size + min_size - 1) // min_size) * min_size  # 鍚戜笂鍙栨暣
                    sync_download(self.raw_stream_url, self.stream_headers,
                                max_file_size=int(self.file_size / 1024 / 1024),
                                output_prefix=self.gen_download_filename(True),
                                stream_info=stream_info,
                                file_name_callback=lambda file_name: self.__download_segment_callback(file_name), database_row_id=self.database_row_id)
                    return True
                # streamlink无法处理flv,鎵€浠ュ洖閫€鍒癴fmpeg
                if self.downloader == 'streamlink' and '.flv' not in parsed_url_path:
                    return self.ffmpeg_download(use_streamlink=True)
                return self.ffmpeg_download()

        if '.flv' in parsed_url_path:
            # 鍋囧畾flv娴?
            self.suffix = 'flv'
        else:
            # 其他娴乻tream_gears浼氭寜hls淇濆瓨涓簍s
            self.suffix = 'ts'
        stream_gears_download(self.raw_stream_url, self.stream_headers, self.gen_download_filename(),
                              self.segment_time,
                              self.file_size,
                              lambda file_name: self.__download_segment_callback(file_name))
        return True

    def ffmpeg_segment_download(self):
        # TODO 鏃犳棩蹇?
        # , '-report'
        # ffmpeg 杈撳叆参数
        input_args = [
            '-loglevel', 'quiet', '-y'
        ]
        # ffmpeg 杈撳嚭参数
        output_args = [
            '-bsf:a', 'aac_adtstoasc'
        ]
        input_args += ['-headers', ''.join('%s: %s\r\n' % x for x in self.fake_headers.items()),
                       '-rw_timeout', '20000000']
        if '.m3u8' in urlparse(self.raw_stream_url).path:
            input_args += ['-max_reload', '1000']

        input_args += ['-i', self.raw_stream_url]

        output_args += ['-f', 'segment']
        # output_args += ['-segment_format', self.suffix]
        output_args += ['-segment_list', 'pipe:1']
        output_args += ['-segment_list_type', 'flat']
        output_args += ['-reset_timestamps', '1']
        # output_args += ['-strftime', '1']
        if self.segment_time:
            output_args += ['-segment_time', self.segment_time]
        else:
            # 閬垮厤閫傞厤涓ゅ
            output_args += ['-segment_time', '9999:00:00']

        output_args += ['-c', 'copy']
        output_args += self.opt_args
        file_name = self.gen_download_filename(is_fmt=True)
        args = ['ffmpeg', *input_args, *output_args, f'{file_name}_%d.{self.suffix}']
        with subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL) as proc:
            for line in iter(proc.stdout.readline, b''):  # b'\n'-separated lines
                try:
                    ffmpeg_file_name = line.rstrip().decode(errors='ignore')
                    time.sleep(1)
                    # 文件閲嶅懡鍚?
                    self.download_file_rename(ffmpeg_file_name, f'{file_name}.{self.suffix}')
                    self.__download_segment_callback(f'{file_name}.{self.suffix}')
                    file_name = self.gen_download_filename(is_fmt=True)
                except:
                    logger.error(f'分段浜嬩欢失败锛歿self.__class__.__name__} - {self.fname}', exc_info=True)

        return proc.returncode == 0

    def ffmpeg_download(self, use_streamlink=False):
        # streamlink杩涚▼
        streamlink_proc = None
        # updatedFileList = False
        try:
            # 文件鍚嶄笉鍚悗鎴?
            fmt_file_name = self.gen_download_filename(is_fmt=True)
            # ffmpeg 杈撳叆参数
            input_args = [
                # '-http_proxy', 'http://127.0.0.1:10808',
                # "-fflags", "+genpts",
            ]
            # ffmpeg 杈撳嚭参数
            output_args = [
                '-c',
                'copy',
            ]
            # https://github.com/biliup/biliup/issues/991
            if use_streamlink and not self.raw_stream_url.startswith('http://localhost:'):
                streamlink_cmd = [
                    'streamlink',
                    '--stream-segment-threads', '3',
                    '--hls-playlist-reload-attempts', '1',
                    # '--http-proxy', 'http://127.0.0.1:7890',
                    # '--hls-live-restart',
                ]
                for key, value in self.stream_headers.items():
                    streamlink_cmd.extend(['--http-header', f'{key}={value}'])
                if self.__class__.__name__ == 'Bililive':
                    # Fix: segment 涓嶆惡甯﹀弬鏁版椂 404
                    from urllib.parse import parse_qs
                    def parse_query_params(url: str) -> List[str]:
                        query_params = []
                        params = url.split('?')[-1]
                        whitelist = ['uparams', 'upsig', 'sigparams', 'sign', 'flvsk', 'sk', 'mid', 'site']
                        data = parse_qs(params)
                        whitelist.extend(data.get('sigparams', [''])[0].split(','))
                        whitelist.extend(data.get('uparams', [''])[0].split(','))
                        if not params or params.startswith('http'):
                            return query_params
                        for param in params.split('&'):
                            if param.split('=')[0] not in whitelist:
                                continue
                            query_params.extend(["--http-query-param", param])
                        return query_params
                    streamlink_cmd.extend(parse_query_params(self.raw_stream_url))
                streamlink_cmd.extend([
                    self.raw_stream_url,
                    'best',
                    '-O'
                ])
                streamlink_proc = subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE)
                input_uri = 'pipe:0'
            else:
                input_args += ['-headers', ''.join('%s: %s\r\n' % x for x in self.stream_headers.items()),
                               '-rw_timeout', '20000000']
                if '.m3u8' in urlparse(self.raw_stream_url).path:
                    input_args += ['-max_reload', '1000']
                input_uri = self.raw_stream_url

            input_args += ['-i', input_uri]

            duration = get_duration(self.segment_time, self.time_range)
            if duration:
                output_args += ['-to', duration]
            if self.file_size:
                output_args += ['-fs', str(self.file_size)]

            output_args += self.opt_args

            if self.suffix == 'mp4':
                output_args += ['-bsf:a', 'aac_adtstoasc', '-f', 'mp4']
            elif self.suffix == 'ts':
                output_args += ['-f', 'mpegts']
            elif self.suffix == 'mkv':
                output_args += ['-f', 'matroska']
            else:
                output_args += ['-f', self.suffix]

            args = ['ffmpeg', '-y', *input_args, *output_args,
                    f'{fmt_file_name}.{self.suffix}.part']
            with subprocess.Popen(args, stdin=subprocess.DEVNULL if not streamlink_proc else streamlink_proc.stdout,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
                for line in iter(proc.stdout.readline, b''):  # b'\n'-separated lines
                    decode_line = line.rstrip().decode(errors='ignore')
                    print(decode_line)
                    logger.debug(decode_line)

            if proc.returncode == 0:
                # 文件閲嶅懡鍚?
                self.download_file_rename(f'{fmt_file_name}.{self.suffix}.part', f'{fmt_file_name}.{self.suffix}')
                # 瑙﹀彂分段浜嬩欢
                self.__download_segment_callback(f'{fmt_file_name}.{self.suffix}')
                return True
            else:
                return False
        finally:
            try:
                if streamlink_proc:
                    streamlink_proc.terminate()
                    streamlink_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlink_proc.kill()
            except:
                logger.exception(f'terminate {self.fname} failed')

    def __download_segment_callback(self, file_name: str):
        """
        分段鍚庤Е鍙戣繑鍥炲惈鍚庢埑鐨勬枃浠跺悕
        """
        exclude_ext_file_name = os.path.splitext(file_name)[0]
        danmaku_file_name = os.path.splitext(file_name)[0] + '.xml'
        if self.danmaku:
            self.danmaku.save(danmaku_file_name)


    def download_success_callback(self):
        pass


    def download_cover(self, fmtname):
        # 获取界面
        if self.use_live_cover and self.live_cover_url is not None:
            try:
                save_dir = f'cover/{self.__class__.__name__}/{self.fname}/'
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)

                url_path = urlparse(self.live_cover_url).path
                suffix = None
                if '.jpg' in url_path:
                    suffix = 'jpg'
                elif '.png' in url_path:
                    suffix = 'png'
                elif '.webp' in url_path:
                    suffix = 'webp'

                if suffix:
                    live_cover_path = f'{save_dir}{fmtname}.{suffix}'
                    if os.path.exists(live_cover_path):
                        self.live_cover_path = live_cover_path
                    else:
                        response = requests.get(self.live_cover_url, headers=self.fake_headers, timeout=30)
                        with open(live_cover_path, 'wb') as f:
                            f.write(response.content)

                    if suffix == 'webp':
                        with Image.open(live_cover_path) as img:
                            img = img.convert('RGB')
                            img.save(f'{save_dir}{fmtname}.jpg', format='JPEG')
                        os.remove(live_cover_path)
                        live_cover_path = f'{save_dir}{fmtname}.jpg'

                    self.live_cover_path = live_cover_path
                    logger.info(
                        f'{self.plugin_msg}: 界面下载成功锛岃矾寰勶細{os.path.abspath(self.live_cover_path)}')
                else:
                    logger.warning(
                        f'{self.plugin_msg}: 界面涓轰笉支持鐨勬牸寮忥細{self.live_cover_url}')
            except:
                logger.exception(f'{self.plugin_msg}: 界面下载失败')

    async def acheck_url_healthy(self, url):
        async def __client_get(url, stream: bool = False):
            client.headers.update(self.fake_headers)
            if stream:
                async with client.stream("GET", url, timeout=60, follow_redirects=False) as response:
                    pass
            else:
                response = await client.get(url)
            if response.status_code not in (301, 302):
                response.raise_for_status()
            return response

        try:
            if '.m3u8' in url:
                r = await __client_get(url)
                import m3u8
                m3u8_obj = m3u8.loads(r.text)
                if m3u8_obj.is_variant:
                    url = m3u8_obj.playlists[0].uri
                    logger.info(f'{self.plugin_msg}: stream url: {url}')
                    r = await __client_get(url)
            else:  # 处理 Flv
                r = await __client_get(url, stream=True)
                if r.headers.get('Location'):
                    url = r.headers['Location']
                    # logger.info(f'{self.plugin_msg}: stream url: {url}')
                    # url = self.replace_url(url)
                    logger.info(f'{self.plugin_msg}: stream url: {url}')
                    r = await __client_get(url, stream=True)
            if r.status_code == 200:
                return url
        except HTTPStatusError as e:
            logger.debug(f'{self.plugin_msg}: url {url}: status_code-{e.response.status_code}')
        except:
            logger.debug(f'{self.plugin_msg}: url {url}: ', exc_info=True)
        return None

    def gen_download_filename(self, is_fmt=False):
        if self.filename_prefix:  # 鍒ゆ柇鏄惁存在鑷畾涔夊綍鎾懡鍚嶈缃?
            filename = (self.filename_prefix.format(streamer=self.fname, title=self.room_title).encode(
                'unicode-escape').decode()).encode().decode("unicode-escape")
        else:
            filename = f'{self.fname}%Y-%m-%dT%H_%M_%S'
        filename = get_valid_filename(filename)
        if is_fmt:
            file_time = time.time()
            while True:
                fmt_file_name = time.strftime(filename.encode("unicode-escape").decode(),
                                              time.localtime(file_time)).encode().decode("unicode-escape")
                if os.path.exists(f"{fmt_file_name}.{self.suffix}"):
                    file_time += 1
                else:
                    return fmt_file_name
        else:
            return filename

    def update_headers(self, headers):
        pass

    @staticmethod
    def download_file_rename(old_file_name, file_name):
        try:
            os.rename(old_file_name, file_name)
            logger.info(f'鏇村悕 {old_file_name} 涓?{file_name}')
        except:
            logger.error(f'鏇村悕 {old_file_name} 涓?{file_name} 失败', exc_info=True)

    def danmaku_init(self):
        pass

    def close(self):
        pass


def stream_gears_download(url, headers, file_name, segment_time=None, file_size=None,
                          file_name_callback: Callable[[str], None] = None):

    segment = stream_gears.PySegment()
    if segment_time:
        seg_time = segment_time.split(':')
        # print(int(seg_time[0]) * 60 * 60 + int(seg_time[1]) * 60 + int(seg_time[2]))
        segment.time = int(seg_time[0]) * 60 * 60 + int(seg_time[1]) * 60 + int(seg_time[2])
    if file_size:
        segment.size = file_size
    if file_size is None and segment_time is None:
        segment.size = 8 * 1024 * 1024 * 1024
    # FIXME: 下载鏃跺鍑虹幇403锛岃繖閲屼笉浼氬洖鍒颁笂灞傛柟娉曡幏鍙栨柊閾炬帴
    if file_name_callback:
        stream_gears.download_with_callback(
            url,
            headers,
            file_name,
            segment,
            file_name_callback
        )
    else:
        stream_gears.download(
            url,
            headers,
            file_name,
            segment,
        )


def sync_download(stream_url, headers, segment_duration=60, max_file_size=100, output_prefix="segment", stream_info=None, file_name_callback: Callable[[str], None] = None, database_row_id=0):
    logger.info(f"启动鍚屾下载鍣?max_file_size {max_file_size}MB")
    video_queue = queue.SimpleQueue()

    def upload(video_queue, stream_info, stop_event: threading.Event):
        with SessionLocal() as db:
            data = get_stream_info(db, f"{stream_info['name']}")
        data = {**data, "name": stream_info['name']}
        if "title" not in data:
            data["title"] = stream_info.get("title", "")
        # 浣跨敤 fmt_title_and_desc 鐢熸垚格式鍖栧悗鐨勬爣棰樺拰绠€浠?
        # fmt_title_and_desc 杩斿洖 (data, context)锛屽叾涓?context 涓寘鍚凡格式鍖栫殑 description
        data, context_fmt = fmt_title_and_desc(data)

        # 更新鍩烘湰信息锛堝惈 format_title锛?
        stream_info.update(data)

        # 鑻ュ瓨鍦ㄦ牸寮忓寲鍚庣殑绠€浠嬶紝灏嗗叾写入 stream_info锛屼繚璇佸悗缁笂浼犳椂浣跨敤姝ｇ‘鐨勭畝浠?
        if context_fmt.get('description'):
            stream_info['description'] = context_fmt['description']
        logger.info(f"stream_info: {stream_info}")
        # 获取 BiliWebAsync.__init__ 鐨勫弬鏁板悕
        init_params = inspect.signature(BiliWebAsync.__init__).parameters
        # 过滤 info 涓殑鏃犲叧閿?
        filtered_info = {key: value for key, value in stream_info.items() if key in init_params}

        filtered_info['submit_api'] = config.get('submit_api')
        filtered_info['lines'] = config.get('lines', 'AUTO')
        # 鏄犲皠 'uploader' 鍒?'principal'
        filtered_info['principal'] = ""
        filtered_info["data"] = stream_info
        uploader = BiliWebAsync(**filtered_info, video_queue=video_queue)
        uploader.upload(total_size=max_file_size * 1024 * 1024,
                        stop_event=stop_event, output_prefix=output_prefix,
                        file_name_callback=file_name_callback, database_row_id=database_row_id)
        # print("上传鍣ㄧ粨鏉?)
        logger.info(f"{stream_info['name']} 上传鍣ㄧ粨鏉?)
        # video_queue = queue.SimpleQueue()

    downloader = SyncDownloader(stream_url, headers, segment_duration, max_file_size, output_prefix, video_queue)

    # 启动上传鍣?
    upload_thread = threading.Thread(target=upload, args=(video_queue, stream_info, downloader.stop_event), daemon=True)
    upload_thread.start()

    downloader.run()
    logger.info(f"{stream_info['name']} 下载鍣ㄧ粨鏉?)


def get_valid_filename(name):
    """
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    # >>> get_valid_filename("john's portrait in 2004.jpg")
    >>> get_valid_filename("{self.fname}%Y-%m-%dT%H_%M_%S")
    '{self.fname}%Y-%m-%dT%H_%M_%S'
    """
    # s = str(name).strip().replace(" ", "_") #鍥犱负鏈変簺浜轰細鍦ㄤ富鎾悕涓棿鍔犲叆绌烘牸锛屼负浜嗛伩鍏嶅拰褰曟挱瀹屾瘯鑷姩鏀瑰悕鍐茬獊锛屾墍浠ユ敞閲婃帀
    s = re.sub(r"(?u)[^-\w.%{}\[\]銆愩€戙€屻€嶏紙锛夈兓掳銆併€?\s]", "", str(name))
    if s in {"", ".", ".."}:
        raise RuntimeError("Could not derive file name from '%s'" % name)

    # 处理%鐧惧垎鍙?
    directives = {
        'a', 'A', 'w', 'd', 'b', 'B', 'm', 'y', 'Y',
        'H', 'I', 'p', 'M', 'S', 'f', 'z', 'Z',
        'j', 'U', 'W', 'c', 'x', 'X', '%'
    }
    s = re.sub(r"%(.?)", lambda m: f"%{m[1]}" if m[1] in directives else f"%%{m[1]}", s)

    return s


def get_duration(segment_time_str, time_range_str):
    """
    璁＄畻褰撳墠时间鍒扮粰瀹氱粨鏉熸椂闂寸殑鏃跺樊
    濡傛灉璁＄畻鐨勬椂宸ぇ浜巗egment_time锛屽垯杩斿洖segment_time銆?
    """
    try:
        time_range = json.loads(time_range_str)
        if not isinstance(time_range, (list, tuple)) or len(time_range) != 2:
            return segment_time_str
        end_time = datetime.fromisoformat(time_range[1].replace('Z', '+00:00')).time()
    except Exception as e:
        return segment_time_str

    now = datetime.now(timezone.utc).time()
    now_sec = now.hour * 3600 + now.minute * 60 + now.second
    end_sec = end_time.hour * 3600 + end_time.minute * 60 + end_time.second

    # 璁＄畻鍒扮粨鏉熸椂闂寸殑绉掓暟
    diff = end_sec - now_sec if end_sec >= now_sec else (24 * 3600 - now_sec + end_sec)

    try:
        h, m, s = map(int, segment_time_str.split(':'))
        segment_sec = h * 3600 + m * 60 + s
    except Exception:
        return segment_time_str

    if diff > segment_sec:
        return segment_time_str

    hours = diff // 3600
    minutes = (diff % 3600) // 60
    seconds = diff % 60

    return f"{hours:02}:{minutes:02}:{seconds:02}"


class BatchCheck(ABC):
    @staticmethod
    @abstractmethod
    async def abatch_check(check_urls: List[str]) -> AsyncGenerator[str, None]:
        """
        鎵归噺检娴嬬洿鎾垨下载鐘舵€?
        杩斿洖鐨勬槸url_list
        """
