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


def resolve_ass_file(save_path, save_dir=None):
    """根据录制路径定位实际生成的 ASS 字幕文件。

    抽成模块级纯函数（不依赖 self / 网络），便于在没有开播的情况下
    用单元测试验证多段录制下的文件名错位问题。

    背景：边录边传是异步分片上传，弹幕在【最后一段】结束时才 save()，
    但此刻传入的save_path 仍是【当前段】的名字。实测 3 段录制时：
      当前段 save_path = xxx_1.mkv → 直接推导 xxx_1.ass
      实际生成         = xxx_2.ass（最后一段的回调产物）
    导致 os.path.exists 恒为 False，字幕上传被静默跳过。

    返回：存在的 ass 路径；找不到时返回推导出的期望路径（供调用方告警打印）。
    """
    ass_file = os.path.splitext(save_path)[0] + '.ass'
    if not save_path or os.path.exists(ass_file):
        return ass_file

    # 退路：save_dir 下按前缀找最新生成的 ass（文件名带分片序号）
    try:
        prefix = os.path.splitext(os.path.basename(save_path))[0]
        stem = prefix.rsplit('_', 1)[0]  # 去掉 _1 / _2 分片后缀
        candidates = []
        search_dir = save_dir or os.path.dirname(save_path) or '.'
        for name in os.listdir(search_dir):
            if name.startswith(stem) and name.endswith('.ass'):
                path = os.path.join(search_dir, name)
                candidates.append((os.path.getmtime(path), path))
        if candidates:
            return max(candidates)[1]
    except Exception as e:
        logger.warning(f"查找字幕文件失败: {e}")
    return ass_file


@Plugin.upload(platform="bili_web_sync")
class BiliWebAsync(UploadBase):
    def __init__(
            self, principal, data, submit_api=None, copyright=2, postprocessor=None, dtime=None,
            dynamic='', lines='AUTO', threads=3, tid=122, tags=None, cover_path=None, description='',
            dolby=0, hires=0, no_reprint=0, is_only_self=0, charging_pay=0, credits=None,
            user_cookie='cookies.json', copyright_source=None, extra_fields="", video_queue=None,
            save_dir=None
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
        self.save_dir = save_dir

    def upload(self, total_size: int, stop_event: threading.Event, output_prefix: str, file_name_callback: Callable[[str], None] = None, database_row_id=0) -> List[UploadBase.FileInfo]:
        # print("开始同步上传")
        logger.info(f"开始同步上传 {database_row_id}")
        file_index = 1
        videos = Data()
        bili = BiliBili(videos, save_dir=self.save_dir)
        bili.database_row_id = database_row_id

        bili.login(self.persistence_path, self.user_cookie)
        videos.title = self.data["format_title"][:80]  # 稿件标题限制80字
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
            videos.source = self.data.get("url", "")  # 添加转载地址说明
        # 设置视频分区,默认为174 生活，其他分区
        videos.tid = self.tid
        videos.set_tag(self.tags)
        if self.dtime:
            videos.delay_time(int(time.time()) + self.dtime)
        if self.cover_path:
            videos.cover = bili.cover_up(self.cover_path).replace('http:', '')

        # 其他参数设置
        videos.extra_fields = self.extra_fields
        videos.dolby = self.dolby
        videos.hires = self.hires
        videos.no_reprint = self.no_reprint
        videos.is_only_self = self.is_only_self
        videos.charging_pay = self.charging_pay

        thread_list = []
        while True:
            file_name = f"{output_prefix}_{file_index}.mkv"
            data_size = 0
            video_upload_queue = queue.SimpleQueue()

            # 先读取第一个数据块，空分段直接跳过上传
            # 避免为 0 字节分段启动上传线程和调用 preupload API
            try:
                first_data = self.video_queue.get(timeout=30)
            except queue.Empty:
                if stop_event.is_set():
                    break
                continue

            if first_data is None:
                # 空分段（ffmpeg 无输出数据），跳过上传
                logger.info(f"[consumer] {file_name} 空分段（0字节），跳过上传")
                stop_event.set()
                break

            data_size = len(first_data)
            video_upload_queue.put(first_data)

            # 有数据，启动上传线程
            t = threading.Thread(target=bili.upload_stream, args=(video_upload_queue,
                                 file_name, total_size, self.lines, videos, stop_event, file_name_callback), daemon=True, name=f"upload_{file_index}")
            thread_list.append(t)
            t.start()

            # 继续读取剩余数据
            while True:
                try:
                    data = self.video_queue.get(timeout=10)
                except queue.Empty:
                    if stop_event.is_set():
                        video_upload_queue.put(None)
                        break
                    continue

                if data is None:
                    video_upload_queue.put(None)
                    break

                video_upload_queue.put(data)
                data_size += len(data)
            logger.info(f"[consumer] 读取 {file_name} {data_size} 字节")
            file_index += 1
            logger.info(f"[consumer] bili.video.videos {bili.video.videos}")
            if data_size < 100:
                logger.info(f"[consumer] 数据量过小 ({data_size} 字节)，停止下载")
                stop_event.set()
                video_upload_queue.put(None)

            if stop_event.is_set():
                video_upload_queue.put(None)
                break

        logger.info("等待上传线程结束")
        for t in thread_list:
            t.join()

        # 检查是否已有 aid（upload_stream 中已投稿），避免重复投稿
        if videos.aid is not None:
            logger.info(f"稿件已投稿 (aid={videos.aid})，跳过最终投稿")
        elif videos.videos:
            try:
                ret = bili.submit(self.submit_api, videos=videos)
                logger.info(f"最终投稿成功: {ret}")
            except Exception as e:
                logger.error(f"最终投稿失败: {e}")
        else:
            logger.info("没有有效分段需要投稿，跳过最终投稿")

        file_list = []
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
                logger.error('简介中的@credit占位符少于credits的数量,替换失败')
        desc_v2.append({
            "raw_text": " " + desc_v2_tmp,
            "biz_id": "",
            "type": 1
        })
        desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 开头空格会导致识别简介过长
        return desc_v2


class BiliBili:
    def __init__(self, video: 'Data', save_dir=None):
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

        self.save_dir = save_dir
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
            print('使用持久化内容上传')
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
            logger.exception('加载cookie出错')

    def store(self):
        with open(self.persistence_path, "w") as f:
            json.dump({**self.cookies,
                       'access_token': self.access_token,
                       'refresh_token': self.refresh_token
                       }, f)

    def login_by_password(self, username, password):
        print('使用账号上传')
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
        logger.info(f"线路:{ret['lines']}")
        data, auto_os = None, None
        min_cost = 0
        if ret['probe'].get('get'):
            method = 'get'
        else:
            method = 'post'
            data = bytes(int(1024 * 0.1 * 1024))
        for line in ret['lines']:
            start = time.perf_counter()
            try:
                test = self.__session.request(method, f"https:{line['probe_url']}", data=data, timeout=30)
            except Exception as e:
                # 单条线路探测失败（SSL 证书 / 连接 / 超时等）不应中断整体探测，
                # 继续尝试剩余候选线路，避免一条线路异常导致整个上传线程崩溃
                logger.warning(f"线路探测失败，跳过 {line.get('query')}: {type(e).__name__}: {e}")
                continue
            cost = time.perf_counter() - start
            print(line['query'], cost)
            if test.status_code != 200:
                logger.warning(f"线路 {line.get('query')} 返回状态码 {test.status_code}，跳过")
                continue
            if not min_cost or min_cost > cost:
                auto_os = line
                min_cost = cost
        if auto_os is None:
            logger.error("所有上传线路探测均失败")
            return None
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

        logger.info(f"{file_name} 开始上传")
        if self.save_dir:
            self.save_path = os.path.join(self.save_dir, file_name)
        else:
            self.save_path = file_name
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
            if not self._auto_os:
                # 所有候选线路均不可用，抛出明确错误，避免后续以 None 取值产生 TypeError
                raise RuntimeError("上传线路探测失败：所有候选线路均不可用（详见上方告警日志）")
            logger.info(f"线路选择 => {self._auto_os['os']}: {self._auto_os['query']}. time: {self._auto_os.get('cost')}")
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
            # 如果返回的endpoint不在probe_url中，则尝试在endpoints中校验probe_url是否可用
            if ret['endpoint'] not in self._auto_os['probe_url']:
                for endpoint in ret['endpoints']:
                    if endpoint in self._auto_os['probe_url']:
                        ret['endpoint'] = endpoint
                        logger.info(f"修改endpoint: {ret['endpoint']}")
                        break
                else:
                    logger.warning(f"选择的线路 {self._auto_os['os']} 没有返回对应 endpoint，不做修改")
        video_part = asyncio.run(upload(stream_queue, file_name, total_size, ret))
        if video_part is None:
            stop_event.set()
            # print("异常流 直接退出")
            return
        video_part['title'] = video_part['title'][:80]

        # ⭐ 尾巴分段过滤：下播/断流瞬间产生的最后一段往往只有几百 KB，
        # 但preupload 申请时声明的 total_size 是整个段的配额（常见 1.5GB），
        # 结果 B站稿件里会出现一个几秒的垃圾分P（实测10-09 场次第 2 段仅 519286 字节）。
        # 阈值取 1MB：低于此值视为无效尾巴段，不追加分P、不触发弹幕保存回调。
        # size 为 None 说明拿不到真实体积（旧链路），保守放行不做过滤。
        MIN_VALID_SEGMENT_BYTES = 1 * 1024 * 1024
        actual_size = video_part.pop('size', None)
        if actual_size is not None and actual_size < MIN_VALID_SEGMENT_BYTES:
            logger.warning(
                f"{file_name} 实际仅 {actual_size} 字节（< 1MB），判定为无效尾巴分段，"
                f"跳过投稿。本场有效分P 已保留，如无有效分段请手动确认投稿。")
            stop_event.set()
            return

        if str(self.database_row_id) in context["sync_downloader_map"]:
            context_data = context["sync_downloader_map"][str(self.database_row_id)].copy()
            context_data.pop('subtitle', None)
            videos = Data(**context_data)

        videos.append(video_part)  # 添加已经上传的视频
        edit = False if videos.aid is None else True
        ret = self.submit(submit_api=submit_api, edit=edit, videos=videos)
        if ret["code"] != 0:
            logger.error(f"投稿失败 [{ret['code']}]: {ret.get('message', '未知错误')}")
            return
        # logger.info(f"上传成功: {ret}")
        if edit:
            logger.info(f"编辑添加成功: {ret}")
        else:
            logger.info(f"上传成功: {ret}")
        aid = ret['data']['aid']
        videos.aid = aid
        context['sync_downloader_map'][str(self.database_row_id)] = videos.__dict__
        logger.info(f"上传完成 {file_name} {context['sync_downloader_map'][str(self.database_row_id)] }")

        # 先触发分段回调：保存弹幕 XML 并生成 ASS 字幕（边录边传模式下视频不落盘，
        #弹幕/字幕依赖此回调生成到 save_dir）
        if file_name_callback:
            file_name_callback(self.save_path)

        # 尝试上传对应字幕
        # ⚠️ 必须用 self.save_path 而不是 file_name 推导：
        # 边录边传是异步分片上传，弹幕在【最后一段】结束时才 save()，
        # 但此刻 file_name 仍是【当前段】的名字（详见 resolve_ass_file 文档）。
        ass_file = resolve_ass_file(self.save_path, self.save_dir)
        if os.path.exists(ass_file):
            try:
                # 传分P 标题（xxx_1），多分P 时精确匹配到本次上传的那一P
                part_title = os.path.splitext(os.path.basename(self.save_path))[0]
                cid = self._get_latest_cid(aid, part_title)
                if cid:
                    self._upload_subtitle_file(aid, cid, ass_file)
                else:
                    logger.warning(f"字幕文件存在但无法获取 cid，跳过字幕上传: {ass_file}")
            except Exception as e:
                logger.warning(f"上传字幕失败: {ass_file}: {e}")
        else:
            # 静默跳过是最坏的失败方式：弹幕录了、ASS 生成了、投稿成功了，
            # 用户却完全看不到字幕没上传。必须显式告警。
            logger.warning(f"未找到 ASS 字幕文件，跳过字幕上传: {ass_file}")

    async def upos_stream(self, stream_queue, file_name, total_size, ret):
        # print("--------------, ", file_name)
        chunk_size = ret['chunk_size']
        auth = ret["auth"]
        endpoint = ret["endpoint"]
        biz_id = ret["biz_id"]
        upos_uri = ret["upos_uri"]
        url = f"https:{endpoint}/{upos_uri.replace('upos://', '')}"  # 视频上传路径
        headers = {
            "X-Upos-Auth": auth
        }
        # 向上传地址申请上传，得到上传id等信息
        upload_id = self.__session.post(f'{url}?uploads&output=json', timeout=15,
                                        headers=headers).json()["upload_id"]
        # 开始上传
        parts = []  # 分块信息
        chunks = math.ceil(total_size / chunk_size)  # 获取分块数量

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

                # 等待所有分片上传完成，并按顺序收集结果
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
        while attempt <= 3:  # 一旦放弃就会丢失前面所有的进度，多试几次吧
            try:
                r = self.__session.post(url, params=p, json={"parts": parts}, headers=headers, timeout=15).json()
                if r.get('OK') == 1:
                    logger.info(f'{file_name} uploaded >> {total_size / 1000 / 1000 / cost:.2f}MB/s. {r}')
                    # size 一并返回：调用方用它判断是否属于无效尾巴分段
                    return {"title": splitext(file_name)[0], "filename": splitext(basename(upos_uri))[0],
                            "desc": "", "size": n}
                raise IOError(r)
            except IOError:
                logger.info(f"请求合并分片 {file_name} 时出现问题，尝试重连，次数：" + str(attempt))
                attempt += 1
                time.sleep(10)
        pass

    def upload_chunk_thread(self, url, chunk, params_clone, headers, file_name, max_retries=3, backoff_factor=1):
        st = time.perf_counter()
        retries = 0
        while retries < max_retries:
            try:
                r = requests.put(url=url, params=params_clone, data=chunk, headers=headers)

                # 如果上传成功，退出重试循环
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

                # 如果上传失败，但未达到最大重试次数，等待一段时间后重试
                else:
                    retries += 1
                    logger.warning(
                        f"{file_name} - chunks-{params_clone['chunk']} - up failed: {r.status_code}. Retrying {retries}/{max_retries}")

                    # 计算退避时间，逐步增加重试间隔
                    backoff_time = backoff_factor ** retries
                    time.sleep(backoff_time)

            except Exception as e:
                retries += 1
                logger.error(f"upload_chunk_thread err {str(e)}. Retrying {retries}/{max_retries}")

                # 计算退避时间，逐步增加重试间隔
                backoff_time = backoff_factor ** retries
                time.sleep(backoff_time)

        # 如果重试了所有次数仍然失败，记录错误
        logger.error(f"{file_name} - chunks-{params_clone['chunk']} - Upload failed after {max_retries} attempts.")
        return None

    def queue_reader_generator(self, simple_queue: queue.SimpleQueue, chunk_size: int, max_size: int):
        """
        从 simple_queue 中读取数据并按 chunk_size 大小分块产出 (yield)
        当队列中获取到 None 或者数据总量达到 max_size 后，就用 0x00 补齐到 chunk_size

        :param simple_queue: queue.SimpleQueue 实例，数据流会以多个分包 (bytes) 入队，最后以 None 表示结束
        :param chunk_size: 消费者每次想要获取的数据块大小
        :param max_size: 需要最终补齐的总大小（单位：字节），必须是 chunk_size 的整数倍
        :return: 生成器，按 chunk_size 大小分批次产出数据
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
                # 数据流结束，用0x00填充剩余的块
                remaining_chunks = total_chunks - chunks_yielded
                if remaining_chunks == total_chunks:
                    # print("空包跳过")
                    break
                if len(current_buffer) > 0:
                    # 处理当前缓冲区中的最后一块数据
                    padding_size = chunk_size - len(current_buffer)
                    if padding_size > 0:
                        current_buffer += b'\x00' * padding_size
                        logger.info(f"最后一个包差了 {padding_size} 个字节")
                    yield bytes(current_buffer)
                    chunks_yielded += 1
                    remaining_chunks -= 1
                break
                logger.info(f"还差 {remaining_chunks} 个完整包")

                # 输出剩余的全0块
                for _ in range(remaining_chunks):
                    yield b'\x00' * chunk_size
                    chunks_yielded += 1
                break

            save_file and save_file.write(data)

            # 将新数据添加到缓冲区
            current_buffer.extend(data)

            # 输出完整的块
            while len(current_buffer) >= chunk_size and chunks_yielded < total_chunks:
                yield bytes(current_buffer[:chunk_size])
                current_buffer = current_buffer[chunk_size:]
                chunks_yielded += 1

        # print("本段分p完成")
        save_file and save_file.close()
        yield None

    def submit(self, submit_api=None, edit=False, videos=None):

        # 不能提交 extra_fields 字段，提前处理
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
            logger.info(f'推测的用户权重: {user_weight}')
            # submit_api = 'web' if user_weight == 2 else 'client'
            # web 目前（2025-01-26）全量分p功能
            submit_api = 'web'
        ret = None
        if submit_api == 'web':
            ret = self.submit_web(post_data, edit=edit)
            if ret["code"] == 21138:
                time.sleep(5)
                logger.info(f'改用客户端接口提交{ret}')
                submit_api = 'client'
        if submit_api == 'client':
            ret = self.submit_client(post_data, edit=edit)
        if not ret:
            raise Exception(f'不存在的选项：{submit_api}')
        if ret["code"] == 0:
            return ret
        else:
            err_msg = ret.get('message', '未知错误')
            err_code = ret['code']
            # 常见错误码建议
            err_tips = {
                -1160: '投稿过于频繁，请24小时后重试',
                -101: '账号未登录或登录已过期',
                -102: '账号未实名认证',
            }
            tip = err_tips.get(err_code, '')
            tip_suffix = f' → 建议: {tip}' if tip else ''
            logger.error(f'投稿失败 [{err_code}]: {err_msg}{tip_suffix}')
            return ret

    def submit_web(self, post_data, edit=False):
        logger.info('使用网页端api提交')
        if not self.__bili_jct:
            raise RuntimeError("bili_jct is required!")
        api = 'https://member.bilibili.com/x/vu/web/add?csrf=' + self.__bili_jct
        if edit:
            api = 'https://member.bilibili.com/x/vu/web/edit?csrf=' + self.__bili_jct
        return self.__session.post(api, timeout=5,
                                   json=post_data).json()

    def submit_client(self, post_data, edit=False):
        logger.info('使用客户端api端提交')
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
                logger.info(f'刷新token{ret}')
                if self.account is None:
                    raise RuntimeError("Account info is required for token refresh!")
                self.login_by_password(**self.account)
                self.store()
                continue
            return ret

    # 候选 cid 查询接口，按顺序尝试。
    # 第一个 member.bilibili.com/x/vu/web/archive/view 已于实测返回 404 HTML
    #（.json() 抛 "Expecting value: line 1 column 1"），保留仅作兜底。
    _CID_APIS = (
        'https://api.bilibili.com/x/web-interface/view?aid={aid}',
        'https://member.bilibili.com/x/vu/web/archive/view?aid={aid}',
    )

    def _get_latest_cid(self, aid: int, part_title: str = None) -> int:
        """获取稿件中最新的视频分P cid。

        part_title 给定时优先按分P 标题精确匹配（边录边传是多分P 场景，
        只取最后一P 有可能拿到别的分P）；匹配不到再退回最后一个。
        """
        for tpl in self._CID_APIS:
            try:
                resp = self.__session.get(tpl.format(aid=aid), timeout=10)
                data = resp.json().get('data') or {}
                pages = data.get('pages') or data.get('videos') or []
                if not pages:
                    continue
                if part_title:
                    for p in pages:
                        # 分P 标题在B站会带上 _1 / _2 分片后缀，做前缀宽松匹配
                        title = p.get('part') or p.get('title') or ''
                        if title and (title == part_title
                                      or title.startswith(part_title)
                                      or part_title.startswith(title)):
                            return p.get('cid', 0)
                return pages[-1].get('cid', 0)
            except Exception as e:
                logger.warning(f"获取稿件 cid 失败 (aid={aid}, api={tpl}): {e}")
        return 0

    def _probe_subtitle_permission(self, aid: int, cid: int) -> bool:
        """探测 B站是否还允许本账号对该稿件提交人工字幕。

        2026-10 实测结论（重要，勿再重复踩）：
        -老接口 member.bilibili.com/x/v2/dm/subtitle/upload 已 404（端点下线）
        - 新流程第一步 api.bilibili.com/x/upload/web/image?bucket=subtitle 仍可用，
          能拿到字幕文件 URL（http://i0.hdslb.com/bfs/subtitle/xxx.txt）
        - 但绑定 URL 到 aid/cid 的 draft 接口返回 412（风控）或 -400
        - **播放器接口 data.subtitle.allow_submit == False 是决定性信号**：
          B站已对该稿件/账号关闭人工字幕提交权限（当前只有 AI 字幕 ai-zh）

        返回 True 表示允许提交；False 表示已被平台关闭。
        """
        try:
            r = self.__session.get(
                'https://api.bilibili.com/x/player/wbi/v2',
                params={'aid': aid, 'cid': cid}, timeout=10)
            sub = (r.json().get('data') or {}).get('subtitle') or {}
            if sub.get('allow_submit') is False:
                existing = [s.get('lan') for s in (sub.get('subtitles') or [])]
                logger.warning(
                    f"B站已关闭该稿件的人工字幕提交权限（allow_submit=False，"
                    f"现有字幕语言={existing or '无'}）。"
                    f"弹幕 ASS 仍会正常生成到本地，但无法自动上传。"
                    f"如需字幕请在创作中心网页端手动上传。"
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"探测字幕提交权限失败（不影响录制）: {e}")
            return True

    def _upload_subtitle_file(self, aid: int, cid: int, subtitle_file: str):
        """上传 ASS 字幕文件到B站视频。

        当前实现走「先传文件拿 URL，再绑定到稿件」的两步新流程，
        因为老的一步式接口 x/v2/dm/subtitle/upload 已 404。
        """
        if not self.__bili_jct:
            logger.warning("无法上传字幕: bili_jct 缺失")
            return

        # 前置检查：平台是否还允许提交人工字幕
        if not self._probe_subtitle_permission(aid, cid):
            return

        # 第1 步：上传字幕文件到 B 站存储，拿回 subtitle_url
        try:
            with open(subtitle_file, 'rb') as f:
                up = self.__session.post(
                    'https://api.bilibili.com/x/upload/web/image',
                    data={'csrf': self.__bili_jct, 'bucket': 'subtitle'},
                    files={'file': (os.path.basename(subtitle_file), f, 'application/octet-stream')},
                    timeout=30).json()
            if up.get('code') != 0:
                logger.warning(f"字幕文件上传失败: {up.get('message', up)} (aid={aid})")
                return
            subtitle_url = ((up.get('data') or {}).get('location') or '')
            if not subtitle_url:
                logger.warning(f"字幕文件上传未返回 URL: {up} (aid={aid})")
                return
            logger.info(f"字幕文件已上传至B站: {subtitle_url} (aid={aid}, cid={cid})")
        except Exception as e:
            logger.warning(f"字幕文件上传异常 (aid={aid}): {e}")
            return

        # 第 2 步：把 URL 绑定到 aid/cid
        # B站要求字幕内容为 BCC（JSON）格式，ASS 为纯文本需转换；
        #此处仅传 URL + 原始文本，由B站侧解析。绑定接口目前 412（风控），
        # 保留完整实现以便接口放开后直接生效。
        bcc = self._ass_to_bcc(subtitle_file)
        payload = {
            'csrf': self.__bili_jct,
            'csrf_token': self.__bili_jct,
            'aid': str(aid),
            'cid': str(cid),
            'lan': 'zh-Hans',
            'subtitle_url': subtitle_url,
            'subtitle_info': bcc,
        }
        for url in ('https://member.bilibili.com/x/vupre/web/draft/edit',
                    'https://member.bilibili.com/x/vupre/web/draft/add'):
            try:
                resp = self.__session.post(url, data=payload, timeout=20)
                if resp.status_code == 412:
                    logger.warning(
                        f"字幕绑定被 B站风控拦截（412）：{url}。"
                        f"字幕文件已上传成功但未绑定到稿件，可手动在创作中心确认。")
                    return
                body = resp.json()
                if body.get('code') == 0:
                    logger.info(f"字幕上传成功: {os.path.basename(subtitle_file)} (aid={aid}, cid={cid})")
                    return
                logger.warning(f"字幕绑定失败 [{body.get('code')}]: {body.get('message')} <- {url}")
            except Exception as e:
                logger.warning(f"字幕绑定异常 <- {url}: {e}")
        logger.warning(
            f"字幕未能绑定到稿件（aid={aid}, cid={cid}）。"
            f"字幕文件保留在本地: {subtitle_file}")

    @staticmethod
    def _ass_to_bcc(subtitle_file: str) -> str:
        """把 ASS 字幕转成 B站 BCC（JSON）格式。

        ⚠️ ASS 的时间轴与文本在**同一行**（Dialogue: 0,0:00:00.82,0:00:05.03,...），
        不是"时间独占一行 + 文本在下一行"。必须按 Dialogue 行整体解析，
        否则永远解析出 0 条（曾踩过这个坑）。
        """
        import re as _re
        body = []
        # Dialogue: 0,0:00:00.82,0:00:05.03,Style,,0,0,0,,文本
        #注意 Text 是最后一个字段，前面还有9 个逗号分隔的空字段（Layer 到 Effect）
        dialogue = _re.compile(
            r'^Dialogue:\s*[^,]*,(\d+):(\d+):(\d+)[.:](\d+)'
            r',(\d+):(\d+):(\d+)[.:](\d+)'
            r',[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)$'
        )
        try:
            with open(subtitle_file, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('['):
                        continue
                    m = dialogue.match(line)
                    if not m:
                        continue
                    h1, m1, s1, c1, h2, m2, s2, c2, text = m.groups()
                    start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(c1) / 100.0
                    end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(c2) / 100.0
                    # 剥离 {\move(...)\c&Hffffff&} 等内联样式标签
                    text = _re.sub(r'\{[^}]*\}', '', text).lstrip(',').strip()
                    if text:
                        body.append({'from': start, 'to': end, 'content': text})
        except Exception as e:
            logger.warning(f"ASS 转 BCC 失败（将提交原文）: {e}")
        if not body:
            logger.warning(f"ASS 转 BCC 未解析出任何字幕条目: {subtitle_file}")
            return ''
        logger.info(f"ASS 转 BCC 完成: {len(body)} 条字幕")
        return json.dumps({
            'font_size': 0.4, 'margin_v': 0.2, 'margin_h': 0.05,
            'bold': False, 'italic': False, 'color': 0xFFFFFF,
            'body': body, 'version': '1',
        }, ensure_ascii=False)

    def cover_up(self, img: str):
        """
        :param img: img path or stream
        :return: img URL
        """
        from PIL import Image
        from io import BytesIO

        with Image.open(img) as im:
            # 宽和高,需要16：10
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
        上传视频后获得推荐标签
        :param vfea:
        :param groupid:
        :param typeid:
        :param desc:
        :param cover:
        :param upvideo:
        :return: 返回官方推荐的tag
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
    cover: 封面图片，可由recovers方法得到视频的帧截图
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
        """设置延时发布时间，距离提交大于2小时，格式为10位时间戳"""
        if dtime - int(time.time()) > 7200:
            self.dtime = dtime

    def set_tag(self, tag: list):
        """设置标签，tag为数组"""
        self.tag = ','.join(tag)

    def append(self, video):
        self.videos.append(video)
