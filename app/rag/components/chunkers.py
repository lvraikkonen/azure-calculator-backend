"""
文本分块器组件 - 将文档分割为可管理的块
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import ContentProcessor
from app.rag.core.models import Document, TextChunk
from app.core.logging import get_logger
import uuid

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.CHUNKER, "sentence_window")
class SentenceWindowChunker(ContentProcessor[Document, TextChunk]):
    """句子窗口分块器 - 使用滑动窗口分割文档"""
    
    def __init__(
        self, 
        chunk_size: int = 1024, 
        chunk_overlap: int = 200,
        window_metadata_key: str = "window",
        original_text_metadata_key: str = "original_text"
    ):
        """
        初始化句子窗口分块器
        
        Args:
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            window_metadata_key: 窗口元数据键
            original_text_metadata_key: 原始文本元数据键
        """
        from llama_index.core.node_parser import SentenceWindowNodeParser
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.window_metadata_key = window_metadata_key
        self.original_text_metadata_key = original_text_metadata_key
        
        self.parser = SentenceWindowNodeParser.from_defaults(
            window_size=chunk_size,
            window_metadata_key=window_metadata_key,
            original_text_metadata_key=original_text_metadata_key
        )
    
    async def process(self, documents: List[Document], **kwargs) -> List[TextChunk]:
        """
        处理文档列表，返回文本块
        
        Args:
            documents: 要处理的文档列表
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 处理后的文本块列表
        """
        from app.rag.adapters.llama_converters import to_llama_document, from_llama_node
        
        chunks = []
        
        try:
            # 将自定义文档转换为LlamaIndex文档
            llama_docs = [to_llama_document(doc) for doc in documents]
            
            # 使用解析器获取节点
            llama_nodes = self.parser.get_nodes_from_documents(llama_docs)
            
            # 将LlamaIndex节点转换为自定义块
            for node in llama_nodes:
                # 找到对应的文档
                doc_id = node.metadata.get("doc_id", "unknown")
                
                # 创建块
                chunk = TextChunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=node.text,
                    metadata=from_llama_node(node).metadata,
                    embedding=node.embedding
                )
                
                chunks.append(chunk)
                
            logger.debug(f"分块器生成了 {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"文档分块失败: {str(e)}")
            raise

@register_component(RAGComponentRegistry.CHUNKER, "semantic")
class SemanticChunker(ContentProcessor[Document, TextChunk]):
    """语义分块器 - 基于语义边界分割文档"""
    
    def __init__(self, min_chunk_size: int = 256, max_chunk_size: int = 1024, buffer_size: int = 50):
        """
        初始化语义分块器
        
        Args:
            min_chunk_size: 最小块大小
            max_chunk_size: 最大块大小
            buffer_size: 缓冲区大小
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.buffer_size = buffer_size
        
    async def process(self, documents: List[Document], **kwargs) -> List[TextChunk]:
        """
        处理文档列表，返回文本块
        
        Args:
            documents: 要处理的文档列表
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 处理后的文本块列表
        """
        chunks = []
        
        try:
            for doc in documents:
                # 分割文本
                text_chunks = self._semantic_split(doc.content)
                
                # 创建块
                for i, chunk_text in enumerate(text_chunks):
                    chunk = TextChunk(
                        id=f"{doc.id}_chunk_{i+1}",
                        doc_id=doc.id,
                        content=chunk_text,
                        metadata=doc.metadata
                    )
                    chunks.append(chunk)
            
            logger.debug(f"语义分块器生成了 {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"语义分块失败: {str(e)}")
            raise
            
    def _semantic_split(self, text: str) -> List[str]:
        """
        基于语义边界分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[str]: 分割后的文本块
        """
        import re
        
        # 定义可能的语义边界
        boundaries = [
            r"\n## ", # Markdown 二级标题
            r"\n\n",  # 双空行
            r"\. ",   # 句号后跟空格
            r"\? ",   # 问号后跟空格
            r"\! ",   # 感叹号后跟空格
            r": ",    # 冒号后跟空格
            r"; "     # 分号后跟空格
        ]
        
        # 合并正则表达式
        pattern = "|".join([re.escape(b) for b in boundaries])
        
        # 分割文本
        splits = re.split(f"({pattern})", text)
        
        # 重新组合分割，保留分隔符
        result = []
        current_chunk = ""
        
        for i in range(0, len(splits), 2):
            part = splits[i]
            delimiter = splits[i+1] if i+1 < len(splits) else ""
            
            # 检查当前块大小
            if len(current_chunk) + len(part) + len(delimiter) <= self.max_chunk_size:
                # 添加到当前块
                current_chunk += part + delimiter
            else:
                # 当前块已满，检查是否达到最小大小
                if len(current_chunk) >= self.min_chunk_size:
                    # 存储当前块并开始新块
                    result.append(current_chunk)
                    current_chunk = part + delimiter
                else:
                    # 当前块太小，继续添加
                    current_chunk += part + delimiter
        
        # 添加最后一个块
        if current_chunk:
            result.append(current_chunk)
            
        return result