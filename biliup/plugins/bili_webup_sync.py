import asyncio
import base64
import concurrent.futures
import hashlib
import json
import logging
import math
import os
import re
import sys
import threading
import time
import queue
import urllib.parse
from dataclasses import asdict, dataclass, field, InitVar
from json import JSONDecodeError
from os.path import splitext, basename
from typing import Callable, Dict, Union, Any, List
from urllib import parse
from urllib.parse import quote

# import aiohttp
from concurrent.futures.thread import ThreadPoolExecutor
import concurrent
import requests.utils
import rsa
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter, Retry

from ..engine import Plugin
from ..engine.upload import UploadBase, logger


logger = logging.getLogger('biliup.engine.bili_web_sync')


@Plugin.upload(platform="bili_web_sync")
class BiliWebAsync(UploadBase):
    def __init__(
            self, principal, data, submit_api=None, copyright=2, postprocessor=None, dtime=None,
            dynamic='', lines='AUTO', threads=3, tid=122, tags=None, cover_path=None, description='',
            dolby=0, hires=0, no_reprint=0, is_only_self=0, charging_pay=0, credits=None,
            user_cookie='cookies.json', copyright_source=None, extra_fields="", video_queue=None
    ):
        super().__init__(principal, data, persistence_path='bili.cookie', postprocessor=postprocessor)
        if credits is None:
            credits = []
        if tags is None:
            tags = []
        self.lines = lines
        self.submit_api = submit_api
        self.threads = threads
        self.tid = tid
        self.tags = tags
        self.dtime = dtime
        if cover_path:
            self.cover_path = cover_path
        elif "live_cover_path" in self.data:
            self.cover_path = self.data["live_cover_path"]
        else:
            self.cover_path = None
        self.desc = description
        self.credits = credits
        self.dynamic = dynamic
        self.copyright = copyright
        self.dolby = dolby
        self.hires = hires
        self.no_reprint = no_reprint
        self.is_only_self = is_only_self
        self.charging_pay = charging_pay
        self.copyright_source = copyright_source
        self.extra_fields = extra_fields

        self.user_cookie = user_cookie
        self.video_queue: queue.SimpleQueue = video_queue

    def upload(self, total_size: int, stop_event: threading.Event, output_prefix: str, file_name_callback: Callable[[str], None] = None, database_row_id=0) -> List[UploadBase.FileInfo]:
        # print("寮€濮嬪悓姝ヤ笂浼?)
        logger.info(f"寮€濮嬪悓姝ヤ笂浼?{database_row_id}")
        file_index = 1
        videos = Data()
        bili = BiliBili(videos)
        bili.database_row_id = database_row_id

        bili.login(self.persistence_path, self.user_cookie)
        videos.title = self.data["format_title"][:80]  # 绋夸欢鏍囬闄愬埗80瀛?
        if self.credits:
            videos.desc_v2 = self.creditsToDesc_v2()
        else:
            videos.desc_v2 = [{
                "raw_text": self.desc,
                "biz_id": "",
                "type": 1
            }]
        videos.desc = self.desc
        videos.copyright = self.copyright
        if self.copyright == 2:
            videos.source = self.data["url"]  # 娣诲姞杞浇鍦板潃璇存槑
        # 璁剧疆瑙嗛鍒嗗尯,榛樿涓?74 鐢熸椿锛屽叾浠栧垎鍖?
        videos.tid = self.tid
        videos.set_tag(self.tags)
        if self.dtime:
            videos.delay_time(int(time.time()) + self.dtime)
        if self.cover_path:
            videos.cover = bili.cover_up(self.cover_path).replace('http:', '')

        # 鍏朵粬鍙傛暟璁剧疆
        videos.extra_fields = self.extra_fields
        videos.dolby = self.dolby
        videos.hires = self.hires
        videos.no_reprint = self.no_reprint
        videos.is_only_self = self.is_only_self
        videos.charging_pay = self.charging_pay

        thread_list = []
        while True:
            # 璋冭瘯浣跨敤 鍒唒 寮哄埗鍋滄
            # if file_index > 10:
            #     logger.info(f"[consumer debug] 鍋滄涓嬭浇鍥炶皟")
            #     stop_event.set()
            #     break

            file_name = f"{output_prefix}_{file_index}.mkv"

            # if file_name_callback:
            # file_name_callback(file_name)
            data_size = 0
            video_upload_queue = queue.SimpleQueue()

            t = threading.Thread(target=bili.upload_stream, args=(video_upload_queue,
                                 file_name, total_size, self.lines, videos, stop_event, file_name_callback), daemon=True, name=f"upload_{file_index}")
            thread_list.append(t)
            t.start()

            while True:
                try:
                    data = self.video_queue.get(timeout=10)
                except queue.Empty:
                    break

                if data is None:
                    video_upload_queue.put(None)
                    break

                video_upload_queue.put(data)
                # print(video_upload_queue.empty())
                data_size += len(data)
            # print(f"[consumer] 璇诲彇 {file_name} {data_size} 瀛楄妭")
            logger.info(f"[consumer] 璇诲彇 {file_name} {data_size} 瀛楄妭")
            file_index += 1
            # print("[consumer] bili.video.videos", bili.video.videos)
            logger.info(f"[consumer] bili.video.videos {bili.video.videos}")
            if data_size < 100:
                # print(f"[consumer] 鍋滄涓嬭浇鍥炶皟")
                # n = video_upload_queue.get()
                logger.info(f"[consumer] 鍋滄涓嬭浇鍥炶皟")
                stop_event.set()
                break

        logger.info("绛夊緟涓婁紶绾跨▼缁撴潫")
        for t in thread_list:
            t.join()

        # ret = bili.submit(self.submit_api)  # 鎻愪氦瑙嗛
        # logger.info(f"涓婁紶鎴愬姛: {ret}")
        file_list = []
        # if config.get('sync_save_dir', None):
        #     file_list = [os for file_name in os.listdir("sync_downloaded")]
        # print("涓婁紶瀹屾垚", file_list)
        return file_list

    def creditsToDesc_v2(self):
        desc_v2 = []
        desc_v2_tmp = self.desc
        for credit in self.credits:
            try:
                num = desc_v2_tmp.index("@credit")
                desc_v2.append({
                    "raw_text": " " + desc_v2_tmp[:num],
                    "biz_id": "",
                    "type": 1
                })
                desc_v2.append({
                    "raw_text": credit["username"],
                    "biz_id": str(credit["uid"]),
                    "type": 2
                })
                self.desc = self.desc.replace(
                    "@credit", "@" + credit["username"] + "  ", 1)
                desc_v2_tmp = desc_v2_tmp[num + 7:]
            except IndexError:
                logger.error('绠€浠嬩腑鐨凘credit鍗犱綅绗﹀皯浜巆redits鐨勬暟閲?鏇挎崲澶辫触')
        desc_v2.append({
            "raw_text": " " + desc_v2_tmp,
            "biz_id": "",
            "type": 1
        })
        desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 寮€澶寸┖鏍间細瀵艰嚧璇嗗埆绠€浠嬭繃闀?
        return desc_v2


class BiliBili:
    def __init__(self, video: 'Data'):
        self.app_key = None
        self.appsec = None
        # if self.app_key is None or self.appsec is None:
        self.app_key = 'ae57252b0c09105d'
        self.appsec = 'c75875c596a69eb55bd119e74b07cfe3'
        self.__session = requests.Session()
        self.video = video
        self.__session.mount('https://', HTTPAdapter(max_retries=Retry(total=5)))
        self.__session.headers.update({
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/63.0.3239.108",
            'referer': "https://www.bilibili.com/",
            'connection': 'keep-alive'
        })
        self.cookies = None
        self.access_token = None
        self.refresh_token = None
        self.account = None
        self.__bili_jct = None
        self._auto_os = None
        self.persistence_path = 'engine/bili.cookie'

        self.save_dir = config.get('sync_save_dir', None)
        self.save_path = ''
        if self.save_dir and not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self.database_row_id = 0

    def myinfo(self, cookies: dict = None):
        if cookies:
            requests.utils.add_dict_to_cookiejar(self.__session.cookies, cookies)
        response = self.__session.get('https://api.bilibili.com/x/space/myinfo', timeout=15)
        return response.json()

    def login(self, persistence_path, user_cookie):
        self.persistence_path = user_cookie
        if os.path.isfile(user_cookie):
            print('浣跨敤鎸佷箙鍖栧唴瀹逛笂浼?)
            self.load()
        if self.cookies:
            try:
                self.login_by_cookies(self.cookies)
            except:
                logger.exception('login error')
                self.login_by_password(**self.account)
        else:
            self.login_by_password(**self.account)
        self.store()

    def load(self):
        try:
            with open(self.persistence_path) as f:
                self.cookies = json.load(f)

                self.access_token = self.cookies['token_info']['access_token']
                self.refresh_token = self.cookies['token_info']['refresh_token']
        except (JSONDecodeError, KeyError):
            logger.exception('鍔犺浇cookie鍑洪敊')

    def store(self):
        with open(self.persistence_path, "w") as f:
            json.dump({**self.cookies,
                       'access_token': self.access_token,
                       'refresh_token': self.refresh_token
                       }, f)

    def login_by_password(self, username, password):
        print('浣跨敤璐﹀彿涓婁紶')
        key_hash, pub_key = self.get_key()
        encrypt_password = base64.b64encode(rsa.encrypt(f'{key_hash}{password}'.encode(), pub_key))
        payload = {
            "actionKey": 'appkey',
            "appkey": self.app_key,
            "build": 6270200,
            "captcha": '',
            "challenge": '',
            "channel": 'bili',
            "device": 'phone',
            "mobi_app": 'android',
            "password": encrypt_password,
            "permission": 'ALL',
            "platform": 'android',
            "seccode": "",
            "subid": 1,
            "ts": int(time.time()),
            "username": username,
            "validate": "",
        }
        response = self.__session.post("https://passport.bilibili.com/x/passport-login/oauth2/login", timeout=5,
                                       data={**payload, 'sign': self.sign(parse.urlencode(payload))})
        r = response.json()
        if r['code'] != 0 or r.get('data') is None or r['data'].get('cookie_info') is None:
            raise RuntimeError(r)
        try:
            for cookie in r['data']['cookie_info']['cookies']:
                self.__session.cookies.set(cookie['name'], cookie['value'])
                if 'bili_jct' == cookie['name']:
                    self.__bili_jct = cookie['value']
            self.cookies = self.__session.cookies.get_dict()
            self.access_token = r['data']['token_info']['access_token']
            self.refresh_token = r['data']['token_info']['refresh_token']
        except:
            raise RuntimeError(r)
        return r

    def login_by_cookies(self, cookie):
        cookies_dict = {c['name']: c['value'] for c in cookie['cookie_info']['cookies']}
        requests.utils.add_dict_to_cookiejar(self.__session.cookies, cookies_dict)
        if 'bili_jct' in cookies_dict:
            self.__bili_jct = cookies_dict['bili_jct']
        data = self.__session.get("https://api.bilibili.com/x/web-interface/nav", timeout=5).json()
        if data["code"] != 0:
            raise Exception(data)
        print('浣跨敤cookies涓婁紶')

    def sign(self, param):
        return hashlib.md5(f"{param}{self.appsec}".encode()).hexdigest()

    def get_key(self):
        url = "https://passport.bilibili.com/x/passport-login/web/key"
        payload = {
            'appkey': f'{self.app_key}',
            'sign': self.sign(f"appkey={self.app_key}"),
        }
        response = self.__session.get(url, data=payload, timeout=5)
        r = response.json()
        if r and r["code"] == 0:
            return r['data']['hash'], rsa.PublicKey.load_pkcs1_openssl_pem(r['data']['key'].encode())

    def probe(self):
        ret = self.__session.get('https://member.bilibili.com/preupload?r=probe', timeout=5).json()
        logger.info(f"绾胯矾:{ret['lines']}")
        data, auto_os = None, None
        min_cost = 0
        if ret['probe'].get('get'):
            method = 'get'
        else:
            method = 'post'
            data = bytes(int(1024 * 0.1 * 1024))
        for line in ret['lines']:
            start = time.perf_counter()
            test = self.__session.request(method, f"https:{line['probe_url']}", data=data, timeout=30)
            cost = time.perf_counter() - start
            print(line['query'], cost)
            if test.status_code != 200:
                return
            if not min_cost or min_cost > cost:
                auto_os = line
                min_cost = cost
        auto_os['cost'] = min_cost
        return auto_os

    def upload_stream(
            self,
            stream_queue: queue.SimpleQueue,
            file_name,
            total_size,
            lines='AUTO',
            videos: 'Data' = None,
            stop_event: threading.Event = None,
            file_name_callback: Callable[[str], None] = None,
            submit_api: Callable[[str], None] = None
    ):
        from biliup.app import context

        logger.info(f"{file_name} 寮€濮嬩笂浼?)
        if self.save_dir:
            self.save_path = os.path.join(self.save_dir, file_name)
        cs_upcdn = ['alia', 'bda', 'bda2', 'bldsa', 'qn', 'tx', 'txa']
        jd_upcdn = ['jd-alia', 'jd-bd', 'jd-bldsa', 'jd-tx', 'jd-txa']
        preferred_upos_cdn = None
        if not self._auto_os:
            if lines in cs_upcdn:
                self._auto_os = {"os": "upos", "query": f"upcdn={lines}&probe_version=20221109",
                                 "probe_url": f"//upos-cs-upcdn{lines}.bilivideo.com/OK"}
                preferred_upos_cdn = lines
            elif lines in jd_upcdn:
                lines = lines.split('-')[1]
                self._auto_os = {"os": "upos", "query": f"upcdn={lines}&probe_version=20221109",
                                 "probe_url": f"//upos-jd-upcdn{lines}.bilivideo.com/OK"}
                preferred_upos_cdn = lines
            else:
                self._auto_os = self.probe()
            logger.info(f"绾胯矾閫夋嫨 => {self._auto_os['os']}: {self._auto_os['query']}. time: {self._auto_os.get('cost')}")
        if self._auto_os['os'] == 'upos':
            upload = self.upos_stream
        else:
            logger.error(f"NoSearch:{self._auto_os['os']}")
            raise NotImplementedError(self._auto_os['os'])
        logger.info(f"os: {self._auto_os['os']}")
        query = {
            'r': self._auto_os['os'],
            'profile': 'ugcupos/bup',
            'ssl': 0,
            'version': '2.8.12',
            'build': 2081200,
            'name': file_name,
            'size': total_size,
        }
        resp = self.__session.get(
            f"https://member.bilibili.com/preupload?{self._auto_os['query']}", params=query,
            timeout=5)
        ret = resp.json()
        if "chunk_size" not in ret:
            stop_event.set()
            return
        logger.debug(f"preupload: {ret}")
        if preferred_upos_cdn:
            # 濡傛灉杩斿洖鐨別ndpoint涓嶅湪probe_url涓紝鍒欏皾璇曞湪endpoints涓牎楠宲robe_url鏄惁鍙敤
            if ret['endpoint'] not in self._auto_os['probe_url']:
                for endpoint in ret['endpoints']:
                    if endpoint in self._auto_os['probe_url']:
                        ret['endpoint'] = endpoint
                        logger.info(f"淇敼endpoint: {ret['endpoint']}")
                        break
                else:
                    logger.warning(f"閫夋嫨鐨勭嚎璺?{self._auto_os['os']} 娌℃湁杩斿洖瀵瑰簲 endpoint锛屼笉鍋氫慨鏀?)
        video_part = asyncio.run(upload(stream_queue, file_name, total_size, ret))
        if video_part is None:
            stop_event.set()
            # print("寮傚父娴?鐩存帴閫€鍑?)
            return
        video_part['title'] = video_part['title'][:80]

        if str(self.database_row_id) in context["sync_downloader_map"]:
            context_data = context["sync_downloader_map"][str(self.database_row_id)].copy()
            context_data.pop('subtitle', None)
            videos = Data(**context_data)

        videos.append(video_part)  # 娣诲姞宸茬粡涓婁紶鐨勮棰?
        edit = False if videos.aid is None else True
        ret = self.submit(submit_api=submit_api, edit=edit, videos=videos)
        # logger.info(f"涓婁紶鎴愬姛: {ret}")
        if edit:
            logger.info(f"缂栬緫娣诲姞鎴愬姛: {ret}")
        else:
            logger.info(f"涓婁紶鎴愬姛: {ret}")
        aid = ret['data']['aid']
        videos.aid = aid
        context['sync_downloader_map'][str(self.database_row_id)] = videos.__dict__
        logger.info(f"涓婁紶瀹屾垚 {file_name} {context['sync_downloader_map'][str(self.database_row_id)] }")
        if file_name_callback:
            file_name_callback(self.save_path)

    async def upos_stream(self, stream_queue, file_name, total_size, ret):
        # print("--------------, ", file_name)
        chunk_size = ret['chunk_size']
        auth = ret["auth"]
        endpoint = ret["endpoint"]
        biz_id = ret["biz_id"]
        upos_uri = ret["upos_uri"]
        url = f"https:{endpoint}/{upos_uri.replace('upos://', '')}"  # 瑙嗛涓婁紶璺緞
        headers = {
            "X-Upos-Auth": auth
        }
        # 鍚戜笂浼犲湴鍧€鐢宠涓婁紶锛屽緱鍒颁笂浼爄d绛変俊鎭?
        upload_id = self.__session.post(f'{url}?uploads&output=json', timeout=15,
                                        headers=headers).json()["upload_id"]
        # 寮€濮嬩笂浼?
        parts = []  # 鍒嗗潡淇℃伅
        chunks = math.ceil(total_size / chunk_size)  # 鑾峰彇鍒嗗潡鏁伴噺

        start = time.perf_counter()

        # print("-----------")
        # print(upload_id, chunks, chunk_size, total_size)
        logger.info(
            f"{file_name} - upload_id: {upload_id}, chunks: {chunks}, chunk_size: {chunk_size}, total_size: {total_size}")
        n = 0
        st = time.perf_counter()
        max_workers = 3
        semaphore = threading.Semaphore(max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for index, chunk in enumerate(self.queue_reader_generator(stream_queue, chunk_size, total_size)):
                if not chunk:
                    break
                const_time = time.perf_counter() - st
                speed = len(chunk) * 8 / 1024 / 1024 / const_time
                logger.info(f"{file_name} - chunks-({index+1}/{chunks}) - down - speed: {speed:.2f}Mbps")
                n += len(chunk)
                params = {
                    'uploadId': upload_id,
                    'chunks': chunks,
                    'total': total_size,
                    'chunk': index,
                    'size': chunk_size,
                    'partNumber': index + 1,
                    'start': index * chunk_size,
                    'end': index * chunk_size + chunk_size
                }
                params_clone = params.copy()
                semaphore.acquire()
                future = executor.submit(self.upload_chunk_thread,
                                         url, chunk, params_clone, headers, file_name)
                future.add_done_callback(lambda x: semaphore.release())
                futures.append(future)
                st = time.perf_counter()

                for f in list(futures):
                    if f.done():
                        futures.remove(f)

                # 绛夊緟鎵€鏈夊垎鐗囦笂浼犲畬鎴愶紝骞舵寜椤哄簭鏀堕泦缁撴灉
            for future in concurrent.futures.as_completed(futures):
                pass

            results = [{
                "partNumber": i + 1,
                "eTag": "etag"
            } for i in range(chunks)]
            parts.extend(results)

        if n == 0:
            return None
        logger.info(f"{file_name} - total_size: {total_size}, n: {n}")
        cost = time.perf_counter() - start
        p = {
            'name': file_name,
            'uploadId': upload_id,
            'biz_id': biz_id,
            'output': 'json',
            'profile': 'ugcupos/bup'
        }
        attempt = 1
        while attempt <= 3:  # 涓€鏃︽斁寮冨氨浼氫涪澶卞墠闈㈡墍鏈夌殑杩涘害锛屽璇曞嚑娆″惂
            try:
                r = self.__session.post(url, params=p, json={"parts": parts}, headers=headers, timeout=15).json()
                if r.get('OK') == 1:
                    logger.info(f'{file_name} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {r}')
                    return {"title": splitext(file_name)[0], "filename": splitext(basename(upos_uri))[0], "desc": ""}
                raise IOError(r)
            except IOError:
                logger.info(f"璇锋眰鍚堝苟鍒嗙墖 {file_name} 鏃跺嚭鐜伴棶棰橈紝灏濊瘯閲嶈繛锛屾鏁帮細" + str(attempt))
                attempt += 1
                time.sleep(10)
        pass

    def upload_chunk_thread(self, url, chunk, params_clone, headers, file_name, max_retries=3, backoff_factor=1):
        st = time.perf_counter()
        retries = 0
        while retries < max_retries:
            try:
                r = requests.put(url=url, params=params_clone, data=chunk, headers=headers)

                # 濡傛灉涓婁紶鎴愬姛锛岄€€鍑洪噸璇曞惊鐜?
                if r.status_code == 200:
                    const_time = time.perf_counter() - st
                    speed = len(chunk) * 8 / 1024 / 1024 / const_time
                    logger.info(
                        f"{file_name} - chunks-{params_clone['chunk'] +1 } - up status: {r.status_code} - speed: {speed:.2f}Mbps"
                    )
                    return {
                        "partNumber": params_clone['chunk'] + 1,
                        "eTag": "etag"
                    }

                # 濡傛灉涓婁紶澶辫触锛屼絾鏈揪鍒版渶澶ч噸璇曟鏁帮紝绛夊緟涓€娈垫椂闂村悗閲嶈瘯
                else:
                    retries += 1
                    logger.warning(
                        f"{file_name} - chunks-{params_clone['chunk']} - up failed: {r.status_code}. Retrying {retries}/{max_retries}")

                    # 璁＄畻閫€閬挎椂闂达紝閫愭澧炲姞閲嶈瘯闂撮殧
                    backoff_time = backoff_factor ** retries
                    time.sleep(backoff_time)

            except Exception as e:
                retries += 1
                logger.error(f"upload_chunk_thread err {str(e)}. Retrying {retries}/{max_retries}")

                # 璁＄畻閫€閬挎椂闂达紝閫愭澧炲姞閲嶈瘯闂撮殧
                backoff_time = backoff_factor ** retries
                time.sleep(backoff_time)

        # 濡傛灉閲嶈瘯浜嗘墍鏈夋鏁颁粛鐒跺け璐ワ紝璁板綍閿欒
        logger.error(f"{file_name} - chunks-{params_clone['chunk']} - Upload failed after {max_retries} attempts.")
        return None

    def queue_reader_generator(self, simple_queue: queue.SimpleQueue, chunk_size: int, max_size: int):
        """
        浠?simple_queue 涓鍙栨暟鎹苟鎸?chunk_size 澶у皬鍒嗗潡浜у嚭 (yield)
        褰撻槦鍒椾腑鑾峰彇鍒?None 鎴栬€呮暟鎹€婚噺杈惧埌 max_size 鍚庯紝灏辩敤 0x00 琛ラ綈鍒?chunk_size

        :param simple_queue: queue.SimpleQueue 瀹炰緥锛屾暟鎹祦浼氫互澶氫釜鍒嗗寘 (bytes) 鍏ラ槦锛屾渶鍚庝互 None 琛ㄧず缁撴潫
        :param chunk_size: 娑堣垂鑰呮瘡娆℃兂瑕佽幏鍙栫殑鏁版嵁鍧楀ぇ灏?
        :param max_size: 闇€瑕佹渶缁堣ˉ榻愮殑鎬诲ぇ灏忥紙鍗曚綅锛氬瓧鑺傦級锛屽繀椤绘槸 chunk_size 鐨勬暣鏁板€?
        :return: 鐢熸垚鍣紝鎸?chunk_size 澶у皬鍒嗘壒娆′骇鍑烘暟鎹?
        """
        if max_size % chunk_size != 0:
            raise ValueError("max_size must be a multiple of chunk_size")

        total_chunks = max_size // chunk_size
        chunks_yielded = 0
        current_buffer = bytearray()
        save_file = None
        if self.save_dir:
            save_file = open(self.save_path, "wb")

        while chunks_yielded < total_chunks:
            try:
                data = simple_queue.get(timeout=10)
            except queue.Empty:
                break

            if data is None:
                # 鏁版嵁娴佺粨鏉燂紝鐢?x00濉厖鍓╀綑鐨勫潡
                remaining_chunks = total_chunks - chunks_yielded
                if remaining_chunks == total_chunks:
                    # print("绌哄寘璺宠繃")
                    break
                if len(current_buffer) > 0:
                    # 澶勭悊褰撳墠缂撳啿鍖轰腑鐨勬渶鍚庝竴鍧楁暟鎹?
                    padding_size = chunk_size - len(current_buffer)
                    if padding_size > 0:
                        current_buffer += b'\x00' * padding_size
                        logger.info(f"鏈€鍚庝竴涓寘宸簡 {padding_size} 涓瓧鑺?)
                    yield bytes(current_buffer)
                    chunks_yielded += 1
                    remaining_chunks -= 1
                break
                logger.info(f"杩樺樊 {remaining_chunks} 涓畬鏁村寘")

                # 杈撳嚭鍓╀綑鐨勫叏0鍧?
                for _ in range(remaining_chunks):
                    yield b'\x00' * chunk_size
                    chunks_yielded += 1
                break

            save_file and save_file.write(data)

            # 灏嗘柊鏁版嵁娣诲姞鍒扮紦鍐插尯
            current_buffer.extend(data)

            # 杈撳嚭瀹屾暣鐨勫潡
            while len(current_buffer) >= chunk_size and chunks_yielded < total_chunks:
                yield bytes(current_buffer[:chunk_size])
                current_buffer = current_buffer[chunk_size:]
                chunks_yielded += 1

        # print("鏈鍒唒瀹屾垚")
        save_file and save_file.close()
        yield None

    def submit(self, submit_api=None, edit=False, videos=None):

        # 涓嶈兘鎻愪氦 extra_fields 瀛楁锛屾彁鍓嶅鐞?
        post_data = asdict(videos)
        if post_data.get('extra_fields'):
            for key, value in json.loads(post_data.pop('extra_fields')).items():
                post_data.setdefault(key, value)

        self.__session.get('https://member.bilibili.com/x/geetest/pre/add', timeout=5)

        if submit_api is None:
            total_info = self.myinfo()
            if total_info.get('data') is None:
                logger.error(total_info)
            total_info = total_info.get('data')
            if total_info['level'] > 3 and total_info['follower'] > 1000:
                user_weight = 2
            else:
                user_weight = 1
            logger.info(f'鎺ㄦ祴鐨勭敤鎴锋潈閲? {user_weight}')
            # submit_api = 'web' if user_weight == 2 else 'client'
            # web 鐩墠锛?025-01-26锛夊叏閲忓垎p鍔熻兘
            submit_api = 'web'
        ret = None
        if submit_api == 'web':
            ret = self.submit_web(post_data, edit=edit)
            if ret["code"] == 21138:
                time.sleep(5)
                logger.info(f'鏀圭敤瀹㈡埛绔帴鍙ｆ彁浜ret}')
                submit_api = 'client'
        if submit_api == 'client':
            ret = self.submit_client(post_data, edit=edit)
        if not ret:
            raise Exception(f'涓嶅瓨鍦ㄧ殑閫夐」锛歿submit_api}')
        if ret["code"] == 0:
            return ret
        else:
            raise Exception(ret)

    def submit_web(self, post_data, edit=False):
        logger.info('浣跨敤缃戦〉绔痑pi鎻愪氦')
        if not self.__bili_jct:
            raise RuntimeError("bili_jct is required!")
        api = 'https://member.bilibili.com/x/vu/web/add?csrf=' + self.__bili_jct
        if edit:
            api = 'https://member.bilibili.com/x/vu/web/edit?csrf=' + self.__bili_jct
        return self.__session.post(api, timeout=5,
                                   json=post_data).json()

    def submit_client(self, post_data, edit=False):
        logger.info('浣跨敤瀹㈡埛绔痑pi绔彁浜?)
        if not self.access_token:
            if self.account is None:
                raise RuntimeError("Access token is required, but account and access_token does not exist!")
            self.login_by_password(**self.account)
            self.store()
        api = 'http://member.bilibili.com/x/vu/client/add?access_key=' + self.access_token
        if edit:
            api = 'http://member.bilibili.com/x/vu/client/edit?access_key=' + self.access_token
        logger.debug(f"client api submit: {post_data}")
        while True:
            ret = self.__session.post(api, timeout=5, json=post_data).json()
            if ret['code'] == -101:
                logger.info(f'鍒锋柊token{ret}')
                self.login_by_password(**config['user']['account'])
                self.store()
                continue
            return ret

    def cover_up(self, img: str):
        """
        :param img: img path or stream
        :return: img URL
        """
        from PIL import Image
        from io import BytesIO

        with Image.open(img) as im:
            # 瀹藉拰楂?闇€瑕?6锛?0
            xsize, ysize = im.size
            if xsize / ysize > 1.6:
                delta = xsize - ysize * 1.6
                region = im.crop((delta / 2, 0, xsize - delta / 2, ysize))
            else:
                delta = ysize - xsize * 10 / 16
                region = im.crop((0, delta / 2, xsize, ysize - delta / 2))
            buffered = BytesIO()
            region.save(buffered, format=im.format)
        r = self.__session.post(
            url='https://member.bilibili.com/x/vu/web/cover/up',
            data={
                'cover': b'data:image/jpeg;base64,' + (base64.b64encode(buffered.getvalue())),
                'csrf': self.__bili_jct
            }, timeout=30
        )
        buffered.close()
        res = r.json()
        if res.get('data') is None:
            raise Exception(res)
        return res['data']['url']

    def get_tags(self, upvideo, typeid="", desc="", cover="", groupid=1, vfea=""):
        """
        涓婁紶瑙嗛鍚庤幏寰楁帹鑽愭爣绛?
        :param vfea:
        :param groupid:
        :param typeid:
        :param desc:
        :param cover:
        :param upvideo:
        :return: 杩斿洖瀹樻柟鎺ㄨ崘鐨則ag
        """
        url = f'https://member.bilibili.com/x/web/archive/tags?'
        f'typeid={typeid}&title={quote(upvideo["title"])}&filename=filename&desc={desc}&cover={cover}'
        f'&groupid={groupid}&vfea={vfea}'
        return self.__session.get(url=url, timeout=5).json()

    def __enter__(self):
        return self

    def __exit__(self, e_t, e_v, t_b):
        self.close()

    def close(self):
        """Closes all adapters and as such the session"""
        self.__session.close()


@dataclass
class Data:
    """
    cover: 灏侀潰鍥剧墖锛屽彲鐢眗ecovers鏂规硶寰楀埌瑙嗛鐨勫抚鎴浘
    """
    copyright: int = 2
    source: str = ''
    tid: int = 21
    cover: str = ''
    title: str = ''
    desc_format_id: int = 0
    desc: str = ''
    desc_v2: list = field(default_factory=list)
    dynamic: str = ''
    subtitle: dict = field(init=False)
    tag: Union[list, str] = ''
    videos: list = field(default_factory=list)
    dtime: Any = None
    open_subtitle: InitVar[bool] = False
    dolby: int = 0
    hires: int = 0
    no_reprint: int = 0
    is_only_self: int = 0
    charging_pay: int = 0
    extra_fields: str = ""

    aid: int = None
    # interactive: int = 0
    # no_reprint: int 1
    # charging_pay: int 1

    def __post_init__(self, open_subtitle):
        self.subtitle = {"open": int(open_subtitle), "lan": ""}
        if self.dtime and self.dtime - int(time.time()) <= 14400:
            self.dtime = None
        if isinstance(self.tag, list):
            self.tag = ','.join(self.tag)

    def delay_time(self, dtime: int):
        """璁剧疆寤舵椂鍙戝竷鏃堕棿锛岃窛绂绘彁浜ゅぇ浜?灏忔椂锛屾牸寮忎负10浣嶆椂闂存埑"""
        if dtime - int(time.time()) > 7200:
            self.dtime = dtime

    def set_tag(self, tag: list):
        """璁剧疆鏍囩锛宼ag涓烘暟缁?""
        self.tag = ','.join(tag)

    def append(self, video):
        self.videos.append(video)
