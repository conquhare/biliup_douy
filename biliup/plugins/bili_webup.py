锘縤mport asyncio
import base64
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.parse
from dataclasses import asdict, dataclass, field, InitVar
from json import JSONDecodeError
from os.path import splitext, basename
from typing import Union, Any, List, Optional, Callable
from urllib import parse
from urllib.parse import quote

import aiohttp
import requests.utils
import rsa
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter, Retry

from ..engine import Plugin
from ..engine.upload import UploadBase, logger


@Plugin.upload(platform="bili_web")
class BiliWeb(UploadBase):
    def __init__(
        self,
        principal,
        data,
        user,
        user_cookie='cookies.json',
        submit_api: Optional[str] = 'web',
        copyright: int = 2,
        postprocessor: Optional[Callable] = None,
        dtime: Optional[int] = None,
        dynamic='',
        lines: Optional[str] = 'AUTO',
        threads: int = 3,
        td: int = 122,
        tags: Optional[List[str]] = None,
        cover_path=None,
        description='',
        credits=[],
    ):
        """
        :param principal:
        :param data:
        :param user_cookie: 閹舵洜顭堢敤鎴穋ookie鏂囦欢
        :param submit_api:
        :param copyright:
        :param postprocessor:
        :param dtime: 瀵よ埖妞傞崣鎴濈鏃堕棿閵嗗倿娓剁捄婵堫瀲閹绘劒姘︽径褌绨?鐏忓繑妞傞敍灞剧壐瀵繋璐?0娴ｅ秵妞傞梻瀛樺煈
        :param dynamic:
        :param lines: 涓婁紶缁捐儻鐭?
        :param threads: 涓婁紶缁捐法鈻奸弫?
        :param td: 缁嬪じ娆㈤崚鍡楀隘
        :param tags: 缁嬪じ娆㈤弽鍥╊劮
        :param cover_path: 缁嬪じ娆㈢晫闈㈢捄顖氱窞
        :param description: 鐟欏棝顣剁粻鈧禒?
        :param credits: ???
        """
        super().__init__(principal, data, persistence_path='bili.cookie', postprocessor=postprocessor)
        if tags is None:
            tags = []
        else:
            tags = [str(tag).format(streamer=self.data['name']) for tag in tags]
        self.user = user # 閺冄呭閺堫剛娈戦惂璇茬秿鐢ㄦ埛
        self.user_cookie = user_cookie # 閺傛壆澧楅張顒傛畱閻ц缍嶇敤鎴穋ookie鏂囦欢
        self.lines = lines
        self.submit_api = submit_api or 'web'
        self.threads = threads
        self.td = td
        self.tags = tags
        self.cover_path = cover_path
        self.desc = description
        self.credits = credits
        self.dynamic = dynamic
        self.copyright = copyright
        self.dtime = dtime

    def upload(
        self,
        file_list: List[UploadBase.FileInfo],
        database_row_d: int = 0
    ) -> List[UploadBase.FileInfo]:
        '''
        涓婁紶鐟欏棝顣?
        :param file_list: 鐟欏棝顣舵枃浠堕崥宥呭灙鐞?
        :param database_row_d: 鏁版嵁鎼存捁顢慖D
        :return: 涓婁紶缁撴灉
        '''
        logger.info(f"瀵偓婵绗傛导鐘侯潒妫?{database_row_d}")
        vdeo = Data()
        vdeo.dynamic = self.dynamic
        with BiliBili(vdeo) as bili:
            bili.app_key = self.user.get('app_key')
            bili.appsec = self.user.get('appsec')
            bili.login(self.persistence_path, self.user_cookie)
            for file in file_list:
                vdeo_part = bili.upload_file(file.vdeo, self.lines, self.threads)  # 涓婁紶鐟欏棝顣?
                vdeo_part['title'] = vdeo_part['title'][:80]
                vdeo.append(vdeo_part)  # 濞ｈ濮炲鑼病涓婁紶閻ㄥ嫯顫嬫０?
            vdeo.title = self.data["format_title"][:80]  # 缁嬪じ娆㈤弽鍥暯闄愬埗80鐎?
            if self.credits:
                vdeo.desc_v2 = self.creditsToDesc_v2()
            else:
                vdeo.desc_v2=[{
                    "raw_text": self.desc,
                    "biz_d": "",
                    "type": 1
                }]
            vdeo.desc = self.desc
            vdeo.copyright = self.copyright
            if self.copyright == 2:
                vdeo.source = self.data["url"]  # 濞ｈ濮炴潪顒冩祰閸︽澘娼冭鏄?
            # 璁剧疆鐟欏棝顣堕崚鍡楀隘,姒涙顓绘稉?74 閻㈢喐妞块敍灞藉従娴犳牕鍨庨崠?
            vdeo.td = self.td
            vdeo.set_tag(self.tags)
            if self.dtime:
                vdeo.delay_time(int(time.time()) + self.dtime)
            if self.cover_path:
                vdeo.cover = bili.cover_up(self.cover_path).replace('http:', '')
            ret = bili.submit(self.submit_api)  # 閹绘劒姘︾憴鍡涱暥
        logger.info(f"涓婁紶鎴愬姛: {ret}")
        return file_list

    def creditsToDesc_v2(self):
            desc_v2 = []
            desc_v2_tmp = self.desc
            for credit in self.credits:
                try :
                    num = desc_v2_tmp.index("@credit")
                    desc_v2.append({
                        "raw_text": " "+desc_v2_tmp[:num],
                        "biz_d": "",
                        "type": 1
                    })
                    desc_v2.append({
                        "raw_text": credit["username"],
                        "biz_d": str(credit["ud"]),
                        "type": 2
                    })
                    self.desc = self.desc.replace(
                        "@credit", "@"+credit["username"]+"  ", 1)
                    desc_v2_tmp = desc_v2_tmp[num+7:]
                except IndexError:
                    logger.error('缁犫偓娴犲鑵戦惃鍑榗redit閸楃姳缍呯粭锕€鐨禍宸唕edits閻ㄥ嫭鏆熼柌?鏇挎崲澶辫触')
            desc_v2.append({
                "raw_text": " "+desc_v2_tmp,
                "biz_d": "",
                "type": 1
            })
            desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 瀵偓婢跺鈹栭弽闂寸窗鐎佃壈鍤х拠鍡楀焼缁犫偓娴犲绻冮梹?
            return desc_v2

class BiliBili:
    def __init__(self, vdeo: 'Data'):
        self.app_key = None
        self.appsec = None
        if self.app_key is None or self.appsec is None:
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

    def check_tag(self, tag):
        r = self.__session.get("https://member.bilibili.com/x/vupre/web/topic/tag/check?tag=" + tag).json()
        if r["code"] == 0:
            return True
        else:
            return False

    def get_qrcode(self):
        params = {
            "appkey": "4409e2ce8ffd12b8",
            "local_d": "0",
            "ts": int(time.time()),
        }
        params["sign"] = hashlib.md5(
            f"{urllib.parse.urlencode(params)}59b43e04ad6965f34319062b478f83dd".encode()).hexdigest()
        response = self.__session.post("http://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code", data=params,
                                       timeout=5)
        r = response.json()
        if r and r["code"] == 0:
            return r

    async def login_by_qrcode(self, value):
        params = {
            "appkey": "4409e2ce8ffd12b8",
            "auth_code": value["data"]["auth_code"],
            "local_d": "0",
            "ts": int(time.time()),
        }
        params["sign"] = hashlib.md5(
            f"{urllib.parse.urlencode(params)}59b43e04ad6965f34319062b478f83dd".encode()).hexdigest()
        for i in range(0, 120):
            await asyncio.sleep(1)
            response = self.__session.post("http://passport.bilibili.com/x/passport-tv-login/qrcode/poll", data=params,
                                           timeout=5)
            r = response.json()
            if r and r["code"] == 0:
                return r
        raise "Qrcode timeout"

    def td_archive(self, cookies):
        requests.utils.add_dict_to_cookiejar(self.__session.cookies, cookies)
        response = self.__session.get("https://member.bilibili.com/x/vupre/web/archive/pre")
        return response.json()

    def myinfo(self, cookies):
        requests.utils.add_dict_to_cookiejar(self.__session.cookies, cookies)
        response = self.__session.get('http://api.bilibili.com/x/space/myinfo')
        return response.json()

    def login(self, persistence_path, user_cookie):
        self.persistence_path = user_cookie
        if os.path.isfile(self.persistence_path):
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

    def send_sms(self, phone_number, country_code):
        params = {
            "actionKey": "appkey",
            "appkey": "783bbb7264451d82",
            "build": 6510400,
            "channel": "bili",
            "cd": country_code,
            "device": "phone",
            "mobi_app": "androd",
            "platform": "androd",
            "tel": phone_number,
            "ts": int(time.time()),
        }
        sign = hashlib.md5(f"{urllib.parse.urlencode(params)}2653583c8873dea268ab9386918b1d65".encode()).hexdigest()
        payload = f"{urllib.parse.urlencode(params)}&sign={sign}"
        response = self.__session.post("https://passport.bilibili.com/x/passport-login/sms/send", data=payload,
                                       timeout=5)
        return response.json()

    def login_by_sms(self, code, params):
        params["code"] = code
        params["sign"] = hashlib.md5(
            f"{urllib.parse.urlencode(params)}59b43e04ad6965f34319062b478f83dd".encode()).hexdigest()
        response = self.__session.post("https://passport.bilibili.com/x/passport-login/login/sms", data=params,
                                       timeout=5)
        r = response.json()
        if r and r["code"] == 0:
            return r

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
        logger.info(f'{self.__class__.__name__}: login by cookies')
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

    def upload_file(self, filepath: str, lines='AUTO', tasks=3):
        """涓婁紶閺堫剙婀寸憴鍡涱暥鏂囦欢,杩斿洖鐟欏棝顣朵俊鎭痙ict
        b缁旀瑧娲伴崜宥嗘暜閹?缁夊秳绗傛导鐘靛殠鐠虹椃pos, kodo, gcs, bos
        gcs: {"os":"gcs","query":"bucket=bvcupcdngcsus&probe_version=20221109",
        "probe_url":"//storage.googleapis.com/bvcupcdngcsus/OK"},
        bos: {"os":"bos","query":"bucket=bvcupcdnboshb&probe_version=20221109",
        "probe_url":"??"}
        """
        preferred_upos_cdn = None
        if not self._auto_os:
            if lines == 'bda':
                self._auto_os = {"os": "upos", "query": "upcdn=bda&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdnbda.bilivdeo.com/OK"}
                preferred_upos_cdn = 'bda'
            elif lines in {'bda2', 'cs-bda2'}:
                self._auto_os = {"os": "upos", "query": "upcdn=bda2&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdnbda2.bilivdeo.com/OK"}
                preferred_upos_cdn = 'bda2'
            elif lines == 'ws':
                self._auto_os = {"os": "upos", "query": "upcdn=ws&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdnws.bilivdeo.com/OK"}
                preferred_upos_cdn = 'ws'
            elif lines in {'qn', 'cs-qn'}:
                self._auto_os = {"os": "upos", "query": "upcdn=qn&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdnqn.bilivdeo.com/OK"}
                preferred_upos_cdn = 'qn'
            elif lines == 'bldsa':
                self._auto_os = {"os": "upos", "query": "upcdn=bldsa&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdnbldsa.bilivdeo.com/OK"}
                preferred_upos_cdn = 'bldsa'
            elif lines == 'tx':
                self._auto_os = {"os": "upos", "query": "upcdn=tx&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdntx.bilivdeo.com/OK"}
                preferred_upos_cdn = 'tx'
            elif lines == 'txa':
                self._auto_os = {"os": "upos", "query": "upcdn=txa&probe_version=20221109",
                                 "probe_url": "//upos-cs-upcdntxa.bilivdeo.com/OK"}
                preferred_upos_cdn = 'txa'
            else:
                self._auto_os = self.probe()
            logger.info(f"缁捐儻鐭鹃€夋嫨 => {self._auto_os['os']}: {self._auto_os['query']}. time: {self._auto_os.get('cost')}")
        if self._auto_os['os'] == 'upos':
            upload = self.upos
        # elif self._auto_os['os'] == 'cos':
        #     upload = self.cos
        # elif self._auto_os['os'] == 'cos-internal':
        #     upload = lambda *args, **kwargs: self.cos(*args, **kwargs, internal=True)
        # elif self._auto_os['os'] == 'kodo':
        #     upload = self.kodo
        else:
            logger.error(f"NoSearch:{self._auto_os['os']}")
            raise NotImplementedError(self._auto_os['os'])
        logger.info(f"os: {self._auto_os['os']}")
        total_size = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            query = {
                'r': self._auto_os['os'] if self._auto_os['os'] != 'cos-internal' else 'cos',
                'profile': 'ugcupos/bup' if 'upos' == self._auto_os['os'] else "ugcupos/bupfetch",
                'ssl': 0,
                'version': '2.8.12',
                'build': 2081200,
                'name': f.name,
                'size': total_size,
            }
            resp = self.__session.get(
                f"https://member.bilibili.com/preupload?{self._auto_os['query']}", params=query,
                timeout=5)
            ret = resp.json()
            logger.debug(f"preupload: {ret}")
            if preferred_upos_cdn:
                original_endpoint: str = ret['endpoint']
                if re.match(r'//upos-(sz|cs)-upcdn(bda2|ws|qn)\.bilivdeo\.com', original_endpoint):
                    if re.match(r'bda2|qn|ws', preferred_upos_cdn):
                        logger.debug(f"Preferred UpOS CDN: {preferred_upos_cdn}")
                        new_endpoint = re.sub(r'upcdn(bda2|qn|ws)', f'upcdn{preferred_upos_cdn}', original_endpoint)
                        logger.debug(f"{original_endpoint} => {new_endpoint}")
                        ret['endpoint'] = new_endpoint
                    else:
                        logger.error(f"Unrecognized preferred_upos_cdn: {preferred_upos_cdn}")
                else:
                    logger.warning(f"Assigned UpOS endpoint {original_endpoint} was never seen before, something else might have changed, so will not modify it")
            return asyncio.run(upload(f, total_size, ret, tasks=tasks))

    async def cos(self, file, total_size, ret, chunk_size=10485760, tasks=3, internal=False):
        filename = file.name
        url = ret["url"]
        if internal:
            url = url.replace("cos.accelerate", "cos-internal.ap-shanghai")
        biz_d = ret["biz_d"]
        post_headers = {
            "Authorization": ret["post_auth"],
        }
        put_headers = {
            "Authorization": ret["put_auth"],
        }

        initiate_multipart_upload_result = ET.fromstring(self.__session.post(f'{url}?uploads&output=json', timeout=5,
                                                                             headers=post_headers).content)
        upload_d = initiate_multipart_upload_result.find('UploadId').text
        # 瀵偓婵绗傛导?
        parts = []  # 閸掑棗娼′俊鎭?
        chunks = math.ceil(total_size / chunk_size)  # 鑾峰彇閸掑棗娼℃暟閲?

        async def upload_chunk(session, chunks_data, params):
            async with session.put(url, params=params, raise_for_status=True,
                                   data=chunks_data, headers=put_headers) as r:
                end = time.perf_counter() - start
                parts.append({"Part": {"PartNumber": params['chunk'] + 1, "ETag": r.headers['Etag']}})
                sys.stdout.write(f"\r{params['end'] / 1000 / 1000 / end:.2f}MB/s "
                                 f"=> {params['partNumber'] / chunks:.1%}")

        start = time.perf_counter()
        await self._upload({
            'uploadId': upload_d,
            'chunks': chunks,
            'total': total_size
        }, file, chunk_size, upload_chunk, tasks=tasks)
        cost = time.perf_counter() - start
        fetch_headers = {
            "X-Upos-Fetch-Source": ret["fetch_headers"]["X-Upos-Fetch-Source"],
            "X-Upos-Auth": ret["fetch_headers"]["X-Upos-Auth"],
            "Fetch-Header-Authorization": ret["fetch_headers"]["Fetch-Header-Authorization"]
        }
        parts = sorted(parts, key=lambda x: x['Part']['PartNumber'])
        complete_multipart_upload = ET.Element('CompleteMultipartUpload')
        for part in parts:
            part_et = ET.SubElement(complete_multipart_upload, 'Part')
            part_number = ET.SubElement(part_et, 'PartNumber')
            part_number.text = str(part['Part']['PartNumber'])
            e_tag = ET.SubElement(part_et, 'ETag')
            e_tag.text = part['Part']['ETag']
        xml = ET.tostring(complete_multipart_upload)
        ii = 0
        while ii <= 3:
            try:
                res = self.__session.post(url, params={'uploadId': upload_d}, data=xml, headers=post_headers,
                                          timeout=15)
                if res.status_code == 200:
                    break
                raise IOError(res.text)
            except IOError:
                ii += 1
                logger.info("璇锋眰鍚堝苟鍒嗙墖鍑虹幇闂閿涘苯鐨剧拠鏇㈠櫢鏉╃儑绱濇鏁伴敍? + str(ii))
                time.sleep(15)
        ii = 0
        while ii <= 3:
            try:
                res = self.__session.post("https:" + ret["fetch_url"], headers=fetch_headers, timeout=15).json()
                if res.get('OK') == 1:
                    logger.info(f'{filename} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {res}')
                    return {"title": splitext(os.path.basename(filename))[0], "filename": ret["bili_filename"], "desc": ""}
                raise IOError(res)
            except IOError:
                ii += 1
                logger.info("涓婁紶鍑虹幇闂閿涘苯鐨剧拠鏇㈠櫢鏉╃儑绱濇鏁伴敍? + str(ii))
                time.sleep(15)

    async def kodo(self, file, total_size, ret, chunk_size=4194304, tasks=3):
        filename = file.name
        bili_filename = ret['bili_filename']
        key = ret['key']
        endpoint = f"https:{ret['endpoint']}"
        token = ret['uptoken']
        fetch_url = ret['fetch_url']
        fetch_headers = ret['fetch_headers']
        url = f'{endpoint}/mkblk'
        headers = {
            'Authorization': f"UpToken {token}",
        }
        # 瀵偓婵绗傛导?
        parts = []  # 閸掑棗娼′俊鎭?
        chunks = math.ceil(total_size / chunk_size)  # 鑾峰彇閸掑棗娼℃暟閲?

        async def upload_chunk(session, chunks_data, params):
            async with session.post(f'{url}/{len(chunks_data)}',
                                    data=chunks_data, headers=headers) as response:
                end = time.perf_counter() - start
                ctx = await response.json()
                parts.append({"index": params['chunk'], "ctx": ctx['ctx']})
                sys.stdout.write(f"\r{params['end'] / 1000 / 1000 / end:.2f}MB/s "
                                 f"=> {params['partNumber'] / chunks:.1%}")

        start = time.perf_counter()
        await self._upload({}, file, chunk_size, upload_chunk, tasks=tasks)
        cost = time.perf_counter() - start

        logger.info(f'{filename} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s')
        parts.sort(key=lambda x: x['index'])
        self.__session.post(f"{endpoint}/mkfile/{total_size}/key/{base64.urlsafe_b64encode(key.encode()).decode()}",
                            data=','.join(map(lambda x: x['ctx'], parts)), headers=headers, timeout=10)
        r = self.__session.post(f"https:{fetch_url}", headers=fetch_headers, timeout=5).json()
        if r["OK"] != 1:
            raise Exception(r)
        return {"title": splitext(os.path.basename(filename))[0], "filename": bili_filename, "desc": ""}

    async def upos(self, file, total_size, ret, tasks=3):
        filename = file.name
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

        async def upload_chunk(session, chunks_data, params):
            async with session.put(url, params=params, raise_for_status=True,
                                   data=chunks_data, headers=headers):
                end = time.perf_counter() - start
                parts.append({"partNumber": params['chunk'] + 1, "eTag": "etag"})
                sys.stdout.write(f"\r{params['end'] / 1000 / 1000 / end:.2f}MB/s "
                                 f"=> {params['partNumber'] / chunks:.1%}")

        start = time.perf_counter()
        await self._upload({
            'uploadId': upload_d,
            'chunks': chunks,
            'total': total_size
        }, file, chunk_size, upload_chunk, tasks=tasks)
        cost = time.perf_counter() - start
        p = {
            'name': filename,
            'uploadId': upload_d,
            'biz_d': biz_d,
            'output': 'json',
            'profile': 'ugcupos/bup'
        }
        attempt = 0
        while attempt <= 5:  # 娑撯偓閺冿附鏂佸鍐ㄦ皑娴兼矮娑径鍗炲闂堛垺澧嶉張澶屾畱鏉╂稑瀹抽敍灞筋樋鐠囨洖鍤戝▎鈥冲惂
            try:
                r = self.__session.post(url, params=p, json={"parts": parts}, headers=headers, timeout=15).json()
                if r.get('OK') == 1:
                    logger.info(f'{filename} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {r}')
                    return {"title": splitext(os.path.basename(filename))[0], "filename": splitext(basename(upos_uri))[0], "desc": ""}
                raise IOError(r)
            except IOError:
                attempt += 1
                logger.info(f"璇锋眰鍚堝苟鍒嗙墖閺冭泛鍤悳浼存６妫版﹫绱濆皾璇曢柌宥堢箾閿涘本顐奸弫甯窗" + str(attempt))
                time.sleep(15)

    @staticmethod
    async def _upload(params, file, chunk_size, afunc, tasks=3):
        params['chunk'] = -1

        async def upload_chunk():
            while True:
                chunks_data = file.read(chunk_size)
                if not chunks_data:
                    return
                params['chunk'] += 1
                params['size'] = len(chunks_data)
                params['partNumber'] = params['chunk'] + 1
                params['start'] = params['chunk'] * chunk_size
                params['end'] = params['start'] + params['size']
                clone = params.copy()
                for i in range(10):
                    try:
                        await afunc(session, chunks_data, clone)
                        break
                    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                        logger.error(f"retry chunk{clone['chunk']} >> {i + 1}. {e}")

        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[upload_chunk() for _ in range(tasks)])

    def submit(self, submit_api: Optional[str] = 'web'):
        if not self.vdeo.title:
            self.vdeo.title = self.vdeo.vdeos[0]["title"]
        self.__session.get('https://member.bilibili.com/x/geetest/pre/add', timeout=5)

        if submit_api is None:
            total_info = self.__session.get('http://api.bilibili.com/x/space/myinfo', timeout=15).json()
            if total_info.get('data') is None:
                logger.error(total_info)
            total_info = total_info.get('data')
            if total_info['level'] > 3 and total_info['follower'] > 1000:
                user_weight = 2
            else:
                user_weight = 1
            logger.info(f'鐢ㄦ埛閺夊啴鍣? {user_weight}')
            submit_api = 'web'
        ret = None
        if submit_api == 'web':
            ret = self.submit_web()
            if ret["code"] != 0:
                logger.error(f'缃戦〉缁旑垱甯撮崣锝嗗絹娴溿倕銇戠拹? {ret}')
                raise Exception(ret)
        if not ret:
            raise Exception(f'娑撳秴鐡ㄩ崷銊ф畱闁銆嶉敍姝縮ubmit_api}')
        return ret

    def submit_web(self):
        logger.info('浣跨敤缃戦〉缁旂棏pi閹绘劒姘?)
        return self.__session.post(f'https://member.bilibili.com/x/vu/web/add?csrf={self.__bili_jct}', timeout=5,
                                   json=asdict(self.vdeo)).json()

    def submit_client(self):
        logger.info('浣跨敤瀹㈡埛缁旂棏pi缁旑垱褰佹禍?)
        if not self.access_token:
            if self.account is None:
                raise RuntimeError("Access token is required, but account and access_token does not exist!")
            self.login_by_password(**self.account)
            self.store()
        while True:
            ret = self.__session.post(f'http://member.bilibili.com/x/vu/client/add?access_key={self.access_token}',
                                      timeout=5, json=asdict(self.vdeo)).json()
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
        url = f'https://member.bilibili.com/x/web/archive/tags?' \
              f'typed={typed}&title={quote(upvdeo["title"])}&filename=filename&desc={desc}&cover={cover}' \
              f'&groupd={groupd}&vfea={vfea}'
        return self.__session.get(url=url, timeout=5).json()

    # ==================== 閸氬牓娉﹂敍鍦獷ASON閿涘顓搁悶?====================
    #
    # B缁?閺傛壆澧楅崥鍫ユ肠"閿涘湯EASON 绫诲瀷閿涘娈戠粻锛勬倞閹恒儱褰涢敍灞炬暜閹镐緤绱?
    #   - 閸掓鍤敤鎴烽惃鍕閺堝鎮庨梿?
    #   - 鏌ョ湅閸氬牓娉﹂崘鍛畱鐟欏棝顣跺垪琛?
    #   - 鐏忓棜顫嬫０鎴炲潑閸旂姴鍩岄崥鍫ユ肠
    #   - 娴犲骸鎮庨梿鍡曡厬缁夊娅庣憴鍡涱暥
    #   - 鐎电懓鎮庨梿鍡楀敶鐟欏棝顣堕噸鏂伴幒鎺戠碍
    #
    # 閺嶇绺惧鍌氬悍閿?
    #   season_d  - 閸氬牓娉D閿涘奔绮犻崚娑楃稊娑擃厼绺鹃崥鍫ユ肠缁狅紕鎮婃い鐢告桨閻ㄥ垊RL閹?list_seasons() 鑾峰彇
    #   section_d - 閸氬牓娉︽稉瀣畱"閸掑棗灏?ID閿涘本鐦℃稉顏勬値闂嗗棜鍤︾亸鎴炴湁娑撯偓娑擃亪绮拋銈呭瀻閸栫尨绱?
    #                闁俺绻?list_seasons() 杩斿洖閻?sections.sections[0].d 鑾峰彇
    #   episode_d - 鐟欏棝顣堕崷銊ユ値闂嗗棔鑵戦惃鍕敶闁問D閿涘牅绗夐弰?ad閿涘绱?
    #                闁俺绻?get_season_section() 杩斿洖閻?episodes[i]['d'] 鑾峰彇
    #
    # 閸忕鐎峰ù浣衡柤閿涘牅绗傛导鐘叉倵濞ｈ濮為崚鏉挎値闂嗗棴绱氶敍?
    #   1. seasons = bili.list_seasons()  # 鑾峰彇閸氬牓娉﹀垪琛ㄩ敍灞惧閸?season_d 閸?section_d
    #   2. info = bili.get_vdeo_info(ad)  # 鑾峰彇鐟欏棝顣堕惃?cd 閸?title
    #   3. bili.add_to_season(section_d, [{...}])  # 濞ｈ濮為崚鏉挎値闂?
    def list_seasons(self, pn=1, ps=30):
        """
        鑾峰彇鐢ㄦ埛閻ㄥ嫬鎮庨梿鍡楀灙鐞?

        杩斿洖閸婅偐銇氭笟?:

            {
                'seasons': [{
                    'season': {'d': 7320255, 'title': '閹存垹娈戦崥鍫ユ肠', ...},
                    'sections': {'sections': [{'d': 8081933, 'title': '濮濓絿澧?, ...}]}
                }, ...],
                'page': {'pn': 1, 'ps': 30, 'total': 5}
            }

        鑾峰彇 section_d 閻ㄥ嫭鏌熷蹇ョ窗
        ``data['seasons'][0]['sections']['sections'][0]['d']``

        :param pn: 妞ょ數鐖滈敍灞肩矤1瀵偓婵?
        :param ps: 濮ｅ繘銆夋暟閲忛敍宀勭帛鐠?0
        :return: 閸栧懎鎯?seasons 鍒楄〃閸滃苯鍨庢い鍏镐繆閹垳娈?dict
        """
        r = self.__session.get(
            'https://member.bilibili.com/x2/creative/web/seasons',
            params={'pn': pn, 'ps': ps, 'order': 'mtime', 'sort': 'desc', 'draft': 1},
            timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r['data']

    def get_season_section(self, section_d, sort=''):
        """
        鑾峰彇閸氬牓娉﹂崚鍡楀隘閸愬懐娈戠憴鍡涱暥鍒楄〃

        杩斿洖閸婇棿鑵戝В蹇庨嚋 episode 閸栧懎鎯?:

            {'d': 176218279, 'ad': 12345, 'cd': 67890, 'title': '...', ...}

        閸忔湹鑵?``d`` 閺?episode_d閿涘牆鎮庨梿鍡楀敶闁問D閿涘绱濋悽銊ょ艾 remove_from_season 閸滃本甯撴惔蹇嬧偓?

        :param section_d: 閸掑棗灏疘D閿涘矂鈧俺绻?list_seasons() 鑾峰彇
        :param sort: 閹烘帒绨弬鐟扮础閿涘苯褰查柅?'desc'閿涘牓妾锋惔蹇ョ礆
        :return: 閸栧懎鎯?section 淇℃伅閸?episodes 鍒楄〃閻?dict
        """
        params = {'d': section_d}
        if sort:
            params['sort'] = sort
        r = self.__session.get(
            'https://member.bilibili.com/x2/creative/web/season/section',
            params=params, timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r['data']

    def get_vdeo_info(self, ad):
        """
        鑾峰彇鐟欏棝顣朵俊鎭敍鍫熺垼妫版ǜ鈧恭d 缁涘绱氶敍宀€鏁ゆ禍搴㈠潑閸旂姴鍩岄崥鍫ユ肠閸撳秷骞忛崣鏍х箑鐟曚礁寮弫?

        :param ad: 鐟欏棝顣禔V閸欏嚖绱欓弫瀛樻殶閿?
        :return: 鐟欏棝顣朵俊鎭?dict閿涘苯瀵橀崥?title, pages[0].cd 缁?
        """
        r = self.__session.get(
            'https://api.bilibili.com/x/web-interface/view',
            params={'ad': ad}, timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r['data']

    def add_to_season(self, section_d, episodes):
        """
        鐏忓棜顫嬫０鎴炲潑閸旂姴鍩岄崥鍫ユ肠閿涘牊鏌婇悧鍫濇値闂?SEASON閿?

        濞ｈ濮為崡鏇氶嚋鐟欏棝顣堕惃鍕悁閸ㄥ鏁ゅ▔?:

            info = bili.get_vdeo_info(ad)
            bili.add_to_season(section_d, [{
                'ad': ad,
                'cd': info['pages'][0]['cd'],
                'title': info['title'],
                'charging_pay': 0,
            }])

        閸欘垯绔村▎鈩冨潑閸旂姴顦挎稉顏囶潒妫版埊绱欐导鐘插弳婢舵矮閲?episode dict閿涘鈧?

        :param section_d: 閸掑棗灏疘D閿涘矂鈧俺绻?list_seasons() 鑾峰彇
        :param episodes: 鐟欏棝顣跺垪琛ㄩ敍灞剧槨妞ゅ綊銆忛崥?ad, cd, title, charging_pay
        :return: API 杩斿洖閻?JSON
        :raises Exception: API 杩斿洖 code != 0 閺冭埖濮忛崙?
        """
        r = self.__session.post(
            f'https://member.bilibili.com/x2/creative/web/season/section/episodes/add'
            f'?csrf={self.__bili_jct}',
            json={
                'sectionId': section_d,
                'episodes': episodes,
                'csrf': self.__bili_jct,
            },
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r

    def remove_from_season(self, episode_d):
        """
        娴犲骸鎮庨梿鍡曡厬缁夊娅庢稉鈧稉顏囶潒妫?

        濞夈劍鍓伴敍姘棘閺佺増妲?episode_d閿涘牆鎮庨梿鍡楀敶闁問D閿涘绱濇稉宥嗘Ц ad閵?
        闂団偓鐟曚礁鍘涢柅姘崇箖 get_season_section() 鑾峰彇 episodes 鍒楄〃閿?
        閹垫儳鍩岀洰鏍囩憴鍡涱暥閻?``episode['d']`` 鐎涙顔岄妴?

        濮ｅ繑顐奸崣顏囧厴缁夊娅庢稉鈧稉顏囶潒妫版埊绱濋幍褰掑櫤缁夊娅庨棁鈧憰浣告儕閻滎垵鐨熼悽銊ｂ偓?

        :param episode_d: 閸氬牓娉﹂崘鍛村劥閻?episode ID閿涘牅绗夐弰?ad閿?
        :return: API 杩斿洖閻?JSON
        :raises Exception: API 杩斿洖 code != 0 閺冭埖濮忛崙?
        """
        r = self.__session.post(
            'https://member.bilibili.com/x2/creative/web/season/section/episode/del',
            data={'d': episode_d, 'csrf': self.__bili_jct},
            timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r

    def sort_season_episodes(self, section_d, season_d, sorts, section_title='濮濓絿澧?):
        """
        鐎电懓鎮庨梿鍡楀敶閻ㄥ嫯顫嬫０鎴﹀櫢閺傜増甯撴惔?

        浣跨敤缁€杞扮伐::

            section = bili.get_season_section(section_d)
            eps = section['episodes']
            # 閸欏秷娴嗘い鍝勭碍
            sorts = [{'d': ep['d'], 'sort': i+1} for i, ep in enumerate(reversed(eps))]
            bili.sort_season_episodes(section_d, season_d, sorts)

        濞夈劍鍓版禍瀣€嶉敍?
        - sorts 蹇呴』閸栧懎鎯堥崥鍫ユ肠涓殑**閹碘偓閺?*鐟欏棝顣堕敍灞肩瑝閼宠棄褰ф导鐘诲劥閸?
        - section_d閵嗕够eason_d閵嗕够ection_title 娑撳閲滃弬鏁扮紓杞扮娑撳秴褰查敍灞芥儊閸掓瑨绻戦崶?-400
        - sort 鎼村繐褰挎禒?瀵偓婵?

        :param section_d: 閸掑棗灏疘D
        :param season_d: 閸氬牓娉D
        :param sorts: 閹烘帒绨弫鎵矋閿涘本鐦℃い鐟版儓 d (episode_d) 閸?sort (1-indexed 鎼村繐褰?
        :param section_title: 閸掑棗灏弽鍥暯閿涘矂绮拋?濮濓絿澧?
        :return: API 杩斿洖閻?JSON
        :raises Exception: API 杩斿洖 code != 0 閺冭埖濮忛崙?
        """
        r = self.__session.post(
            f'https://member.bilibili.com/x2/creative/web/season/section/edit'
            f'?csrf={self.__bili_jct}',
            json={
                'section': {
                    'd': section_d,
                    'type': 1,
                    'seasonId': season_d,
                    'title': section_title,
                },
                'sorts': sorts,
                'captcha_token': '',
            },
            headers={'Content-Type': 'application/json'},
            timeout=15
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r

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
    dynamic: str = ''
    subtitle: dict = field(init=False)
    tag: Union[list, str] = ''
    vdeos: list = field(default_factory=list)
    dtime: Any = None
    open_subtitle: InitVar[bool] = False

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
