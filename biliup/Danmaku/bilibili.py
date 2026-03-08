锘縤mport json
import logging
import zlib
from struct import pack, unpack

import aiohttp
import brotli

from biliup.plugins import match1
from biliup.plugins import random_user_agent
from biliup.plugins import wbi, generate_fake_buvid3

logger = logging.getLogger('biliup')


class Bilibili:
    heartbeat = b'\x00\x00\x00\x1f\x00\x10\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x5b\x6f\x62\x6a\x65\x63\x74\x20' \
                b'\x4f\x62\x6a\x65\x63\x74\x5d '
    heartbeatInterval = 30
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'accept-language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'user-agent': random_user_agent(),
        'origin': 'https://live.bilibili.com',
        'referer': 'https://live.bilibili.com'
    }

    @staticmethod
    async def get_ws_info(url, content):

        uid = content['uid']
        # 娴肩姴鍙嗛崘鍛啇娑擃叏绱濇俊鍌涚亯 uid 娑撳秳璐?0閿涘苯鍨?cookie 韫囧懐鍔у瓨鍦ㄩ敍灞肩瑬韫囧懐鍔ф稉楦款嚊缂佸棙膩瀵?
        Bilibili.headers['cookie'] = f"buvid3={generate_fake_buvid3()};"
        if uid > 0:
            Bilibili.headers['cookie'] += content['cookie']
            
            
        # 鑾峰彇瀵懓绠风拋銈堢槈淇℃伅
        danmu_wss_url = 'wss://broadcastlv.chat.bilibili.com/sub'
        room_id = content.get('room_id')
        async with aiohttp.ClientSession(headers=Bilibili.headers) as session:
            if not room_id:
                async with session.get("https://api.live.bilibili.com/room/v1/Room/room_init?id=" + match1(url, r'/(\d+)'),
                                   timeout=5) as resp:
                    room_json = await resp.json()
                    room_id = room_json['data']['room_id']
            # 2025-05-29 B缁旀瑦鏌婃搴㈠付闂団偓鐟曚箘BI
            params = {
                'id': str(room_id),
                'type': '0',
                'web_location': '444.8'
            }
            wbi.sign(params)
            
            async with session.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo",params=params,
                                   timeout=5) as resp:
                danmu_info = await resp.json()
                #print(danmu_info)
                danmu_token = danmu_info['data']['token']
                try:
                    # 閸忎浇顔忓彲鑳借幏鍙栨稉宥呭煂鏉╂柨娲栭惃鍒猳st
                    danmu_host = danmu_info['data']['host_list'][0]
                    danmu_wss_url = f"wss://{danmu_host['host']}:{danmu_host['wss_port']}/sub"
                except:
                    pass

            w_data = {
                'uid': uid,
                'roomid': room_id,
                'protover': 3,
                'platform': 'web',
                'type': 2,
                'key': danmu_token,
            }

            data = json.dumps(w_data).encode('utf-8')
            # logger.info(f"danmaku auth info {data}")
            reg_datas = [(pack('>i', len(data) + 16) + b'\x00\x10\x00\x01' + pack('>i', 7) + pack('>i', 1) + data)]
        return danmu_wss_url, reg_datas

    @staticmethod
    def decode_msg(data):
        msgs = []

        def decode_packet(packet_data):
            dm_list = []
            while True:
                try:
                    packet_len, header_len, ver, op, seq = unpack('!IHHII', packet_data[0:16])
                except Exception:
                    break
                if len(packet_data) < packet_len:
                    break

                if ver == 2:
                    dm_list.extend(decode_packet(zlib.decompress(packet_data[16:packet_len])))
                elif ver == 3:
                    dm_list.extend(decode_packet(brotli.decompress(packet_data[16:packet_len])))
                elif ver == 0 or ver == 1:
                    dm_list.append({
                        'type': op,
                        'body': packet_data[16:packet_len]
                    })
                else:
                    break

                if len(packet_data) == packet_len:
                    break
                else:
                    packet_data = packet_data[packet_len:]
            return dm_list

        def bytes_serializer(obj):
            if isinstance(obj, bytes):
                return obj.decode('utf-8')
            raise TypeError("Type not serializable")

        dm_list = decode_packet(data)
        for dm in dm_list:
            try:
                msg = {}
                if dm.get('type') == 5:
                    j = json.loads(dm.get('body'))
                    msg['msg_type'] = {
                        'SEND_GIFT': 'gift',
                        'DANMU_MSG': 'danmaku',
                        'WELCOME': 'enter',
                        'NOTICE_MSG': 'broadcast',
                        'SUPER_CHAT_MESSAGE': 'super_chat',
                        'LIVE_INTERACTIVE_GAME': 'interactive_danmaku',  # 閺傛澘顤冩禍鎺戝З瀵懓绠烽敍宀€绮″ù瀣槸娑撳骸鑴婇獮鏇炲敶鐎归€涚閼?
                        'GUARD_BUY': 'guard_buy'
                    }.get(j.get('cmd'), 'other')
                    # 2021-06-03 bilibili 鐎涙顔屾洿鏂? 瑜般垹顩?DANMU_MSG:4:0:2:2:2:0
                    if msg.get('msg_type', 'UNKNOWN').startswith('DANMU_MSG'):
                        msg['msg_type'] = 'danmaku'

                    if msg['msg_type'] == 'danmaku':
                        msg['name'] = (j.get('info', ['', '', ['', '']])[2][1] or
                                       j.get('data', {}).get('uname', ''))
                        msg['uid'] = j.get('info', ['', '', ['', '']])[2][0]
                        msg['content'] = j.get('info', ['', ''])[1]
                        msg["color"] = f"{j.get('info', '16777215')[0][3]}"

                        # 閸栧搫鍨庨弰顖濄€冮幆鍛瘶鏉╂ɑ妲搁弲顕€鈧艾鑴婇獮?
                        msg_extra = json.loads(j.get('info', [['','','','','','','','','','','','','','','',{}]])[0][15].get("extra", "{}"))
                        if msg_extra.get("emoticon_unique", "") != "":
                            msg['content'] = f"鐞涖劍鍎忛妴鎭祄sg_extra['emoticon_unique']}閵?

                    elif msg['msg_type'] == 'super_chat':
                        msg['name'] = j.get('data', {}).get('user_info', {}).get('uname', "")
                        msg['uid'] = j.get('data', {}).get('uid', '')
                        msg['content'] = j.get('data', {}).get('message', '')
                        msg['price'] = int(j.get('data', {}).get('price', 0)) * 1000
                        msg['num'] = 1
                        msg['gift_name'] = "闁辨帞娲伴悾娆掆枅"

                    elif msg['msg_type'] == "guard_buy":
                        msg['name'] = j.get('data', {}).get('username', '')
                        msg['uid'] = j.get('data', {}).get('uid', '')
                        msg['gift_name'] = j.get('data', {}).get('gift_name', '')
                        msg['price'] = j.get('data', {}).get('price', '')
                        msg['num'] = j.get('data', {}).get('num', '')
                        msg['content'] = f"{msg['name']}娑撳﹣绨msg['num']}娑擃亝婀€{msg['gift_name']}"

                    elif msg['msg_type'] == 'gift':
                        msg['name'] = j.get('data', {}).get('uname', '')
                        msg['uid'] = j.get('data', {}).get('uid', '')
                        msg['gift_name'] = j.get('data', {}).get('giftName', '')
                        msg['price'] = j.get('data', {}).get('price', '')
                        msg['num'] = j.get('data', {}).get('num', '')
                        msg['content'] = f"{msg['name']}閹舵洖鏉烘禍鍞焟sg['num']}娑撶崊msg['gift_name']}"

                    elif msg['msg_type'] == 'interactive_danmaku':
                        msg['name'] = j.get('data', {}).get('uname', '')
                        msg['content'] = j.get('data', {}).get('msg', '')
                        msg["color"] = '16777215'

                    elif msg['msg_type'] == 'broadcast':
                        msg['type'] = j.get('msg_type', 0)
                        msg['roomid'] = j.get('real_roomid', 0)
                        msg['content'] = j.get('msg_common', '')
                        msg['raw'] = j
                    else:
                        msg['content'] = j
                else:
                    msg = {'name': '', 'content': dm.get('body'), 'msg_type': 'other'}
                try:
                    msg['raw_data'] = json.dumps(dm, default=bytes_serializer, ensure_ascii=False)
                except:
                    msg['raw_data'] = ""
                msgs.append(msg)
            except Exception as Error:
                logger.warning(f"{Bilibili.__name__}: 瀵懓绠烽幒銉︽暪瀵倸鐖?- {Error}")
        return msgs
