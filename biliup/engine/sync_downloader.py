锘?!/usr/bin/env python3
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
    閼汇儲鏋冩禒璺恒亣鐏忓繋绗夌搾?min_file_size閿涘苯鍨崷銊︽瀮娴犺埖婀亸鎯э綖閸?0x00 閼峰磭娲伴弽鍥с亣鐏忓繈鈧?
    """
    if not os.path.exists(filename):
        return

    current_size = os.path.getsize(filename)
    if current_size < min_file_size:
        need_pad = min_file_size - current_size
        print(f"[pad_file_to_size] 鐞涖儵缍堟枃浠?{filename}閿?
              f"婵夘偄鍘?{need_pad} 鐎涙濡?0x00 娴ｅ灝鍙炬潏鎯у煂 {min_file_size} 鐎涙濡?)
        with open(filename, "ab") as f:
            f.write(b"\x00" * need_pad)


class SyncDownloader:
    """
    閸氬本顒炰笅杞?閸掑洨澧栫猾?
    璇存槑閿?
      1. 閸?run() 閺傝纭舵稉顓ㄧ礉閸楁洜鍤庣粙瀣儕閻滎垱澧界悰灞界秿閸掑爼鈧槒绶敍?
      2. 濮ｅ繑顐煎惎鍔ㄦ稉鈧▓?ffmpeg 瑜版洖鍩楅敍灞借嫙鐠囪褰?streamlink stdout 娴ｆ粈璐熸潏鎾冲弳閿?
      3. 瑜?ffmpeg 瑜版洖鍩楃粨鏉熼崥搴礉閺夆偓閹哄缍嬮崜宥囨畱 streamlink 鏉╂稓鈻奸獮鎯八夋鎰瀮娴犺泛銇囩亸蹇ョ幢
      4. 閼汇儰鑵戦柅鏂垮絺閻?streamlink 閺冪姵鏆熼幑顔煎讲鐠囦紮绱橢OF閿涘绱濋崚娆掝嚛閺勫孩鐥呴張澶嬫纯婢舵艾鍞寸€圭懓褰蹭笅杞介敍宀€绮ㄩ弶鐔告殻娑擃亞鈻兼惔蹇嬧偓?
    """

    def __init__(self,
                 stream_url="http://localhost:8888/stream0/index.m3u8",
                 headers={"a": "1"},
                 segment_duration=10,
                 max_file_size=100,
                 output_prefix="segment_",
                 video_queue=None):
        """
        :param stream_url:   閹峰绁﹂崷鏉挎絻

        :param segment_duration: 濮ｅ繑顔岃ぐ鏇炲煑閺冨爼鏆遍敍鍫㈩潡閿涘绱欐殏鏃舵稉宥囨暏閿?
        :param max_file_size:     鏂囦欢閺堚偓鐏忓繐銇囩亸蹇ョ礉娑撳秷鍐婚弮鎯扮箻鐞?0x00 婵夘偄鍘?閸楁洑缍?MB
        :param read_block_size:   娴?streamlink stdout 鐠囪褰囨暟鎹弮鍓佹畱閸楁洘顐奸崸妤€銇囩亸?
        :param output_prefix:     鏉堟挸鍤枃浠堕崥宥呭缂傗偓
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
            logger.info("[run] 鍚姩 ffmpeg...")
            if output_filename == "-":
                data = ffmpeg_proc.stdout.read(self.read_block_size)  # 鐠囪褰囩粭顑跨娑?data
                if not data:  # 婵″倹鐏夌粭顑跨娑?data 娑撹櫣鈹?
                    logger.info("[run] ffmpeg 娌℃湁鏉堟挸鍤暟鎹敍宀冪箲閸?False")
                    err = ffmpeg_proc.stderr.read()
                    if err:
                        logger.error("[run] ffmpeg err " + err.decode("utf-8", errors="replace"))
                    return False
                self.video_queue.put(data)  # 鐏忓棛顑囨稉鈧稉顏呮殶閹诡喗鏂侀崗銉╂Е閸?
                while True:
                    data = ffmpeg_proc.stdout.read(self.read_block_size)
                    if not data:
                        logger.info("[run] ffmpeg stdout 瀹告彃鍩屾潏?EOF閵嗗倻绮ㄩ弶鐔告拱濞堥潧鍟撻崗銉ｂ偓?)
                        break
                    self.video_queue.put(data)
            ffmpeg_proc.wait()
            # 鏉堟挸鍤?ffmpeg 閻ㄥ嫰鏁婄拠顖欎繆閹垽绱欐俊鍌涚亯閺堝娈戠拠婵撶礆
            # err = ffmpeg_proc.stderr.read()
            # if err:
            #     logger.error("[run] ffmpeg err " + err.decode("utf-8", errors="replace"))
        return True  # 婵″倹鐏夊锝呯埗閹笛嗩攽閿涘矁绻戦崶?True

    def run_streamlink_with_ffmpeg(self, streamlink_cmd, ffmpeg_cmd, output_filename):
        with subprocess.Popen(streamlink_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as streamlink_proc:
            logger.info("[run] 鍚姩 streamlink...")
            with subprocess.Popen(ffmpeg_cmd, stdin=streamlink_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as ffmpeg_proc:
                logger.info("[run] 鍚姩 ffmpeg...")
                if output_filename == "-":
                    logger.info("[run] 鐠囪褰?ffmpeg stdout...")
                    # 鐠囪褰囩粭顑跨娑擃亝鏆熼幑?
                    data = ffmpeg_proc.stdout.read(self.read_block_size)
                    if not data:  # 婵″倹鐏夌粭顑跨娑擃亝鏆熼幑顔昏礋缁?
                        logger.info("[run] ffmpeg 娌℃湁鏉堟挸鍤暟鎹敍宀冪箲閸?False")
                        streamlink_proc.kill()  # 缂佸牊顒?streamlink 鏉╂稓鈻?
                        ffmpeg_proc.kill()  # 缂佸牊顒?ffmpeg 鏉╂稓鈻?
                        # 閹垫挸宓冮敊璇潏鎾冲毉
                        ffmpeg_err = ffmpeg_proc.stderr.read()
                        if ffmpeg_err:
                            logger.error("[run] ffmpeg err " + ffmpeg_err.decode("utf-8", errors="replace"))
                        streamlink_err = streamlink_proc.stderr.read()
                        if streamlink_err:
                            logger.error("[run] streamlink err " + streamlink_err.decode("utf-8", errors="replace"))
                        return False

                    self.video_queue.put(data)  # 鐏忓棛顑囨稉鈧稉顏呮殶閹诡喗鏂侀崗銉╂Е閸?
                    # 缂佈呯敾鐠囪褰囬崜鈺€缍戞暟鎹?
                    while True:
                        data = ffmpeg_proc.stdout.read(self.read_block_size)
                        if not data:
                            logger.info("[run] ffmpeg stdout 瀹告彃鍩屾潏?EOF閵嗗倻绮ㄩ弶鐔告拱濞堥潧鍟撻崗銉ｂ偓?)
                            break
                        self.video_queue.put(data)

                ffmpeg_proc.wait()
                logger.info("[run] ffmpeg 瀹告彃鍩屾潏鎹愮翻閸戝搫銇囩亸蹇撹嫙闁偓閸戞亽鈧倻绮ㄩ弶鐔告拱濞堥潧鍟撻崗銉ｂ偓?)
                # 閹垫挸宓?ffmpeg 鐎涙劘绻樼粙瀣畱閿欒鏉堟挸鍤?
                # ffmpeg_err = ffmpeg_proc.stderr.read()
                # if ffmpeg_err:
                # logger.error("[run] ffmpeg err " + ffmpeg_err.decode("utf-8", errors="replace"))
            # 閹垫挸宓?streamlink 鐎涙劘绻樼粙瀣畱閿欒鏉堟挸鍤?
            # streamlink_err = streamlink_proc.stderr.read()
            # if streamlink_err:
            #     logger.error("[run] streamlink err " + streamlink_err.decode("utf-8", errors="replace"))
        return True  # 婵″倹鐏夋稉鈧崚鍥劀鐢潻绱濇潻鏂挎礀 True

    def build_ffmpeg_cmd(self, input_source, output_filename, headers, segment_duration):
        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            # "-"  # 鐟曞棛娲婃潏鎾冲毉鏂囦欢
        ]
        if headers:
            cmd += ["-headers", ''.join(f'{key}: {value}\r\n' for key, value in headers.items())]
        for i in [
            "-fflags", "+genpts",
            "-i", input_source,  # 鏉堟挸鍙嗗┃?
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
        娑撳鈧槒绶敍姘儕閻滎垵绻樼悰灞藉瀻濞堥潧缍嶉崚韬测偓?
        - 濮ｅ繑顔岃ぐ鏇炲煑閿?
          1) 鍚姩 streamlink閿涙稖瀚?EOF 閸掓瑩鈧偓閸戞亽鈧?
          2) 鍚姩 ffmpeg (鐢?-fs 鍙傛暟闄愬埗鏉堟挸鍤ぇ灏?閿?
          3) 娴?streamlink stdout 鐠囩粯鏆熼幑顕嗙礉閸愭瑧绮?ffmpeg stdin閿?
          4) ffmpeg 閸掔増妞傞梹鍨倵闁偓閸戠尨绱濋悞璺烘倵閺夆偓閹?streamlink閿?
          5) 鏉╂稑鍙嗘稉瀣╃濞堢绱濇俊鍌涱劃瀵扳偓婢跺秲鈧?
        - 閼汇儰鑵戦柅鏂垮絺閻?streamlink 閺冪姵鏆熼幑顕嗙礄EOF閿涘鍨捄鍐插毉瀵邦亞骞嗛妴?
        """

        file_index = 1
        retry_count = 0
        while True:
            if self.stop_event.is_set():
                break
            if retry_count >= 5:
                logger.info("鏉╂瑤閲滅洿鎾ù浣稿嚒缂佸繐銇戦弫鍫礉閸嬫粍顒涗笅杞介崳?)
                return

            output_filename = f"{self.output_prefix}{file_index:03d}.mkv"
            # print(f"\n[run] ========== 閸戝棗顦ぐ鏇炲煑缁?{file_index} 濞堢绱皗output_filename} ==========")
            # logging.info(f"\n[run] == 瑜版挸澧犱笅杞藉ù浣告勾閸р偓閿涙self.stream_url} ==")
            logger.info(f"\n[run] == 閸戝棗顦ぐ鏇炲煑缁?{file_index} 濞堢绱皗output_filename} ==")
            output_filename = "-"
            is_hls = '.m3u8' in urlparse(self.stream_url).path
            if not is_hls:
                # print("[run] 鏉堟挸鍙嗗┃鎰瑝閺?HLS 閸︽澘娼冮敍灞界殺閻╁瓨甯存担璺ㄦ暏 ffmpeg 鏉╂稖顢戣ぐ鏇炲煑閵?, self.stream_url)
                logger.info("[run] 鏉堟挸鍙嗗┃鎰瑝閺?HLS 閸︽澘娼冮敍灞界殺閻╁瓨甯存担璺ㄦ暏 ffmpeg 鏉╂稖顢戣ぐ鏇炲煑閵?)
                ffmpeg_cmd = self.build_ffmpeg_cmd(self.stream_url, output_filename,
                                                   self.headers, self.segment_duration)
                if not self.run_ffmpeg_with_url(ffmpeg_cmd, output_filename):
                    retry_count += 1
                    time.sleep(1)
                    continue
            else:
                # print("[run] 鏉堟挸鍙嗗┃鎰Ц HLS 閸︽澘娼冮敍灞界殺娴ｈ法鏁?streamlink + ffmpeg 鏉╂稖顢戣ぐ鏇炲煑閵?)
                logger.info("[run] 鏉堟挸鍙嗗┃鎰Ц HLS 閸︽澘娼冮敍灞界殺娴ｈ法鏁?streamlink + ffmpeg 鏉╂稖顢戣ぐ鏇炲煑閵?)
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

            # 6. 鏉╂稑鍙嗘稉瀣╃濞?
            # if file_index != 1:
            self.video_queue.put(None)  # 闁氨鐓″☉鍫ｅ瀭閼板懐鍤庣粙瀣拱濞堥潧缍嶉崚鍓佺波閺?
            file_index += 1


def main():
    slicer = SyncDownloader(
        stream_url="http://127.0.0.1:8888/live/index.m3u8",
        segment_duration=10,
        read_block_size=4096,
        output_prefix="segment_"
    )

    # ====閵嗘劕褰查柅澶堚偓鎴炵Х鐠愮鈧懐鍤庣粙瀣仛娓氬绱濆鏃傘仛婵″倷缍嶉幏鍨煂 video_queue 閻ㄥ嫭鏆熼幑?===
    def consumer():
        file_index = 1
        while True:
            data_count = 0
            with open(f"output_{file_index}.mkv", "wb") as f:
                while True:
                    data = slicer.video_queue.get()  # 闂冭顢ｅ蹇氬箯閸?
                    if data is None:
                        break
                    f.write(data)
                    data_count += len(data)
                    # print(f"[consumer] 鍐欏叆鏂囦欢 output_{file_index}.mkv閿涘苯銇囩亸蹇ョ窗{data_count} 鐎?)
            print(f"[consumer] 鍐欏叆鏂囦欢 output_{file_index}.mkv閿涘苯銇囩亸蹇ョ窗{data_count} 鐎?)

            if data_count < 100:
                print(f"[consumer] 閺冪姵鏅ユ枃浠堕敍灞藉灩闂?output_{file_index}.mkv")
                os.remove(f"output_{file_index}.mkv")
                slicer.stop_event.set()
                break

            pad_file_to_size(f"output_{file_index}.mkv", 100 * 1024 * 1024)  # 鐞涖儵缍堟枃浠跺ぇ灏?
            file_index += 1
            # if slicer.stop_event.is_set():
            # break
            # 閸︺劏绻栭柌灞藉讲娴犮儱顕?data 閸嬫俺绻樻稉鈧銉ヮ槱閻炲棴绱濆В鏂款洤閸愬秵甯归崚鏉垮焼閻ㄥ嫬婀撮弬?

    # 鍚姩濞戝牐鍨傞懓鍛殠缁?
    t = threading.Thread(target=consumer, daemon=True)
    t.start()

    # 鍚姩涓嬭浇瑜版洖鍩楁稉濠氣偓鏄忕帆
    slicer.run()

    # 閸嬫粍顒涘☉鍫ｅ瀭閼板拑绱欐俊鍌氱秿閸掕泛鐣В鏇炴倵閸欘垱澧界悰宀嬬礆
    # slicer.video_queue.put(None)

    # t.join()


if __name__ == "__main__":
    main()
