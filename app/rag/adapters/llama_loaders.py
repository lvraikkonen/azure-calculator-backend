"""
LlamaIndex加载器适配器 - 将LlamaIndex文档加载器适配到自定义接口
"""

from typing import List, Dict, Any, Optional
import asyncio
from functools import partial

# 正确的导入路径
from llama_index.readers.web import SimpleWebPageReader
from app.rag.core.interfaces import DocumentLoader
from app.rag.core.models import Document
from app.rag.adapters.llama_converters import from_llama_document
from app.core.logging import get_logger

logger = get_logger(__name__)

class LlamaWebLoader(DocumentLoader[Document]):
    """LlamaIndex SimpleWebPageReader适配器"""
    
    def __init__(self, html_to_text: bool = True):
        self.reader = SimpleWebPageReader(html_to_text=html_to_text)
    
    async def load(self, source: str, **kwargs) -> List[Document]:
        """异步加载网页文档"""
        logger.info(f"使用LlamaIndex加载网页: {source}")
        
        try:
            # LlamaIndex加载器是同步的，使用run_in_executor运行
            loop = asyncio.get_event_loop()
            llama_docs = await loop.run_in_executor(
                None,
                partial(self.reader.load_data, [source])
            )
            
            # 转换为自定义文档
            docs = [from_llama_document(doc) for doc in llama_docs]
            logger.info(f"已加载 {len(docs)} 个文档从: {source}")
            return docs
            
        except Exception as e:
            logger.error(f"LlamaIndex加载网页失败: {source}, 错误: {str(e)}")
            raise