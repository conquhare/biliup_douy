锘縤mport asyncio
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
            dynamic='', lines='AUTO', threads=3, td=122, tags=None, cover_path=None, description='',
            dolby=0, hires=0, no_reprint=0, is_only_self=0, charging_pay=0, credits=None,
            user_cookie='cookies.json', copyright_source=None, extra_fields="", vdeo_queue=None
    ):
        super().__init__(principal, data, persistence_path='bili.cookie', postprocessor=postprocessor)
        if credits is None:
            credits = []
        if tags is None:
            tags = []
        self.lines = lines
        self.submit_api = submit_api
        self.threads = threads
        self.td = td
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
        self.vdeo_queue: queue.SimpleQueue = vdeo_queue

    def upload(self, total_size: int, stop_event: threading.Event, output_prefix: str, file_name_callback: Callable[[str], None] = None, database_row_d=0) -> List[UploadBase.FileInfo]:
        # print("瀵偓婵鎮撳銉ょ瑐娴?)
        logger.info(f"瀵偓婵鎮撳銉ょ瑐娴?{database_row_d}")
        file_index = 1
        vdeos = Data()
        bili = BiliBili(vdeos)
        bili.database_row_d = database_row_d

        bili.login(self.persistence_path, self.user_cookie)
        vdeos.title = self.data["format_title"][:80]  # 缁嬪じ娆㈤弽鍥暯闄愬埗80鐎?
        if self.credits:
            vdeos.desc_v2 = self.creditsToDesc_v2()
        else:
            vdeos.desc_v2 = [{
                "raw_text": self.desc,
                "biz_d": "",
                "type": 1
            }]
        vdeos.desc = self.desc
        vdeos.copyright = self.copyright
        if self.copyright == 2:
            vdeos.source = self.data["url"]  # 濞ｈ濮炴潪顒冩祰閸︽澘娼冭鏄?
        # 璁剧疆鐟欏棝顣堕崚鍡楀隘,姒涙顓绘稉?74 閻㈢喐妞块敍灞藉従娴犳牕鍨庨崠?
        vdeos.td = self.td
        vdeos.set_tag(self.tags)
        if self.dtime:
            vdeos.delay_time(int(time.time()) + self.dtime)
        if self.cover_path:
            vdeos.cover = bili.cover_up(self.cover_path).replace('http:', '')

        # 鍏朵粬鍙傛暟璁剧疆
        vdeos.extra_fields = self.extra_fields
        vdeos.dolby = self.dolby
        vdeos.hires = self.hires
        vdeos.no_reprint = self.no_reprint
        vdeos.is_only_self = self.is_only_self
        vdeos.charging_pay = self.charging_pay

        thread_list = []
        while True:
            # 鐠嬪啳鐦娇鐢?閸掑敀 瀵搫鍩楀仠姝?
            # if file_index > 10:
            #     logger.info(f"[consumer debug] 鍋滄涓嬭浇閸ョ偠鐨?)
            #     stop_event.set()
            #     break

            file_name = f"{output_prefix}_{file_index}.mkv"

            # if file_name_callback:
            # file_name_callback(file_name)
            data_size = 0
            vdeo_upload_queue = queue.SimpleQueue()

            t = threading.Thread(target=bili.upload_stream, args=(vdeo_upload_queue,
                                 file_name, total_size, self.lines, vdeos, stop_event, file_name_callback), daemon=True, name=f"upload_{file_index}")
            thread_list.append(t)
            t.start()

            while True:
                try:
                    data = self.vdeo_queue.get(timeout=10)
                except queue.Empty:
                    break

                if data is None:
                    vdeo_upload_queue.put(None)
                    break

                vdeo_upload_queue.put(data)
                # print(vdeo_upload_queue.empty())
                data_size += len(data)
            # print(f"[consumer] 璇诲彇 {file_name} {data_size} 瀛楄妭")
            logger.info(f"[consumer] 璇诲彇 {file_name} {data_size} 瀛楄妭")
            file_index += 1
            # print("[consumer] bili.vdeo.vdeos", bili.vdeo.vdeos)
            logger.info(f"[consumer] bili.vdeo.vdeos {bili.vdeo.vdeos}")
            if data_size < 100:
                # print(f"[consumer] 鍋滄涓嬭浇閸ョ偠鐨?)
                # n = vdeo_upload_queue.get()
                logger.info(f"[consumer] 鍋滄涓嬭浇閸ョ偠鐨?)
                stop_event.set()
                break

        logger.info("绛夊緟涓婁紶缁捐法鈻肩粨鏉?)
        for t in thread_list:
            t.join()

        # ret = bili.submit(self.submit_api)  # 閹绘劒姘︾憴鍡涱暥
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
                    "biz_d": "",
                    "type": 1
                })
                desc_v2.append({
                    "raw_text": credit["username"],
                    "biz_d": str(credit["ud"]),
                    "type": 2
                })
                self.desc = self.desc.replace(
                    "@credit", "@" + credit["username"] + "  ", 1)
                desc_v2_tmp = desc_v2_tmp[num + 7:]
            except IndexError:
                logger.error('缁犫偓娴犲鑵戦惃鍑榗redit閸楃姳缍呯粭锕€鐨禍宸唕edits閻ㄥ嫭鏆熼柌?鏇挎崲澶辫触')
        desc_v2.append({
            "raw_text": " " + desc_v2_tmp,
            "biz_d": "",
            "type": 1
        })
        desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 瀵偓婢跺鈹栭弽闂寸窗鐎佃壈鍤х拠鍡楀焼缁犫偓娴犲绻冮梹?
        return desc_v2


class BiliBili:
    def __init__(self, vdeo: 'Data'):
        self.app_key = None
        self.appsec = None
        # if self.app_key is None or self.appsec is None:
        self.app_key = 'ae57252b0c09105d'
        self.appsec = 'c75875c596a69eb55bd119e74b07cfe3'
        self.__session = requests.Session()
        self.vdeo = vdeo
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

        self.database_row_d = 0

    def myinfo(self, cookies: dict = None):
        if cookies:
            requests.utils.add_dict_to_cookiejar(self.__session.cookies, cookies)
        response = self.__session.get('https://api.bilibili.com/x/space/myinfo', timeout=15)
        return response.json()

    def login(self, persistence_path, user_cookie):
        self.persistence_path = user_cookie
        if os.path.isfile(user_cookie):
            print('浣跨敤閹镐椒绠欓崠鏍у敶鐎归€涚瑐娴?)
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
            logger.exception('閸旂姾娴嘽ookie閸戞椽鏁?)

    def store(self):
        with open(self.persistence_path, "w") as f:
            json.dump({**self.cookies,
                       'access_token': self.access_token,
                       'refresh_token': self.refresh_token
                       }, f)

    def login_by_password(self, username, password):
        print('浣跨敤鐠愶箑褰夸笂浼?)
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
            "mobi_app": 'androd',
            "password": encrypt_password,
            "permission": 'ALL',
            "platform": 'androd',
            "seccode": "",
            "subd": 1,
            "ts": int(time.time()),
            "username": username,
            "valdate": "",
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
        logger.info(f"缁捐儻鐭?{ret['lines']}")
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
            vdeos: 'Data' = None,
            stop_event: threading.Event = None,
            file_name_callback: Callable[[str], None] = None,
            submit_api: Callable[[str], None] = None
    ):
        from biliup.app import context

        logger.info(f"{file_name} 瀵偓婵绗傛导?)
        if self.save_dir:
            self.save_path = os.path.join(self.save_dir, file_name)
        cs_upcdn = ['alia', 'bda', 'bda2', 'bldsa', 'qn', 'tx', 'txa']
        jd_upcdn = ['jd-alia', 'jd-bd', 'jd-bldsa', 'jd-tx', 'jd-txa']
        preferred_upos_cdn = None
        if not self._auto_os:
            if lines in cs_upcdn:
                self._auto_os = {"os": "upos", "query": f"upcdn={lines}&probe_version=20221109",
                                 "probe_url": f"//upos-cs-upcdn{lines}.bilivdeo.com/OK"}
                preferred_upos_cdn = lines
            elif lines in jd_upcdn:
                lines = lines.split('-')[1]
                self._auto_os = {"os": "upos", "query": f"upcdn={lines}&probe_version=20221109",
                                 "probe_url": f"//upos-jd-upcdn{lines}.bilivdeo.com/OK"}
                preferred_upos_cdn = lines
            else:
                self._auto_os = self.probe()
            logger.info(f"缁捐儻鐭鹃€夋嫨 => {self._auto_os['os']}: {self._auto_os['query']}. time: {self._auto_os.get('cost')}")
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
            # 濡傛灉杩斿洖鐨刵dpoint娑撳秴婀猵robe_url娑擃叏绱濋崚娆忕毦鐠囨洖婀猠ndpoints娑擃厽鐗庢瀹瞨obe_url閺勵垰鎯侀崣顖滄暏
            if ret['endpoint'] not in self._auto_os['probe_url']:
                for endpoint in ret['endpoints']:
                    if endpoint in self._auto_os['probe_url']:
                        ret['endpoint'] = endpoint
                        logger.info(f"娣囶喗鏁糴ndpoint: {ret['endpoint']}")
                        break
                else:
                    logger.warning(f"閫夋嫨閻ㄥ嫮鍤庣捄?{self._auto_os['os']} 娌℃湁杩斿洖鐎电懓绨?endpoint閿涘奔绗夐崑姘叏閺€?)
        vdeo_part = asyncio.run(upload(stream_queue, file_name, total_size, ret))
        if vdeo_part is None:
            stop_event.set()
            # print("瀵倸鐖跺ù?閻╁瓨甯撮柅鈧崙?)
            return
        vdeo_part['title'] = vdeo_part['title'][:80]

        if str(self.database_row_d) in context["sync_downloader_map"]:
            context_data = context["sync_downloader_map"][str(self.database_row_d)].copy()
            context_data.pop('subtitle', None)
            vdeos = Data(**context_data)

        vdeos.append(vdeo_part)  # 濞ｈ濮炲鑼病涓婁紶閻ㄥ嫯顫嬫０?
        edit = False if vdeos.ad is None else True
        ret = self.submit(submit_api=submit_api, edit=edit, vdeos=vdeos)
        # logger.info(f"涓婁紶鎴愬姛: {ret}")
        if edit:
            logger.info(f"缂栬緫濞ｈ濮炴垚鍔? {ret}")
        else:
            logger.info(f"涓婁紶鎴愬姛: {ret}")
        ad = ret['data']['ad']
        vdeos.ad = ad
        context['sync_downloader_map'][str(self.database_row_d)] = vdeos.__dict__
        logger.info(f"涓婁紶瀹屾垚 {file_name} {context['sync_downloader_map'][str(self.database_row_d)] }")
        if file_name_callback:
            file_name_callback(self.save_path)

    async def upos_stream(self, stream_queue, file_name, total_size, ret):
        # print("--------------, ", file_name)
        chunk_size = ret['chunk_size']
        auth = ret["auth"]
        endpoint = ret["endpoint"]
        biz_d = ret["biz_d"]
        upos_uri = ret["upos_uri"]
        url = f"https:{endpoint}/{upos_uri.replace('upos://', '')}"  # 鐟欏棝顣朵笂浼犵捄顖氱窞
        headers = {
            "X-Upos-Auth": auth
        }
        # 閸氭垳绗傛导鐘叉勾鍧€閻㈠疇顕笂浼犻敍灞界繁閸掗绗傛导鐖刣缁涘淇婇幁?
        upload_d = self.__session.post(f'{url}?uploads&output=json', timeout=15,
                                        headers=headers).json()["upload_d"]
        # 瀵偓婵绗傛导?
        parts = []  # 閸掑棗娼′俊鎭?
        chunks = math.ceil(total_size / chunk_size)  # 鑾峰彇閸掑棗娼℃暟閲?

        start = time.perf_counter()

        # print("-----------")
        # print(upload_d, chunks, chunk_size, total_size)
        logger.info(
            f"{file_name} - upload_d: {upload_d}, chunks: {chunks}, chunk_size: {chunk_size}, total_size: {total_size}")
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
                    'uploadId': upload_d,
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

                # 绛夊緟閹碘偓閺堝鍨庨悧鍥︾瑐娴肩姴鐣幋鎰剁礉楠炶埖瀵滄い鍝勭碍閺€鍫曟肠缁撴灉
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
            'uploadId': upload_d,
            'biz_d': biz_d,
            'output': 'json',
            'profile': 'ugcupos/bup'
        }
        attempt = 1
        while attempt <= 3:  # 娑撯偓閺冿附鏂佸鍐ㄦ皑娴兼矮娑径鍗炲闂堛垺澧嶉張澶屾畱鏉╂稑瀹抽敍灞筋樋鐠囨洖鍤戝▎鈥冲惂
            try:
                r = self.__session.post(url, params=p, json={"parts": parts}, headers=headers, timeout=15).json()
                if r.get('OK') == 1:
                    logger.info(f'{file_name} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {r}')
                    return {"title": splitext(file_name)[0], "filename": splitext(basename(upos_uri))[0], "desc": ""}
                raise IOError(r)
            except IOError:
                logger.info(f"璇锋眰鍚堝苟鍒嗙墖 {file_name} 閺冭泛鍤悳浼存６妫版﹫绱濆皾璇曢柌宥堢箾閿涘本顐奸弫甯窗" + str(attempt))
                attempt += 1
                time.sleep(10)
        pass

    def upload_chunk_thread(self, url, chunk, params_clone, headers, file_name, max_retries=3, backoff_factor=1):
        st = time.perf_counter()
        retries = 0
        while retries < max_retries:
            try:
                r = requests.put(url=url, params=params_clone, data=chunk, headers=headers)

                # 濡傛灉涓婁紶鎴愬姛閿涘矂鈧偓閸戞椽鍣哥拠鏇炴儕閻?
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

                # 濡傛灉涓婁紶澶辫触閿涘奔绲鹃張顏囨彧閸掔増娓舵径褔鍣哥拠鏇燁偧閺佸府绱濈瓑寰呮稉鈧▓鍨闂傛潙鎮楅噸璇?
                else:
                    retries += 1
                    logger.warning(
                        f"{file_name} - chunks-{params_clone['chunk']} - up failed: {r.status_code}. Retrying {retries}/{max_retries}")

                    # 鐠侊紕鐣婚柅鈧柆鎸庢闂傝揪绱濋柅鎰劄婢х偛濮為噸璇曢梻鎾
                    backoff_time = backoff_factor ** retries
                    time.sleep(backoff_time)

            except Exception as e:
                retries += 1
                logger.error(f"upload_chunk_thread err {str(e)}. Retrying {retries}/{max_retries}")

                # 鐠侊紕鐣婚柅鈧柆鎸庢闂傝揪绱濋柅鎰劄婢х偛濮為噸璇曢梻鎾
                backoff_time = backoff_factor ** retries
                time.sleep(backoff_time)

        # 濡傛灉閲嶈瘯娴滃棙澧嶉張澶嬵偧閺侀绮涢悞璺恒亼鐠愩儻绱濈拋鏉跨秿閿欒
        logger.error(f"{file_name} - chunks-{params_clone['chunk']} - Upload failed after {max_retries} attempts.")
        return None

    def queue_reader_generator(self, simple_queue: queue.SimpleQueue, chunk_size: int, max_size: int):
        """
        娴?simple_queue 娑擃叀顕伴崣鏍ㄦ殶閹诡喖鑻熼幐?chunk_size 澶у皬閸掑棗娼℃禍褍鍤?(yield)
        瑜版捇妲﹂崚妞捐厬鑾峰彇閸?None 閹存牞鈧懏鏆熼幑顔解偓濠氬櫤鏉堟儳鍩?max_size 閸氬函绱濈亸杈╂暏 0x00 鐞涖儵缍堥崚?chunk_size

        :param simple_queue: queue.SimpleQueue 鐎圭偘绶ラ敍灞炬殶閹诡喗绁︽导姘簰婢舵矮閲滈崚鍡楀瘶 (bytes) 閸忋儵妲﹂敍灞炬付閸氬簼浜?None 鐞涖劎銇氱粨鏉?
        :param chunk_size: 濞戝牐鍨傞懓鍛槨濞嗏剝鍏傜憰浣藉箯閸欐牜娈戞暟鎹崸妤€銇囩亸?
        :param max_size: 闂団偓鐟曚焦娓剁紒鍫Ｋ夋鎰畱閹銇囩亸蹇ョ礄鍗曚綅閿涙艾鐡ч懞鍌︾礆閿涘苯绻€妞ょ粯妲?chunk_size 閻ㄥ嫭鏆ｉ弫鏉库偓?
        :return: 閻㈢喐鍨氶崳顭掔礉閹?chunk_size 澶у皬閸掑棙澹掑▎鈥查獓閸戠儤鏆熼幑?
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
                # 鏁版嵁濞翠胶绮ㄩ弶鐕傜礉閻?x00婵夘偄鍘栭崜鈺€缍戦惃鍕健
                remaining_chunks = total_chunks - chunks_yielded
                if remaining_chunks == total_chunks:
                    # print("缁屽搫瀵樿烦杩?)
                    break
                if len(current_buffer) > 0:
                    # 澶勭悊瑜版挸澧犵紓鎾冲暱閸栬桨鑵戦惃鍕付閸氬簼绔撮崸妤佹殶閹?
                    padding_size = chunk_size - len(current_buffer)
                    if padding_size > 0:
                        current_buffer += b'\x00' * padding_size
                        logger.info(f"閺堚偓閸氬簼绔存稉顏勫瘶瀹割喕绨?{padding_size} 娑擃亜鐡ч懞?)
                    yield bytes(current_buffer)
                    chunks_yielded += 1
                    remaining_chunks -= 1
                break
                logger.info(f"鏉╂ê妯?{remaining_chunks} 娑擃亜鐣弫鏉戝瘶")

                # 鏉堟挸鍤崜鈺€缍戦惃鍕弿0閸?
                for _ in range(remaining_chunks):
                    yield b'\x00' * chunk_size
                    chunks_yielded += 1
                break

            save_file and save_file.write(data)

            # 鐏忓棙鏌婃暟鎹ǎ璇插閸掓壆绱﹂崘鎻掑隘
            current_buffer.extend(data)

            # 鏉堟挸鍤€瑰本鏆ｉ惃鍕健
            while len(current_buffer) >= chunk_size and chunks_yielded < total_chunks:
                yield bytes(current_buffer[:chunk_size])
                current_buffer = current_buffer[chunk_size:]
                chunks_yielded += 1

        # print("閺堫剚顔岄崚鍞掑畬鎴?)
        save_file and save_file.close()
        yield None

    def submit(self, submit_api=None, edit=False, vdeos=None):

        # 娑撳秷鍏橀幓鎰唉 extra_fields 鐎涙顔岄敍灞惧絹閸撳秴顦╅悶?
        post_data = asdict(vdeos)
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
            logger.info(f'閹恒劍绁撮惃鍕暏閹撮攱娼堥柌? {user_weight}')
            # submit_api = 'web' if user_weight == 2 else 'client'
            # web 閻╊喖澧犻敍?025-01-26閿涘鍙忛柌蹇撳瀻p鍔熻兘
            submit_api = 'web'
        ret = None
        if submit_api == 'web':
            ret = self.submit_web(post_data, edit=edit)
            if ret["code"] == 21138:
                time.sleep(5)
                logger.info(f'閺€鍦暏瀹㈡埛缁旑垱甯撮崣锝嗗絹娴滎槨ret}')
                submit_api = 'client'
        if submit_api == 'client':
            ret = self.submit_client(post_data, edit=edit)
        if not ret:
            raise Exception(f'娑撳秴鐡ㄩ崷銊ф畱闁銆嶉敍姝縮ubmit_api}')
        if ret["code"] == 0:
            return ret
        else:
            raise Exception(ret)

    def submit_web(self, post_data, edit=False):
        logger.info('浣跨敤缃戦〉缁旂棏pi閹绘劒姘?)
        if not self.__bili_jct:
            raise RuntimeError("bili_jct is required!")
        api = 'https://member.bilibili.com/x/vu/web/add?csrf=' + self.__bili_jct
        if edit:
            api = 'https://member.bilibili.com/x/vu/web/edit?csrf=' + self.__bili_jct
        return self.__session.post(api, timeout=5,
                                   json=post_data).json()

    def submit_client(self, post_data, edit=False):
        logger.info('浣跨敤瀹㈡埛缁旂棏pi缁旑垱褰佹禍?)
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
                logger.info(f'閸掗攱鏌妕oken{ret}')
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
            # 鐎硅棄鎷版?闂団偓鐟?6閿?0
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

    def get_tags(self, upvdeo, typed="", desc="", cover="", groupd=1, vfea=""):
        """
        涓婁紶鐟欏棝顣堕崥搴ゅ箯瀵版甯归懡鎰垼缁?
        :param vfea:
        :param groupd:
        :param typed:
        :param desc:
        :param cover:
        :param upvdeo:
        :return: 杩斿洖鐎规ɑ鏌熼幒銊ㄥ礃閻ㄥ墖ag
        """
        url = f'https://member.bilibili.com/x/web/archive/tags?'
        f'typed={typed}&title={quote(upvdeo["title"])}&filename=filename&desc={desc}&cover={cover}'
        f'&groupd={groupd}&vfea={vfea}'
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
    cover: 鐣岄潰閸ュ墽澧栭敍灞藉讲閻㈢湕ecovers閺傝纭跺妤€鍩岀憴鍡涱暥閻ㄥ嫬鎶氶幋顏勬禈
    """
    copyright: int = 2
    source: str = ''
    td: int = 21
    cover: str = ''
    title: str = ''
    desc_format_d: int = 0
    desc: str = ''
    desc_v2: list = field(default_factory=list)
    dynamic: str = ''
    subtitle: dict = field(init=False)
    tag: Union[list, str] = ''
    vdeos: list = field(default_factory=list)
    dtime: Any = None
    open_subtitle: InitVar[bool] = False
    dolby: int = 0
    hires: int = 0
    no_reprint: int = 0
    is_only_self: int = 0
    charging_pay: int = 0
    extra_fields: str = ""

    ad: int = None
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
        """璁剧疆瀵よ埖妞傞崣鎴濈鏃堕棿閿涘矁绐涚粋缁樺絹娴溿倕銇囨禍?鐏忓繑妞傞敍灞剧壐瀵繋璐?0娴ｅ秵妞傞梻瀛樺煈"""
        if dtime - int(time.time()) > 7200:
            self.dtime = dtime

    def set_tag(self, tag: list):
        """璁剧疆閺嶅洨顒烽敍瀹糰g娑撶儤鏆熺紒?""
        self.tag = ','.join(tag)

    def append(self, vdeo):
        self.vdeos.append(vdeo)
