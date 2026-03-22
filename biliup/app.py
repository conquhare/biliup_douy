"""
biliup.app - 应用程序上下文模块

提供全局上下文对象，用于存储应用程序级别的共享数据。
"""

from threading import Lock

class ContextDict(dict):
    """线程安全的上下文字典"""
    def __init__(self):
        super().__init__()
        self._lock = Lock()

    def __setitem__(self, key, value):
        with self._lock:
            super().__setitem__(key, value)

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def get(self, key, default=None):
        with self._lock:
            return super().get(key, default)

context = ContextDict()

# 初始化 sync_downloader_map 用于存储同步下载器状态
context["sync_downloader_map"] = {}
