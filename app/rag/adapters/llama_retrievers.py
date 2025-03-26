"""
LlamaIndex检索器适配器 - 将LlamaIndex检索器适配到自定义接口
"""

from typing import List, Dict, Any, Optional, cast

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore
from llama_index.core.retrievers import VectorIndexRetriever

from app.rag.core.interfaces import Retriever
from app.rag.core.models import TextChunk
from app.rag.adapters.llama_converters import from_llama_nodes
from app.core.logging import get_logger

logger = get_logger(__name__)

class LlamaVectorRetriever(Retriever[TextChunk]):
    """LlamaIndex向量检索器适配器"""
    
    def __init__(
        self, 
        index: VectorStoreIndex,
        similarity_top_k: int = 5,
        score_threshold: Optional[float] = None,
    ):
        """
        初始化LlamaIndex向量检索器适配器
        
        Args:
            index: LlamaIndex向量索引
            similarity_top_k: 返回的最大结果数
            score_threshold: 相似度阈值，低于该阈值的结果将被过滤
        """
        self.index = index
        self.retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k,
        )
        self.score_threshold = score_threshold
    
    async def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[TextChunk]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            limit: 返回结果数量上限
            **kwargs: 额外参数
            
        Returns:
            List[TextChunk]: 相关块列表
        """
        logger.debug(f"LlamaIndex向量检索: {query}")
        
        try:
            # 覆盖default_similarity_top_k
            if limit != self.retriever.similarity_top_k:
                self.retriever.similarity_top_k = limit
            
            # LlamaIndex检索器是异步的
            nodes = await self.retriever.aretrieve(query)
            
            # 转换为自定义块
            chunks = from_llama_nodes(nodes)
            
            # 应用分数阈值
            if self.score_threshold is not None:
                chunks = [
                    chunk for chunk in chunks 
                    if chunk.score is not None and chunk.score >= self.score_threshold
                ]
            
            logger.debug(f"LlamaIndex向量检索结果: {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"LlamaIndex向量检索失败: {str(e)}")
            raise