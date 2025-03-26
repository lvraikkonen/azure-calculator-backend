"""
Azure特定检索器 - 针对Azure云服务内容的优化检索
"""

from typing import List, Dict, Any, Optional
import re

from app.rag.core.interfaces import Retriever
from app.rag.core.models import TextChunk, Metadata
from app.core.logging import get_logger

logger = get_logger(__name__)

class AzureServiceRetriever(Retriever[TextChunk]):
    """Azure服务特定检索器"""
    
    def __init__(
        self,
        base_retriever: Retriever[TextChunk],
        service_terms: Optional[Dict[str, List[str]]] = None,
    ):
        """
        初始化Azure服务特定检索器
        
        Args:
            base_retriever: 基础检索器
            service_terms: 服务术语映射，例如{"VM": ["虚拟机", "Virtual Machine"]}
        """
        self.base_retriever = base_retriever
        self.service_terms = service_terms or {}
    
    async def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[TextChunk]:
        """
        检索相关内容，增强对Azure服务的理解
        
        Args:
            query: 查询文本
            limit: 返回结果数量上限
            **kwargs: 额外参数
            
        Returns:
            List[TextChunk]: 相关块列表
        """
        logger.debug(f"Azure服务检索: {query}")
        
        # 扩展查询以增强对Azure服务的理解
        enhanced_query = self._enhance_query(query)
        
        # 使用基础检索器检索
        results = await self.base_retriever.retrieve(enhanced_query, limit=limit, **kwargs)
        
        # 执行Azure特定后处理
        processed_results = self._process_azure_results(query, results)
        
        logger.debug(f"Azure服务检索结果: {len(processed_results)} 个块")
        return processed_results
    
    def _enhance_query(self, query: str) -> str:
        """增强查询，扩展Azure服务术语"""
        enhanced = query
        
        # 替换缩写
        for service, aliases in self.service_terms.items():
            if service in query:
                continue  # 服务名已经存在，不需要替换
                
            # 检查别名是否存在
            for alias in aliases:
                if re.search(rf'\b{re.escape(alias)}\b', query, re.IGNORECASE):
                    # 替换为正式服务名
                    enhanced = enhanced.replace(alias, f"{alias} ({service})")
                    break
        
        if enhanced != query:
            logger.debug(f"查询增强: '{query}' -> '{enhanced}'")
            
        return enhanced
    
    def _process_azure_results(self, query: str, results: List[TextChunk]) -> List[TextChunk]:
        """处理Azure特定结果，调整分数并优先考虑特定内容"""
        if not results:
            return []
            
        processed = []
        
        # 判断查询类型
        is_pricing_query = self._is_pricing_query(query)
        is_comparison_query = self._is_comparison_query(query)
        
        # 处理每个结果
        for chunk in results:
            # 复制一份
            processed_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=chunk.score
            )
            
            # 针对不同查询类型调整分数
            if is_pricing_query and "价格" in chunk.content:
                if processed_chunk.score is not None:
                    processed_chunk.score *= 1.2  # 提高定价内容的分数
            
            if is_comparison_query and any(term in chunk.content for term in ["比较", "对比", "vs", "versus"]):
                if processed_chunk.score is not None:
                    processed_chunk.score *= 1.15  # 提高比较内容的分数
            
            processed.append(processed_chunk)
        
        # 重新排序
        processed.sort(key=lambda x: x.score or 0, reverse=True)
        
        return processed[:len(results)]
    
    def _is_pricing_query(self, query: str) -> bool:
        """检查是否为定价查询"""
        pricing_terms = ["价格", "定价", "成本", "费用", "多少钱", "报价", "价格表"]
        return any(term in query for term in pricing_terms)
    
    def _is_comparison_query(self, query: str) -> bool:
        """检查是否为比较查询"""
        comparison_terms = ["比较", "对比", "区别", "差异", "优缺点", "vs", "versus", "哪个更好"]
        return any(term in query for term in comparison_terms)