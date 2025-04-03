from typing import Optional

from pathlib import Path
from app.rag.core.models import Document, Metadata
from app.rag.utils.file_processors.base import FileProcessor, FileProcessorRegistry


class ProcessorFactory:
    """处理器工厂类"""

    @staticmethod
    def create_processor(file_path: Path) -> Optional[FileProcessor]:
        """创建适合的处理器实例"""
        processor_class = FileProcessorRegistry.get_processor(file_path)
        if processor_class:
            return processor_class()
        return None


# 实现缓存系统
class DocumentCache:
    """文档缓存系统"""
    _cache = {}
    _max_size = 100  # 最大缓存数量

    @classmethod
    def set_max_size(cls, size: int):
        """设置最大缓存大小"""
        cls._max_size = size

    @classmethod
    def get(cls, key: str) -> Optional[Document]:
        """获取缓存文档"""
        return cls._cache.get(key)

    @classmethod
    def set(cls, key: str, document: Document):
        """缓存文档"""
        # 如果缓存已满，删除最旧的缓存
        if len(cls._cache) >= cls._max_size:
            oldest_key = next(iter(cls._cache))
            del cls._cache[oldest_key]

        cls._cache[key] = document

    @classmethod
    def clear(cls):
        """清空缓存"""
        cls._cache.clear()

    @classmethod
    def invalidate(cls, key: str):
        """使指定缓存失效"""
        if key in cls._cache:
            del cls._cache[key]
