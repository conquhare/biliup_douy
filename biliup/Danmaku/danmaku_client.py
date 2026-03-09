# 弹幕客户端基类实现
# 提供统一的弹幕录制、保存接口

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger('biliup')


class BaseDanmakuClient(ABC):
    """弹幕客户端基类"""

    def __init__(self, url: str, filename: str):
        self.url = url
        self.filename = filename
        self.danmaku_list: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @abstractmethod
    async def get_ws_info(self, url: str, context: dict) -> tuple:
        """获取 WebSocket 连接信息"""
        pass

    @abstractmethod
    def decode_msg(self, data: bytes) -> tuple:
        """解码弹幕消息"""
        pass

    async def start(self):
        """启动弹幕录制"""
        if self._running:
            return
        self._running = True
        self.start_time = time.time()
        self._task = asyncio.create_task(self._run())
        logger.info(f'弹幕录制启动: {self.url}')

    async def stop(self):
        """停止弹幕录制"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f'弹幕录制停止: {self.url}, 共录制 {len(self.danmaku_list)} 条弹幕')

    def save(self, filename: str):
        """保存弹幕到文件（XML格式）"""
        if not self.danmaku_list:
            logger.warning(f'没有弹幕需要保存: {filename}')
            return

        # 保存为 XML 格式（B站弹幕格式兼容）
        self._save_as_xml(filename)

        # 同时保存为 JSON 格式便于处理
        json_filename = filename.replace('.xml', '.json')
        self._save_as_json(json_filename)

        logger.info(f'弹幕已保存: {filename} ({len(self.danmaku_list)} 条)')

    def _save_as_xml(self, filename: str):
        """保存为 XML 格式（兼容 B 站弹幕格式）"""
        root = ET.Element('i')
        root.set('chatserver', 'chat.bilibili.com')
        root.set('chatid', '0')
        root.set('mission', '0')
        root.set('maxlimit', '1000')
        root.set('state', '0')
        root.set('real_name', '0')
        root.set('platform', 'biliup')

        for danmaku in self.danmaku_list:
            d = ET.SubElement(root, 'd')
            # p 属性: 时间,模式,字号,颜色,发送时间,池,用户ID,rowID
            timestamp = danmaku.get('timestamp', 0)
            content = danmaku.get('content', '')
            color = danmaku.get('color', '16777215')
            name = danmaku.get('name', '匿名')

            p_attr = f"{timestamp:.3f},1,25,{color},{int(time.time())},0,0,0"
            d.set('p', p_attr)
            d.text = content

        # 格式化 XML
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        # 写入文件
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(pretty_xml)

    def _save_as_json(self, filename: str):
        """保存为 JSON 格式"""
        data = {
            'url': self.url,
            'start_time': self.start_time,
            'end_time': time.time(),
            'count': len(self.danmaku_list),
            'danmaku_list': self.danmaku_list
        }

        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _run(self):
        """运行弹幕录制循环"""
        try:
            context = {'url': self.url}
            ws_url, reg_datas = await self.get_ws_info(self.url, context)

            import websockets

            async with websockets.connect(ws_url) as websocket:
                # 发送注册数据
                if reg_datas:
                    for data in reg_datas:
                        await websocket.send(data)

                # 启动心跳任务
                heartbeat_task = asyncio.create_task(self._heartbeat(websocket))

                while self._running:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), timeout=30)
                        msgs, ack = self.decode_msg(data)

                        # 发送确认包
                        if ack:
                            await websocket.send(ack)

                        # 处理弹幕消息
                        for msg in msgs:
                            await self._process_message(msg)

                    except asyncio.TimeoutError:
                        logger.debug('弹幕接收超时')
                        continue
                    except Exception as e:
                        logger.exception(f'弹幕处理错误: {e}')
                        await asyncio.sleep(1)

                heartbeat_task.cancel()

        except Exception as e:
            logger.exception(f'弹幕录制错误: {e}')

    async def _heartbeat(self, websocket):
        """发送心跳包"""
        try:
            while self._running:
                if hasattr(self, 'heartbeat') and self.heartbeat:
                    await websocket.send(self.heartbeat)
                await asyncio.sleep(getattr(self, 'heartbeatInterval', 30))
        except Exception as e:
            logger.debug(f'心跳错误: {e}')

    async def _process_message(self, msg: dict):
        """处理弹幕消息"""
        if msg.get('msg_type') == 'danmaku':
            # 添加时间戳
            msg['timestamp'] = time.time() - self.start_time
            self.danmaku_list.append(msg)

            # 调试日志
            if len(self.danmaku_list) % 100 == 0:
                logger.debug(f'已录制 {len(self.danmaku_list)} 条弹幕')


class IDanmakuClient:
    """弹幕客户端接口（用于类型注解）"""
    pass
