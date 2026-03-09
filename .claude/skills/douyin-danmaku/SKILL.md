---
name: "douyin-danmaku"
description: "抖音直播弹幕录制开发指南，包含 WebSocket 连接、签名计算和 protobuf 解析"
---

# 抖音弹幕录制开发技能

## 适用场景

**当需要以下操作时使用此技能：**
1. 开发或修复抖音弹幕录制功能
2. 理解抖音直播 WebSocket 连接机制
3. 调试抖音弹幕连接问题
4. 更新签名算法（signature 计算）
5. 解析抖音 protobuf 弹幕数据

## 核心架构

### 文件结构
```
biliup/Danmaku/
├── douyin.py              # 主弹幕录制类
├── douyin_util/
│   ├── __init__.py        # 工具函数导出
│   ├── dy_pb2.py          # Protobuf 定义（自动生成）
│   ├── webmssdk.js        # 签名计算 JS 库
│   └── douyin_util.py     # 辅助工具函数
```

### 关键类：Douyin

```python
class Douyin:
    heartbeat = b':\x02hb'           # WebSocket 心跳包
    heartbeatInterval = 10            # 心跳间隔（秒）
```

## WebSocket 连接流程

### 1. 获取连接信息（get_ws_info）

```python
@staticmethod
async def get_ws_info(url, context):
    # 构建请求头
    headers = {
        'Referer': 'https://live.douyin.com/',
        'Cookie': context['config'].get('user', {}).get('douyin_cookie', '')
    }
    
    # 获取/生成 ttwid
    if "ttwid" not in headers['Cookie']:
        headers['Cookie'] = f'ttwid={DouyinUtils.get_ttwid()};{headers["Cookie"]}'
    
    # 生成签名参数
    sig_params = {
        "live_id": "1",
        "aid": "6383",
        "version_code": 180800,
        "webcast_sdk_version": "1.0.14-beta.0",
        "room_id": context['room_id'],
        # ... 其他参数
    }
    
    # 计算签名
    signature = DouyinDanmakuUtils.get_signature(
        DouyinDanmakuUtils.get_x_ms_stub(sig_params)
    )
    
    # 构建 WebSocket URL
    wss_url = f"wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/?..."
    return wss_url, []
```

**关键参数说明：**
- `version_code`: 180800（从抖音 JS 文件获取）
- `webcast_sdk_version`: "1.0.14-beta.0"
- `user_unique_id`: 随机生成的用户 ID
- `signature`: 通过 webmssdk.js 计算的签名

### 2. 签名计算

签名计算使用 `webmssdk.js` 库：

```python
# douyin_util/__init__.py
import execjs
import os

# 加载 webmssdk.js
js_path = os.path.join(os.path.dirname(__file__), 'webmssdk.js')
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# 编译 JS
ctx = execjs.compile(js_content)

# 调用签名函数
signature = ctx.call('get_sign', x_ms_stub)
```

**更新签名算法时：**
1. 从抖音网页版获取最新 `webmssdk.js`
2. 替换 `douyin_util/webmssdk.js`
3. 测试签名是否有效

### 3. 消息解码（decode_msg）

抖音使用 protobuf 格式传输弹幕数据：

```python
@staticmethod
def decode_msg(data):
    # 解析外层 PushFrame
    wss_package = PushFrame()
    wss_package.ParseFromString(data)
    log_id = wss_package.logId
    
    # gzip 解压 payload
    decompressed = gzip.decompress(wss_package.payload)
    
    # 解析 Response
    payload_package = Response()
    payload_package.ParseFromString(decompressed)
    
    # 处理需要确认的消息
    if payload_package.needAck:
        ack = PushFrame()
        ack.payloadType = 'ack'
        ack.logId = log_id
        # ... 构建 ack 包
    
    # 遍历消息列表
    for msg in payload_package.messages:
        # 根据方法名处理不同类型的消息
        if msg.method == 'WebcastChatMessage':
            # 普通弹幕
            chat_msg = ChatMessage()
            chat_msg.ParseFromString(msg.payload)
            # 提取弹幕内容
        elif msg.method == 'WebcastGiftMessage':
            # 礼物消息
            pass
        elif msg.method == 'WebcastLikeMessage':
            # 点赞消息
            pass
```

**常见消息类型：**
- `WebcastChatMessage` - 普通弹幕
- `WebcastGiftMessage` - 礼物
- `WebcastLikeMessage` - 点赞
- `WebcastMemberMessage` - 进入直播间
- `WebcastSocialMessage` - 关注消息

## 调试技巧

### 1. 检查 WebSocket 连接

```python
# 在 get_ws_info 中添加日志
logger.info(f"WebSocket URL: {wss_url}")
logger.info(f"Signature: {signature}")
logger.info(f"User Unique ID: {USER_UNIQUE_ID}")
```

### 2. 捕获原始数据

```python
# 在 decode_msg 中保存原始数据
with open('debug_douyin.bin', 'wb') as f:
    f.write(data)
```

### 3. 验证签名

```python
# 对比网页版生成的签名
# 在浏览器控制台执行：
# window.byted_acrawler && window.byted_acrawler.sign({...})
```

## 常见问题

### Q1: 连接后立即断开
**原因**：签名过期或无效  
**解决**：更新 `webmssdk.js` 或检查参数

### Q2: 收到消息但无法解析
**原因**：protobuf 定义不匹配  
**解决**：从抖音获取最新的 `.proto` 文件重新生成

### Q3: 弹幕内容为空
**原因**：gzip 解压失败  
**解决**：检查 `compress` 参数是否为 'gzip'

### Q4: 签名计算失败
**原因**：execjs 环境问题  
**解决**：安装 Node.js，确保 `execjs.get().name` 返回 node

## 更新流程

当抖音更新接口时：

1. **获取最新 JS 文件**
   - 打开抖音直播页面
   - 在 Network 面板找到 `webmssdk.js`
   - 保存到 `douyin_util/webmssdk.js`

2. **更新版本号**
   - 在抖音 JS 文件中搜索 `version_code`
   - 更新 `get_ws_info` 中的 `VERSION_CODE`

3. **测试连接**
   ```bash
   python -m biliup.Danmaku.douyin
   ```

4. **验证弹幕接收**
   - 检查日志输出
   - 确认各类型消息正常解析

## 相关文件

- `biliup/Danmaku/douyin.py` - 主实现
- `biliup/Danmaku/douyin_util/webmssdk.js` - 签名库
- `biliup/plugins/douyin.py` - 直播流获取（共享工具函数）

## 参考资源

- 原始参考：[stream-rec](https://github.com/hua0512/stream-rec)
- Protobuf 定义：从抖音 JS 逆向获取
