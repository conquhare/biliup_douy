---
name: "bilibili-upload"
description: "B站视频上传开发指南，包含分P上传、线路选择和投稿接口"
---

# B站视频上传技能

## 适用场景

**当需要以下操作时使用此技能：**
1. 开发或修复 B站上传功能
2. 理解分P上传流程
3. 调试上传失败问题
4. 选择最优上传线路
5. 实现投稿接口

## 核心架构

### 上传流程

```
1. 预上传（获取 upload_id）
   ↓
2. 分片上传（逐片上传视频数据）
   ↓
3. 合并分片
   ↓
4. 投稿（提交视频信息）
```

### 文件结构

```
biliup/plugins/
├── bili_web.py          # B站 Web 上传
├── biliuprs.py          # biliup-rs 上传
└── ...

biliup/uploader.py       # 上传管理
```

## 上传方式

### 方式1：Web 上传（bili_web）

```python
from biliup.plugins.bili_web import BiliWeb

uploader = BiliWeb(
    video_path="video.mp4",
    title="视频标题",
    desc="视频描述",
    tid=21,  # 分区 ID
    tags=["标签1", "标签2"]
)

# 执行上传
result = await uploader.upload()
```

### 方式2：biliup-rs（推荐）

使用 Rust 实现的高效上传：

```python
from biliup.plugins.biliuprs import BiliUpRs

uploader = BiliUpRs(
    video_path="video.mp4",
    title="视频标题",
    desc="视频描述"
)

result = await uploader.upload()
```

## 分P上传

### 多P视频

```python
videos = [
    {"path": "part1.mp4", "title": "第一P"},
    {"path": "part2.mp4", "title": "第二P"},
    {"path": "part3.mp4", "title": "第三P"}
]

uploader = BiliWeb(
    videos=videos,
    title="合集标题",
    desc="合集描述"
)
```

### 追加分P

```python
# 在已有视频上追加分P
uploader = BiliWeb(
    videos=[{"path": "new_part.mp4", "title": "新分P"}],
    bvid="BV1xx411c7mD",  # 已有视频的 BV 号
    title="原标题"
)
```

## 线路选择

### 上传线路

B站支持多条上传线路：

```python
# 线路配置
lines = {
    'bda2': '百度线路',
    'qn': '七牛线路',
    'ws': '网宿线路',
    'bldsa': 'B站自建线路'
}

# 自动选择最优线路
uploader = BiliWeb(
    video_path="video.mp4",
    line='auto'  # 自动选择
)
```

### 线路测速

```python
async def test_line_speed(line):
    """测试线路速度"""
    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get(line['probe_url']) as resp:
            await resp.read()
    return time.time() - start

# 选择最快的线路
best_line = min(lines, key=test_line_speed)
```

## 投稿参数

### 必填参数

```python
params = {
    'title': '视频标题',           # 标题（最多80字符）
    'desc': '视频描述',            # 简介
    'tid': 21,                     # 分区 ID
    'tags': ['标签1', '标签2'],     # 标签（至少1个）
    'copyright': 1,                # 1=原创, 2=转载
    'source': ''                   # 转载来源（copyright=2时必填）
}
```

### 选填参数

```python
params = {
    'dynamic': '',                 # 动态内容
    'cover': 'cover.jpg',          # 封面路径
    'dtime': 0,                    # 定时发布时间（时间戳）
    'open_elec': 0,                # 是否开启充电
    'no_reprint': 1,               # 禁止转载
    'open_subtitle': 0,            # 开启字幕
}
```

### 分区 ID 参考

| 分区 | ID | 说明 |
|------|-----|------|
| 动画 | 1 | 综合 |
| 游戏 | 4 | 综合 |
| 知识 | 36 | 科学科普 |
| 科技 | 188 | 数码 |
| 音乐 | 3 | 综合 |
| 舞蹈 | 129 | 综合 |
| 生活 | 21 | 日常 |
| 鬼畜 | 119 | 综合 |
| 时尚 | 155 | 综合 |
| 娱乐 | 5 | 综合 |
| 影视 | 181 | 综合 |

## 调试技巧

### 1. 检查登录状态

```python
from biliup.common.util import check_login

if not await check_login():
    logger.error("未登录或登录已过期")
    return
```

### 2. 查看上传进度

```python
# 在分片上传中添加进度回调
async def on_progress(uploaded, total):
    percent = uploaded / total * 100
    logger.info(f"上传进度: {percent:.1f}%")

uploader = BiliWeb(
    video_path="video.mp4",
    progress_callback=on_progress
)
```

### 3. 保存上传日志

```python
# 记录完整的上传请求和响应
import json

with open('upload_log.json', 'w') as f:
    json.dump({
        'request': upload_request,
        'response': upload_response
    }, f, indent=2)
```

### 4. 测试分片上传

```bash
# 手动测试单个分片上传
curl -X POST \
  -H "Cookie: SESSDATA=xxx" \
  -F "file=@chunk_0.bin" \
  "https://upos-sz-upcdnbda2.bilivideo.com/..."
```

## 常见问题

### Q1: 上传失败 "Preupload error"
**原因**：登录过期或 Cookie 无效  
**解决**：更新 SESSDATA 和 bili_jct

### Q2: "Request Entity Too Large"
**原因**：分片大小超过限制  
**解决**：减小分片大小（默认 8MB，建议 4-6MB）

### Q3: 合并分片失败
**原因**：分片上传不完整  
**解决**：检查所有分片是否上传成功，重试失败的分片

### Q4: 投稿后视频不可见
**原因**：稿件被审核或设置错误  
**解决**：检查投稿参数，确认分区正确

### Q5: 上传速度很慢
**原因**：线路选择不当  
**解决**：尝试切换线路（qn/ws/bda2）

## 高级功能

### 自动换源

```python
# 上传高清版本替换原有视频
uploader = BiliWeb(
    video_path="hd_version.mp4",
    bvid="BV1xx411c7mD",
    replace=True  # 替换原有视频
)
```

### 多线程上传

```python
# 同时上传多个视频
import asyncio

uploaders = [
    BiliWeb(f"video{i}.mp4", title=f"视频{i}")
    for i in range(5)
]

results = await asyncio.gather(*[u.upload() for u in uploaders])
```

### 断点续传

```python
# 保存上传进度
upload_state = {
    'upload_id': 'xxx',
    'uploaded_chunks': [0, 1, 2],
    'total_chunks': 10
}

# 恢复上传
uploader = BiliWeb(
    video_path="video.mp4",
    resume_state=upload_state
)
```

## 相关文件

- `biliup/plugins/bili_web.py` - Web 上传实现
- `biliup/plugins/biliuprs.py` - biliup-rs 上传
- `biliup/uploader.py` - 上传管理器

## 参考资源

- B站投稿 API 文档（逆向获取）
- biliup-rs 项目：[biliup/biliup-rs](https://github.com/biliup/biliup-rs)
