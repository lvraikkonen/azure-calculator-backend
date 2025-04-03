from typing import Dict, Any, Optional
from pathlib import Path
import json
import aiofiles
from app.rag.utils.file_processors.base import FileProcessorRegistry

from app.core.logging import get_logger

logger = get_logger(__name__)


# 基础处理器实现
@FileProcessorRegistry.register
class TextFileProcessor:
    """文本文件处理器"""

    @classmethod
    def can_process(cls, file_path: Path) -> bool:
        suffix = file_path.suffix.lower()
        return suffix in [".txt", ".md", ".py", ".js", ".html", ".css", ".csv", ".json", ".xml", ".yaml", ".yml"]

    async def process(self, file_path: Path, encoding: str = 'utf-8', **kwargs) -> Dict[str, Any]:
        try:
            async with aiofiles.open(file_path, mode='r', encoding=encoding) as f:
                content = await f.read()

            # 提取额外元数据
            metadata = {}

            # 对于Markdown文件，尝试提取标题
            if file_path.suffix.lower() == '.md':
                title = self._extract_markdown_title(content)
                if title:
                    metadata["title"] = title

            # 对于JSON文件，检查文件结构
            elif file_path.suffix.lower() == '.json':
                metadata["json_structure"] = self._analyze_json_structure(content)

            return {
                "content": content,
                "metadata": metadata
            }
        except UnicodeDecodeError:
            logger.warning(f"编码错误，尝试检测编码: {file_path}")
            # 尝试检测编码
            encoding = kwargs.get("fallback_encoding", "latin-1")
            async with aiofiles.open(file_path, mode='r', encoding=encoding) as f:
                content = await f.read()
            return {"content": content, "metadata": {"encoding_fallback": True}}

    def _extract_markdown_title(self, content: str) -> Optional[str]:
        """从Markdown内容中提取标题"""
        lines = content.split('\n')
        for line in lines:
            # 检查一级标题格式
            if line.startswith('# '):
                return line[2:].strip()
        return None

    def _analyze_json_structure(self, content: str) -> Dict[str, Any]:
        """分析JSON结构"""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return {"type": "array", "length": len(data)}
            elif isinstance(data, dict):
                return {"type": "object", "keys": list(data.keys())[:10]}  # 仅返回前10个键
            else:
                return {"type": "primitive", "value_type": type(data).__name__}
        except:
            return {"type": "invalid"}
