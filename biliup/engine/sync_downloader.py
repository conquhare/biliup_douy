#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import queue
import threading
import subprocess
import time
from urllib.parse import urlparse


logger = logging.getLogger('biliup.engine.sync_downloader')


def pad_file_to_size(filename, min_file_size):
    """
    鑻ユ枃浠跺ぇ灏忎笉瓒?min_file_size锛屽垯鍦ㄦ枃浠舵湯灏惧～鍏?0x00 鑷崇洰鏍囧ぇ灏忋€?
    """
    if not os.path.exists(filename):
        return

    current_size = os.path.getsize(filename)
    if current_size < min_file_size:
        need_pad = min_file_size - current_size
        print(f"[pad_file_to_size] 琛ラ綈文件 {filename}锛?
              f"濉厖 {need_pad} 瀛楄妭 0x00 浣垮叾杈惧埌 {min_file_size} 瀛楄妭")
        with open(filename, "ab") as f:
            f.write(b"\x00" * need_pad)


class SyncDownloader:
    """
    鍚屾下载-鍒囩墖绫?
    说明锛?
      1. 鍦?run() 鏂规硶涓紝鍗曠嚎绋嬪惊鐜墽琛屽綍鍒堕€昏緫锛?
      2. 姣忔启动涓€娈?ffmpeg 褰曞埗锛屽苟璇诲彇 streamlink stdout 浣滀负杈撳叆锛?
      3. 褰?ffmpeg 褰曞埗结束鍚庯紝鏉€鎺夊綋鍓嶇殑 streamlink 杩涚▼骞惰ˉ榻愭枃浠跺ぇ灏忥紱
      4. 鑻ヤ腑閫斿彂鐜?streamlink 鏃犳暟鎹彲璇伙紙EOF锛夛紝鍒欒鏄庢病鏈夋洿澶氬唴瀹瑰彲下载锛岀粨鏉熸暣涓▼搴忋€?
    """

    def __init__(self,
                 stream_url="http://localhost:8888/stream0/index.m3u8",
                 headers={"a": "1"},
                 segment_duration=10,
                 max_file_size=100,
                 output_prefix="segment_",
                 video_queue=None):
        """
        :param stream_url:   鎷夋祦鍦板潃

        :param segment_duration: 姣忔褰曞埗鏃堕暱锛堢锛夛紙暂时涓嶇敤锛?
        :param max_file_size:     文件鏈€灏忓ぇ灏忥紝涓嶈冻鏃惰繘琛?0x00 濉厖 鍗曚綅 MB
        :param read_block_size:   浠?streamlink stdout 璇诲彇数据鏃剁殑鍗曟鍧楀ぇ灏?
        :param output_prefix:     杈撳嚭文件鍚嶅墠缂€
        """
        self.stream_url = stream_url
        self.quality = "best"
        self.headers = headers
        self.segment_duration = segment_duration
        self.read_block_size = 500
        self.max_file_size = max_file_size
        self.output_prefix = output_prefix

        self.video_queue: queue.SimpleQueue = video_queue
        self.stop_event = threading.Event()

    def run_ffmpeg_with_url(self, ffmpeg_cmd, output_filename):
        with subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE) as ffmpeg_proc:
            logger.info("[run] 启动 ffmpeg...")
            if output_filename == "-":
                data = ffmpeg_proc.stdout.read(self.read_block_size)  # 璇诲彇绗竴涓?data
                if not data:  # 濡傛灉绗竴涓?data 涓虹┖
                    logger.info("[run] ffmpeg 没有杈撳嚭数据锛岃繑鍥?False")
                    err = ffmpeg_proc.stderr.read()
                    if err:
                        logger.error("[run] ffmpeg err " + err.decode("utf-8", errors="replace"))
                    return False
                self.video_queue.put(data)  # 灏嗙涓€涓暟鎹斁鍏ラ槦鍒?
                while True:
                    data = ffmpeg_proc.stdout.read(self.read_block_size)
                    if not data:
                        logger.info("[run] ffmpeg stdout 宸插埌杈?EOF銆傜粨鏉熸湰娈靛啓鍏ャ€?)
                        break
                    self.video_queue.put(data)
            ffmpeg_proc.wait()
            # 杈撳嚭 ffmpeg 鐨勯敊璇俊鎭紙濡傛灉鏈夌殑璇濓級
            # err = ffmpeg_proc.stderr.read()
            # if err:
            #     logger.error("[run] ffmpeg err " + err.decode("utf-8", errors="replace"))
        return True  # 濡傛灉姝ｅ父鎵ц锛岃繑鍥?True

    def run_streamlink_with_ffmpeg(self, streamlink_cmd, ffmpeg_cmd, output_filename):
        with subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as streamlink_proc:
            logger.info("[run] 启动 streamlink...")
            with subprocess.Popen(ffmpeg_cmd, stdin=streamlink_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ffmpeg_proc:
                logger.info("[run] 启动 ffmpeg...")
                if output_filename == "-":
                    logger.info("[run] 璇诲彇 ffmpeg stdout...")
                    # 璇诲彇绗竴涓暟鎹?
                    data = ffmpeg_proc.stdout.read(self.read_block_size)
                    if not data:  # 濡傛灉绗竴涓暟鎹负绌?
                        logger.info("[run] ffmpeg 没有杈撳嚭数据锛岃繑鍥?False")
                        streamlink_proc.kill()  # 缁堟 streamlink 杩涚▼
                        ffmpeg_proc.kill()  # 缁堟 ffmpeg 杩涚▼
                        # 鎵撳嵃错误杈撳嚭
                        ffmpeg_err = ffmpeg_proc.stderr.read()
                        if ffmpeg_err:
                            logger.error("[run] ffmpeg err " + ffmpeg_err.decode("utf-8", errors="replace"))
                        streamlink_err = streamlink_proc.stderr.read()
                        if streamlink_err:
                            logger.error("[run] streamlink err " + streamlink_err.decode("utf-8", errors="replace"))
                        return False

                    self.video_queue.put(data)  # 灏嗙涓€涓暟鎹斁鍏ラ槦鍒?
                    # 缁х画璇诲彇鍓╀綑数据
                    while True:
                        data = ffmpeg_proc.stdout.read(self.read_block_size)
                        if not data:
                            logger.info("[run] ffmpeg stdout 宸插埌杈?EOF銆傜粨鏉熸湰娈靛啓鍏ャ€?)
                            break
                        self.video_queue.put(data)

                ffmpeg_proc.wait()
                logger.info("[run] ffmpeg 宸插埌杈捐緭鍑哄ぇ灏忓苟閫€鍑恒€傜粨鏉熸湰娈靛啓鍏ャ€?)
                # 鎵撳嵃 ffmpeg 瀛愯繘绋嬬殑错误杈撳嚭
                # ffmpeg_err = ffmpeg_proc.stderr.read()
                # if ffmpeg_err:
                # logger.error("[run] ffmpeg err " + ffmpeg_err.decode("utf-8", errors="replace"))
            # 鎵撳嵃 streamlink 瀛愯繘绋嬬殑错误杈撳嚭
            # streamlink_err = streamlink_proc.stderr.read()
            # if streamlink_err:
            #     logger.error("[run] streamlink err " + streamlink_err.decode("utf-8", errors="replace"))
        return True  # 濡傛灉涓€鍒囨甯革紝杩斿洖 True

    def build_ffmpeg_cmd(self, input_source, output_filename, headers, segment_duration):
        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            # "-"  # 瑕嗙洊杈撳嚭文件
        ]
        if headers:
            cmd += ["-headers", ''.join(f'{key}: {value}\r\n' for key, value in headers.items())]
        for i in [
            "-fflags", "+genpts",
            "-i", input_source,  # 杈撳叆婧?
            # "-t", str(segment_duration),
            "-fs", f"{self.max_file_size}M",
            "-c:v", "copy",
            "-c:a", "copy",
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "1",
            "-movflags", "+frag_keyframe+empty_moov",
            "-f", "matroska",
            "-",
        ]:
            cmd.append(i)
        return cmd

    def run(self):
        """
        涓婚€昏緫锛氬惊鐜繘琛屽垎娈靛綍鍒躲€?
        - 姣忔褰曞埗锛?
          1) 启动 streamlink锛涜嫢 EOF 鍒欓€€鍑恒€?
          2) 启动 ffmpeg (甯?-fs 参数限制杈撳嚭大小)锛?
          3) 浠?streamlink stdout 璇绘暟鎹紝鍐欑粰 ffmpeg stdin锛?
          4) ffmpeg 鍒版椂闀垮悗閫€鍑猴紝鐒跺悗鏉€鎺?streamlink锛?
          5) 杩涘叆涓嬩竴娈碉紝濡傛寰€澶嶃€?
        - 鑻ヤ腑閫斿彂鐜?streamlink 鏃犳暟鎹紙EOF锛夊垯璺冲嚭寰幆銆?
        """

        file_index = 1
        retry_count = 0
        while True:
            if self.stop_event.is_set():
                break
            if retry_count >= 5:
                logger.info("杩欎釜直播娴佸凡缁忓け鏁堬紝鍋滄下载鍣?)
                return

            output_filename = f"{self.output_prefix}{file_index:03d}.mkv"
            # print(f"\n[run] ========== 鍑嗗褰曞埗绗?{file_index} 娈碉細{output_filename} ==========")
            # logging.info(f"\n[run] == 褰撳墠下载娴佸湴鍧€锛歿self.stream_url} ==")
            logger.info(f"\n[run] == 鍑嗗褰曞埗绗?{file_index} 娈碉細{output_filename} ==")
            output_filename = "-"
            is_hls = '.m3u8' in urlparse(self.stream_url).path
            if not is_hls:
                # print("[run] 杈撳叆婧愪笉鏄?HLS 鍦板潃锛屽皢鐩存帴浣跨敤 ffmpeg 杩涜褰曞埗銆?, self.stream_url)
                logger.info("[run] 杈撳叆婧愪笉鏄?HLS 鍦板潃锛屽皢鐩存帴浣跨敤 ffmpeg 杩涜褰曞埗銆?)
                ffmpeg_cmd = self.build_ffmpeg_cmd(self.stream_url, output_filename,
                                                   self.headers, self.segment_duration)
                if not self.run_ffmpeg_with_url(ffmpeg_cmd, output_filename):
                    retry_count += 1
                    time.sleep(1)
                    continue
            else:
                # print("[run] 杈撳叆婧愭槸 HLS 鍦板潃锛屽皢浣跨敤 streamlink + ffmpeg 杩涜褰曞埗銆?)
                logger.info("[run] 杈撳叆婧愭槸 HLS 鍦板潃锛屽皢浣跨敤 streamlink + ffmpeg 杩涜褰曞埗銆?)
                if self.headers:
                    headers = []
                    for key, value in self.headers.items():
                        headers.extend(['--http-header', f'{key}={value}'])
                streamlink_cmd = [
                    'streamlink',
                    '--stream-segment-threads', '3',
                    '--hls-playlist-reload-attempts', '1',
                    *headers,
                    self.stream_url,
                    self.quality,
                    '-O'
                ]
                logger.info(f"[run] streamlink_cmd: {streamlink_cmd}")
                # output_filename = "-"
                ffmpeg_cmd = self.build_ffmpeg_cmd("pipe:0", output_filename, None, self.segment_duration)
                if not self.run_streamlink_with_ffmpeg(streamlink_cmd, ffmpeg_cmd, output_filename):
                    retry_count += 1
                    time.sleep(1)
                    continue

            # 6. 杩涘叆涓嬩竴娈?
            # if file_index != 1:
            self.video_queue.put(None)  # 閫氱煡娑堣垂鑰呯嚎绋嬫湰娈靛綍鍒剁粨鏉?
            file_index += 1


def main():
    slicer = SyncDownloader(
        stream_url="http://127.0.0.1:8888/live/index.m3u8",
        segment_duration=10,
        read_block_size=4096,
        output_prefix="segment_"
    )

    # ====銆愬彲閫夈€戞秷璐硅€呯嚎绋嬬ず渚嬶紝婕旂ず濡備綍鎷垮埌 video_queue 鐨勬暟鎹?===
    def consumer():
        file_index = 1
        while True:
            data_count = 0
            with open(f"output_{file_index}.mkv", "wb") as f:
                while True:
                    data = slicer.video_queue.get()  # 闃诲寮忚幏鍙?
                    if data is None:
                        break
                    f.write(data)
                    data_count += len(data)
                    # print(f"[consumer] 写入文件 output_{file_index}.mkv锛屽ぇ灏忥細{data_count} 瀛?)
            print(f"[consumer] 写入文件 output_{file_index}.mkv锛屽ぇ灏忥細{data_count} 瀛?)

            if data_count < 100:
                print(f"[consumer] 鏃犳晥文件锛屽垹闄?output_{file_index}.mkv")
                os.remove(f"output_{file_index}.mkv")
                slicer.stop_event.set()
                break

            pad_file_to_size(f"output_{file_index}.mkv", 100 * 1024 * 1024)  # 琛ラ綈文件大小
            file_index += 1
            # if slicer.stop_event.is_set():
            # break
            # 鍦ㄨ繖閲屽彲浠ュ data 鍋氳繘涓€姝ュ鐞嗭紝姣斿鍐嶆帹鍒板埆鐨勫湴鏂?

    # 启动娑堣垂鑰呯嚎绋?
    t = threading.Thread(target=consumer, daemon=True)
    t.start()

    # 启动下载褰曞埗涓婚€昏緫
    slicer.run()

    # 鍋滄娑堣垂鑰咃紙濡傚綍鍒跺畬姣曞悗鍙墽琛岋級
    # slicer.video_queue.put(None)

    # t.join()


if __name__ == "__main__":
    main()
