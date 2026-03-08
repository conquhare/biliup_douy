import asyncio
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
        :param user_cookie: 鎶曠用户cookie文件
        :param submit_api:
        :param copyright:
        :param postprocessor:
        :param dtime: 寤舵椂鍙戝竷时间銆傞渶璺濈鎻愪氦澶т簬4灏忔椂锛屾牸寮忎负10浣嶆椂闂存埑
        :param dynamic:
        :param lines: 上传绾胯矾
        :param threads: 上传绾跨▼鏁?
        :param td: 绋夸欢鍒嗗尯
        :param tags: 绋夸欢鏍囩
        :param cover_path: 绋夸欢界面璺緞
        :param description: 瑙嗛绠€浠?
        :param credits: ???
        """
        super().__init__(principal, data, persistence_path='bili.cookie', postprocessor=postprocessor)
        if tags is None:
            tags = []
        else:
            tags = [str(tag).format(streamer=self.data['name']) for tag in tags]
        self.user = user # 鏃х増鏈殑鐧诲綍用户
        self.user_cookie = user_cookie # 鏂扮増鏈殑鐧诲綍用户cookie文件
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
        上传瑙嗛
        :param file_list: 瑙嗛文件鍚嶅垪琛?
        :param database_row_d: 数据搴撹ID
        :return: 上传结果
        '''
        logger.info(f"寮€濮嬩笂浼犺棰?{database_row_d}")
        vdeo = Data()
        vdeo.dynamic = self.dynamic
        with BiliBili(vdeo) as bili:
            bili.app_key = self.user.get('app_key')
            bili.appsec = self.user.get('appsec')
            bili.login(self.persistence_path, self.user_cookie)
            for file in file_list:
                vdeo_part = bili.upload_file(file.vdeo, self.lines, self.threads)  # 上传瑙嗛
                vdeo_part['title'] = vdeo_part['title'][:80]
                vdeo.append(vdeo_part)  # 娣诲姞宸茬粡上传鐨勮棰?
            vdeo.title = self.data["format_title"][:80]  # 绋夸欢鏍囬限制80瀛?
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
                vdeo.source = self.data["url"]  # 娣诲姞杞浇鍦板潃说明
            # 设置瑙嗛鍒嗗尯,榛樿涓?74 鐢熸椿锛屽叾浠栧垎鍖?
            vdeo.td = self.td
            vdeo.set_tag(self.tags)
            if self.dtime:
                vdeo.delay_time(int(time.time()) + self.dtime)
            if self.cover_path:
                vdeo.cover = bili.cover_up(self.cover_path).replace('http:', '')
            ret = bili.submit(self.submit_api)  # 鎻愪氦瑙嗛
        logger.info(f"上传成功: {ret}")
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
                    logger.error('绠€浠嬩腑鐨凘credit鍗犱綅绗﹀皯浜巆redits鐨勬暟閲?替换失败')
            desc_v2.append({
                "raw_text": " "+desc_v2_tmp,
                "biz_d": "",
                "type": 1
            })
            desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 寮€澶寸┖鏍间細瀵艰嚧璇嗗埆绠€浠嬭繃闀?
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
            print('使用鎸佷箙鍖栧唴瀹逛笂浼?)
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
        print('使用璐﹀彿上传')
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
        print('使用cookies上传')

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

    def upload_file(self, filepath: str, lines='AUTO', tasks=3):
        """上传鏈湴瑙嗛文件,返回瑙嗛信息dict
        b绔欑洰鍓嶆敮鎸?绉嶄笂浼犵嚎璺痷pos, kodo, gcs, bos
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
            logger.info(f"绾胯矾选择 => {self._auto_os['os']}: {self._auto_os['query']}. time: {self._auto_os.get('cost')}")
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
        # 寮€濮嬩笂浼?
        parts = []  # 鍒嗗潡信息
        chunks = math.ceil(total_size / chunk_size)  # 获取鍒嗗潡数量

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
                logger.info("请求合并分片出现问题锛屽皾璇曢噸杩烇紝次数锛? + str(ii))
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
                logger.info("上传出现问题锛屽皾璇曢噸杩烇紝次数锛? + str(ii))
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
        # 寮€濮嬩笂浼?
        parts = []  # 鍒嗗潡信息
        chunks = math.ceil(total_size / chunk_size)  # 获取鍒嗗潡数量

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
        url = f"https:{endpoint}/{upos_uri.replace('upos://', '')}"  # 瑙嗛上传璺緞
        headers = {
            "X-Upos-Auth": auth
        }
        # 鍚戜笂浼犲湴址鐢宠上传锛屽緱鍒颁笂浼爄d绛変俊鎭?
        upload_d = self.__session.post(f'{url}?uploads&output=json', timeout=15,
                                        headers=headers).json()["upload_d"]
        # 寮€濮嬩笂浼?
        parts = []  # 鍒嗗潡信息
        chunks = math.ceil(total_size / chunk_size)  # 获取鍒嗗潡数量

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
        while attempt <= 5:  # 涓€鏃︽斁寮冨氨浼氫涪澶卞墠闈㈡墍鏈夌殑杩涘害锛屽璇曞嚑娆″吧
            try:
                r = self.__session.post(url, params=p, json={"parts": parts}, headers=headers, timeout=15).json()
                if r.get('OK') == 1:
                    logger.info(f'{filename} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {r}')
                    return {"title": splitext(os.path.basename(filename))[0], "filename": splitext(basename(upos_uri))[0], "desc": ""}
                raise IOError(r)
            except IOError:
                attempt += 1
                logger.info(f"请求合并分片鏃跺嚭鐜伴棶棰橈紝尝试閲嶈繛锛屾鏁帮細" + str(attempt))
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
            logger.info(f'用户鏉冮噸: {user_weight}')
            submit_api = 'web'
        ret = None
        if submit_api == 'web':
            ret = self.submit_web()
            if ret["code"] != 0:
                logger.error(f'网页绔帴鍙ｆ彁浜ゅけ璐? {ret}')
                raise Exception(ret)
        if not ret:
            raise Exception(f'涓嶅瓨鍦ㄧ殑閫夐」锛歿submit_api}')
        return ret

    def submit_web(self):
        logger.info('使用网页绔痑pi鎻愪氦')
        return self.__session.post(f'https://member.bilibili.com/x/vu/web/add?csrf={self.__bili_jct}', timeout=5,
                                   json=asdict(self.vdeo)).json()

    def submit_client(self):
        logger.info('使用客户绔痑pi绔彁浜?)
        if not self.access_token:
            if self.account is None:
                raise RuntimeError("Access token is required, but account and access_token does not exist!")
            self.login_by_password(**self.account)
            self.store()
        while True:
            ret = self.__session.post(f'http://member.bilibili.com/x/vu/client/add?access_key={self.access_token}',
                                      timeout=5, json=asdict(self.vdeo)).json()
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

    def get_tags(self, upvdeo, typed="", desc="", cover="", groupd=1, vfea=""):
        """
        上传瑙嗛鍚庤幏寰楁帹鑽愭爣绛?
        :param vfea:
        :param groupd:
        :param typed:
        :param desc:
        :param cover:
        :param upvdeo:
        :return: 返回瀹樻柟鎺ㄨ崘鐨則ag
        """
        url = f'https://member.bilibili.com/x/web/archive/tags?' \
              f'typed={typed}&title={quote(upvdeo["title"])}&filename=filename&desc={desc}&cover={cover}' \
              f'&groupd={groupd}&vfea={vfea}'
        return self.__session.get(url=url, timeout=5).json()

    # ==================== 鍚堥泦锛圫EASON锛夌鐞?====================
    #
    # B绔?鏂扮増鍚堥泦"锛圫EASON 类型锛夌殑绠＄悊鎺ュ彛锛屾敮鎸侊細
    #   - 鍒楀嚭用户鐨勬墍鏈夊悎闆?
    #   - 查看鍚堥泦鍐呯殑瑙嗛列表
    #   - 灏嗚棰戞坊鍔犲埌鍚堥泦
    #   - 浠庡悎闆嗕腑绉婚櫎瑙嗛
    #   - 瀵瑰悎闆嗗唴瑙嗛重新鎺掑簭
    #
    # 鏍稿績姒傚康锛?
    #   season_d  - 鍚堥泦ID锛屼粠鍒涗綔涓績鍚堥泦绠＄悊椤甸潰鐨刄RL鎴?list_seasons() 获取
    #   section_d - 鍚堥泦涓嬬殑"鍒嗗尯"ID锛屾瘡涓悎闆嗚嚦灏戞有涓€涓粯璁ゅ垎鍖猴紝
    #                閫氳繃 list_seasons() 返回鐨?sections.sections[0].d 获取
    #   episode_d - 瑙嗛鍦ㄥ悎闆嗕腑鐨勫唴閮↖D锛堜笉鏄?ad锛夛紝
    #                閫氳繃 get_season_section() 返回鐨?episodes[i]['d'] 获取
    #
    # 鍏稿瀷娴佺▼锛堜笂浼犲悗娣诲姞鍒板悎闆嗭級锛?
    #   1. seasons = bili.list_seasons()  # 获取鍚堥泦列表锛屾壘鍒?season_d 鍜?section_d
    #   2. info = bili.get_vdeo_info(ad)  # 获取瑙嗛鐨?cd 鍜?title
    #   3. bili.add_to_season(section_d, [{...}])  # 娣诲姞鍒板悎闆?
    def list_seasons(self, pn=1, ps=30):
        """
        获取用户鐨勫悎闆嗗垪琛?

        返回鍊肩ず渚?:

            {
                'seasons': [{
                    'season': {'d': 7320255, 'title': '鎴戠殑鍚堥泦', ...},
                    'sections': {'sections': [{'d': 8081933, 'title': '姝ｇ墖', ...}]}
                }, ...],
                'page': {'pn': 1, 'ps': 30, 'total': 5}
            }

        获取 section_d 鐨勬柟寮忥細
        ``data['seasons'][0]['sections']['sections'][0]['d']``

        :param pn: 椤电爜锛屼粠1寮€濮?
        :param ps: 姣忛〉数量锛岄粯璁?0
        :return: 鍖呭惈 seasons 列表鍜屽垎椤典俊鎭殑 dict
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
        获取鍚堥泦鍒嗗尯鍐呯殑瑙嗛列表

        返回鍊间腑姣忎釜 episode 鍖呭惈::

            {'d': 176218279, 'ad': 12345, 'cd': 67890, 'title': '...', ...}

        鍏朵腑 ``d`` 鏄?episode_d锛堝悎闆嗗唴閮↖D锛夛紝鐢ㄤ簬 remove_from_season 鍜屾帓搴忋€?

        :param section_d: 鍒嗗尯ID锛岄€氳繃 list_seasons() 获取
        :param sort: 鎺掑簭鏂瑰紡锛屽彲閫?'desc'锛堥檷搴忥級
        :return: 鍖呭惈 section 信息鍜?episodes 列表鐨?dict
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
        获取瑙嗛信息锛堟爣棰樸€乧d 绛夛級锛岀敤浜庢坊鍔犲埌鍚堥泦鍓嶈幏鍙栧繀瑕佸弬鏁?

        :param ad: 瑙嗛AV鍙凤紙鏁存暟锛?
        :return: 瑙嗛信息 dict锛屽寘鍚?title, pages[0].cd 绛?
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
        灏嗚棰戞坊鍔犲埌鍚堥泦锛堟柊鐗堝悎闆?SEASON锛?

        娣诲姞鍗曚釜瑙嗛鐨勫吀鍨嬬敤娉?:

            info = bili.get_vdeo_info(ad)
            bili.add_to_season(section_d, [{
                'ad': ad,
                'cd': info['pages'][0]['cd'],
                'title': info['title'],
                'charging_pay': 0,
            }])

        鍙竴娆℃坊鍔犲涓棰戯紙浼犲叆澶氫釜 episode dict锛夈€?

        :param section_d: 鍒嗗尯ID锛岄€氳繃 list_seasons() 获取
        :param episodes: 瑙嗛列表锛屾瘡椤归』鍚?ad, cd, title, charging_pay
        :return: API 返回鐨?JSON
        :raises Exception: API 返回 code != 0 鏃舵姏鍑?
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
        浠庡悎闆嗕腑绉婚櫎涓€涓棰?

        娉ㄦ剰锛氬弬鏁版槸 episode_d锛堝悎闆嗗唴閮↖D锛夛紝涓嶆槸 ad銆?
        闇€瑕佸厛閫氳繃 get_season_section() 获取 episodes 列表锛?
        鎵惧埌目标瑙嗛鐨?``episode['d']`` 瀛楁銆?

        姣忔鍙兘绉婚櫎涓€涓棰戯紝鎵归噺绉婚櫎闇€瑕佸惊鐜皟鐢ㄣ€?

        :param episode_d: 鍚堥泦鍐呴儴鐨?episode ID锛堜笉鏄?ad锛?
        :return: API 返回鐨?JSON
        :raises Exception: API 返回 code != 0 鏃舵姏鍑?
        """
        r = self.__session.post(
            'https://member.bilibili.com/x2/creative/web/season/section/episode/del',
            data={'d': episode_d, 'csrf': self.__bili_jct},
            timeout=10
        ).json()
        if r['code'] != 0:
            raise Exception(r)
        return r

    def sort_season_episodes(self, section_d, season_d, sorts, section_title='姝ｇ墖'):
        """
        瀵瑰悎闆嗗唴鐨勮棰戦噸鏂版帓搴?

        使用绀轰緥::

            section = bili.get_season_section(section_d)
            eps = section['episodes']
            # 鍙嶈浆椤哄簭
            sorts = [{'d': ep['d'], 'sort': i+1} for i, ep in enumerate(reversed(eps))]
            bili.sort_season_episodes(section_d, season_d, sorts)

        娉ㄦ剰浜嬮」锛?
        - sorts 必须鍖呭惈鍚堥泦中的**鎵€鏈?*瑙嗛锛屼笉鑳藉彧浼犻儴鍒?
        - section_d銆乻eason_d銆乻ection_title 涓変釜参数缂轰竴涓嶅彲锛屽惁鍒欒繑鍥?-400
        - sort 搴忓彿浠?寮€濮?

        :param section_d: 鍒嗗尯ID
        :param season_d: 鍚堥泦ID
        :param sorts: 鎺掑簭鏁扮粍锛屾瘡椤瑰惈 d (episode_d) 鍜?sort (1-indexed 搴忓彿)
        :param section_title: 鍒嗗尯鏍囬锛岄粯璁?姝ｇ墖"
        :return: API 返回鐨?JSON
        :raises Exception: API 返回 code != 0 鏃舵姏鍑?
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
    cover: 界面鍥剧墖锛屽彲鐢眗ecovers鏂规硶寰楀埌瑙嗛鐨勫抚鎴浘
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
        """设置寤舵椂鍙戝竷时间锛岃窛绂绘彁浜ゅぇ浜?灏忔椂锛屾牸寮忎负10浣嶆椂闂存埑"""
        if dtime - int(time.time()) > 7200:
            self.dtime = dtime

    def set_tag(self, tag: list):
        """设置鏍囩锛宼ag涓烘暟缁?""
        self.tag = ','.join(tag)

    def append(self, vdeo):
        self.vdeos.append(vdeo)
