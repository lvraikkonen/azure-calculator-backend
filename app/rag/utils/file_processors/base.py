"""
文件处理器基础定义 - 定义处理器接口和注册表
"""
from typing import Dict, Any, Type, List, Optional, Protocol, runtime_checkable
from pathlib import Path


@runtime_checkable
class FileProcessor(Protocol):
    """文件处理器接口协议"""

    @classmethod
    def can_process(cls, file_path: Path) -> bool:
        """检查是否能处理此文件"""
        ...

    async def process(self, file_path: Path, encoding: str = 'utf-8', **kwargs) -> Dict[str, Any]:
        """处理文件内容"""
        ...


class FileProcessorRegistry:
    """文件处理器注册表"""
    _processors: List[Type[FileProcessor]] = []

    @classmethod
    def register(cls, processor: Type[FileProcessor]) -> Type[FileProcessor]:
        """注册处理器"""
        cls._processors.append(processor)
        return processor

    @classmethod
    def get_processor(cls, file_path: Path) -> Optional[Type[FileProcessor]]:
        """获取适合的处理器"""
        for processor in cls._processors:
            if processor.can_process(file_path):
                return processor
        return None