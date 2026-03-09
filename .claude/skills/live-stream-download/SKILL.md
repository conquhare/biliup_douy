---
name: "live-stream-download"
description: "直播流下载引擎开发指南，包含多平台适配、分段录制和下载管理"
---

# 直播流下载引擎开发技能

## 适用场景

**当需要以下操作时使用此技能：**
1. 开发新的直播平台下载插件
2. 修复现有平台的下载问题
3. 理解下载引擎架构
4. 调试下载失败问题
5. 实现分段录制功能

## 核心架构

### 文件结构
```
biliup/engine/
├── download.py           # 下载引擎基类
├── sync_downloader.py    # 同步下载器
├── decorators.py         # 下载装饰器
└── ...

biliup/plugins/
├── douyin.py            # 抖音下载插件
├── bilibili.py          # B站下载插件
├── huya.py              # 虎牙下载插件
├── douyu.py             # 斗鱼下载插件
└── ...
```

### 下载流程

```
1. 检测直播状态 (check_stream)
   ↓
2. 获取直播流地址 (get_stream_url)
   ↓
3. 启动下载 (start_download)
   ↓
4. 分段/持续下载 (download_segment)
   ↓
5. 处理下载完成 (on_download_finished)
```

## 开发新平台插件

### 1. 继承基类

```python
from biliup.engine.download import DownloadBase

class MyPlatform(DownloadBase):
    def __init__(self, fname, url, suffix='flv'):
        super().__init__(fname, url, suffix)
        self.platform = "myplatform"
```

### 2. 实现检测方法

```python
async def check_stream(self):
    """
    检测直播间是否在线
    
    Returns:
        bool: True 表示正在直播，False 表示未直播
    """
    logger.info(f"检测 {self.url}")
    
    # 发送 HTTP 请求获取直播间信息
    async with aiohttp.ClientSession() as session:
        async with session.get(self.url, headers=self.headers) as resp:
            html = await resp.text()
            
            # 解析直播状态
            if '"status":1' in html:
                self.room_title = self._extract_title(html)
                self.raw_stream_url = self._extract_stream_url(html)
                return True
            else:
                logger.debug("未检测到直播")
                return False
```

### 3. 获取流地址

```python
def get_stream_url(self):
    """
    获取直播流地址
    
    Returns:
        str: 直播流 URL
    """
    # 可能需要处理重定向或选择清晰度
    return self.raw_stream_url
```

### 4. 处理下载

```python
async def start_download(self):
    """
    开始下载直播流
    """
    stream_url = self.get_stream_url()
    output_file = f"{self.fname}_{time.strftime('%Y%m%d_%H%M%S')}.{self.suffix}"
    
    # 使用 ffmpeg 或 streamlink 下载
    cmd = [
        'ffmpeg',
        '-i', stream_url,
        '-c', 'copy',
        '-f', self.suffix,
        output_file
    ]
    
    self.proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await self.proc.wait()
```

## 分段录制

### 时间分段

```python
# 在配置中设置分段时长（秒）
segment_time = 3600  # 1小时

# ffmpeg 参数
cmd = [
    'ffmpeg',
    '-i', stream_url,
    '-c', 'copy',
    '-f', 'segment',
    '-segment_time', str(segment_time),
    '-reset_timestamps', '1',
    f"{self.fname}_%03d.{self.suffix}"
]
```

### 大小分段

```python
segment_size = 1024 * 1024 * 1024  # 1GB

cmd = [
    'ffmpeg',
    '-i', stream_url,
    '-c', 'copy',
    '-f', 'segment',
    '-segment_size', str(segment_size),
    f"{self.fname}_%03d.{self.suffix}"
]
```

## 下载引擎基类

### 核心属性

```python
class DownloadBase:
    def __init__(self, fname, url, suffix='flv'):
        self.fname = fname          # 文件名前缀
        self.url = url              # 直播间 URL
        self.suffix = suffix        # 文件后缀 (flv/mp4)
        self.room_title = None      # 直播间标题
        self.raw_stream_url = None  # 原始流地址
        self.proc = None            # 下载进程
```

### 装饰器

```python
from biliup.engine.decorators import Plugin

@Plugin.download(regexp=r'https?://live\.douyin\.com/')
class Douyin(DownloadBase):
    """抖音下载插件"""
    pass
```

## 调试技巧

### 1. 检查流地址

```python
# 在 check_stream 中添加
logger.info(f"Stream URL: {self.raw_stream_url}")
```

### 2. 测试 ffmpeg 命令

```bash
# 手动测试下载
ffmpeg -i "流地址" -c copy -t 10 test.mp4
```

### 3. 检查 HTTP 响应

```python
# 保存响应内容
async with session.get(url) as resp:
    with open('debug.html', 'w') as f:
        f.write(await resp.text())
```

### 4. 监控下载进程

```python
# 实时输出 ffmpeg 日志
async def read_stream(stream, prefix):
    while True:
        line = await stream.readline()
        if not line:
            break
        logger.debug(f"{prefix}: {line.decode().strip()}")

# 启动读取任务
asyncio.create_task(read_stream(self.proc.stdout, "FFMPEG"))
asyncio.create_task(read_stream(self.proc.stderr, "FFMPEG_ERR"))
```

## 常见问题

### Q1: 403 Forbidden
**原因**：流地址需要 Referer 或 Cookie  
**解决**：
```python
headers = {
    'Referer': 'https://live.platform.com/',
    'User-Agent': 'Mozilla/5.0...'
}
```

### Q2: 下载中断后无法恢复
**原因**：流地址过期  
**解决**：在下载循环中定期刷新流地址

### Q3: 文件损坏
**原因**：直接终止 ffmpeg  
**解决**：发送 SIGINT 信号让 ffmpeg 正常退出
```python
self.proc.send_signal(signal.SIGINT)
await asyncio.wait_for(self.proc.wait(), timeout=5)
```

### Q4: 内存占用过高
**原因**：ffmpeg 缓冲区过大  
**解决**：添加 `-thread_queue_size 1024` 参数

## 平台适配要点

| 平台 | 特点 | 注意事项 |
|------|------|----------|
| 抖音 | 签名验证 | 需要计算 signature |
| B站 | 多清晰度 | 需要处理 qn 参数 |
| 虎牙 | CDN 选择 | 支持多种 CDN 线路 |
| 斗鱼 | 房间号转换 | 短号转长号 |
| Twitch | 广告插入 | 需要处理广告分段 |

## 相关文件

- `biliup/engine/download.py` - 下载基类
- `biliup/engine/sync_downloader.py` - 同步下载器
- `biliup/plugins/` - 各平台实现

## 测试方法

```python
# 测试单个插件
from biliup.plugins.douyin import Douyin

downloader = Douyin("test", "https://live.douyin.com/xxxx")
result = await downloader.check_stream()
print(f"Live: {result}")
if result:
    print(f"Stream URL: {downloader.raw_stream_url}")
```
