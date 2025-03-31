"""
检索器组件 - 检索相关内容
"""
from typing import List, Dict, Any, Optional, Type, Union
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import Retriever, VectorStore
from app.rag.core.models import TextChunk
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.RETRIEVER, "vector")
class VectorRetriever(Retriever[TextChunk]):
    """向量检索器 - 基于向量相似度检索内容"""
    
    def __init__(
        self, 
        vector_store: VectorStore,
        embedding_provider: Any,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ):
        """
        初始化向量检索器
        
        Args:
            vector_store: 向量存储
            embedding_provider: 嵌入提供者
            top_k: 返回结果数量
            score_threshold: 相似度阈值
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.top_k = top_k
        self.score_threshold = score_threshold
    
    async def retrieve(self, query: str, limit: int = None, **kwargs) -> List[TextChunk]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            limit: 结果数量限制，覆盖top_k
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 检索结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用传入的limit或默认的top_k
            k = limit if limit is not None else self.top_k
            
            # 获取查询嵌入
            query_embedding = await self.embedding_provider.get_embedding(query)
            
            # 执行向量搜索
            results = await self.vector_store.search(
                query_embedding, 
                limit=k,
                **kwargs
            )
            
            # 应用得分阈值
            if self.score_threshold is not None:
                results = [
                    result for result in results 
                    if result.score is None or result.score >= self.score_threshold
                ]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"向量检索耗时: {elapsed:.3f}秒, 返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            raise

@register_component(RAGComponentRegistry.RETRIEVER, "keyword")
class KeywordRetriever(Retriever[TextChunk]):
    """关键词检索器 - 基于关键词匹配检索内容"""
    
    def __init__(
        self, 
        vector_store: VectorStore,  # 仍然需要向量存储获取全部文档
        top_k: int = 5,
    ):
        """
        初始化关键词检索器
        
        Args:
            vector_store: 向量存储，用于获取所有文档
            top_k: 返回结果数量
        """
        self.vector_store = vector_store
        self.top_k = top_k
        self.documents_cache = {}  # 简单的文档缓存
    
    async def retrieve(self, query: str, limit: int = None, **kwargs) -> List[TextChunk]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            limit: 结果数量限制，覆盖top_k
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 检索结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用传入的limit或默认的top_k
            k = limit if limit is not None else self.top_k
            
            # 生成查询关键词
            keywords = self._extract_keywords(query)
            
            # 获取所有文档
            # 实际实现应该使用更高效的方法，如倒排索引
            # 这里使用简单实现作为示例
            chunks = await self._get_chunks()
            
            # 基于关键词匹配计算得分
            scored_chunks = []
            for chunk in chunks:
                score = self._compute_keyword_score(chunk.content, keywords)
                
                # 创建得分副本
                scored_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=score
                )
                
                scored_chunks.append(scored_chunk)
            
            # 按得分排序
            scored_chunks.sort(key=lambda x: x.score or 0, reverse=True)
            
            # 取top k结果
            results = scored_chunks[:k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"关键词检索耗时: {elapsed:.3f}秒, 返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"关键词检索失败: {str(e)}")
            raise
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        从查询中提取关键词
        
        Args:
            query: 查询文本
            
        Returns:
            List[str]: 关键词列表
        """
        # 简单实现：分词并去除停用词
        import re
        
        # 分词
        words = re.findall(r'\b\w+\b', query.lower())
        
        # 停用词（简化版）
        stopwords = {"and", "or", "the", "a", "an", "is", "are", "in", "on", "at", "to", "for", "with", "by", "about", "like", "of"}
        
        # 过滤停用词
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords
    
    def _compute_keyword_score(self, text: str, keywords: List[str]) -> float:
        """
        计算文本与关键词的匹配得分
        
        Args:
            text: 文本内容
            keywords: 关键词列表
            
        Returns:
            float: 匹配得分
        """
        if not keywords:
            return 0.0
            
        text_lower = text.lower()
        
        # 统计每个关键词出现的次数
        keyword_counts = {}
        for keyword in keywords:
            import re
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text_lower)
            keyword_counts[keyword] = len(matches)
        
        # 计算加权得分
        total_matches = sum(keyword_counts.values())
        unique_matches = sum(1 for count in keyword_counts.values() if count > 0)
        
        # 结合总匹配次数和唯一匹配关键词数量
        score = 0.6 * (total_matches / (len(text.split()) + 1)) + 0.4 * (unique_matches / len(keywords))
        
        return min(1.0, score)
    
    async def _get_chunks(self) -> List[TextChunk]:
        """
        获取所有块
        
        Returns:
            List[TextChunk]: 所有块
        """
        # 简单实现，实际应该有更高效的方法
        # 比如从数据库查询或使用专门的索引
        # 这里假设vector_store能提供这种功能
        
        # 使用缓存
        if "all_chunks" in self.documents_cache:
            return self.documents_cache["all_chunks"]
            
        # 实际获取逻辑
        # 这是一个占位实现，需要根据实际情况替换
        chunks = []
        
        # 缓存结果
        self.documents_cache["all_chunks"] = chunks
        
        return chunks

@register_component(RAGComponentRegistry.RETRIEVER, "hybrid")
class HybridRetriever(Retriever[TextChunk]):
    """混合检索器 - 结合多种检索策略"""
    
    def __init__(
        self,
        retrievers: List[Retriever],
        fusion_method: str = "reciprocal_rank",
        weights: Optional[List[float]] = None,
        top_k: int = 5
    ):
        """
        初始化混合检索器
        
        Args:
            retrievers: 检索器列表
            fusion_method: 融合方法，支持 "reciprocal_rank", "round_robin", "weighted"
            weights: 权重列表，用于加权融合，长度应与retrievers相同
            top_k: 返回结果数量
        """
        self.retrievers = retrievers
        self.fusion_method = fusion_method
        self.weights = weights
        self.top_k = top_k
        
        # 验证权重
        if weights and len(weights) != len(retrievers):
            raise ValueError(f"权重列表长度 ({len(weights)}) 必须与检索器列表长度 ({len(retrievers)}) 相同")
    
    async def retrieve(self, query: str, limit: int = None, **kwargs) -> List[TextChunk]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            limit: 结果数量限制，覆盖top_k
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 检索结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用传入的limit或默认的top_k
            k = limit if limit is not None else self.top_k
            
            # 并行执行所有检索器
            all_results = []
            for retriever in self.retrievers:
                results = await retriever.retrieve(query, limit=k, **kwargs)
                all_results.append(results)
            
            # 融合结果
            if self.fusion_method == "reciprocal_rank":
                fused_results = self._reciprocal_rank_fusion(all_results)
            elif self.fusion_method == "round_robin":
                fused_results = self._round_robin_fusion(all_results)
            elif self.fusion_method == "weighted":
                fused_results = self._weighted_fusion(all_results)
            else:
                raise ValueError(f"未知的融合方法: {self.fusion_method}")
            
            # 取top k结果
            results = fused_results[:k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"混合检索耗时: {elapsed:.3f}秒, 返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            raise
    
    def _reciprocal_rank_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        倒数排名融合
        
        Args:
            result_lists: 检索结果列表的列表
            
        Returns:
            List[TextChunk]: 融合后的结果
        """
        # 创建ID到块的映射
        id_to_chunk = {}
        # 创建ID到得分的映射
        id_to_score = {}
        
        # 常数k，避免高排名结果的支配
        k = 60
        
        # 遍历所有结果列表
        for i, results in enumerate(result_lists):
            # 遍历当前列表中的每个结果
            for rank, chunk in enumerate(results):
                # 将块保存到映射
                id_to_chunk[chunk.id] = chunk
                
                # 计算RRF得分
                rrf_score = 1.0 / (k + rank + 1)
                
                # 累加得分
                if chunk.id in id_to_score:
                    id_to_score[chunk.id] += rrf_score
                else:
                    id_to_score[chunk.id] = rrf_score
        
        # 创建融合结果
        fused_results = []
        for chunk_id, score in id_to_score.items():
            # 获取原始块
            chunk = id_to_chunk[chunk_id]
            
            # 创建新块，更新得分
            fused_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=score  # 使用RRF得分
            )
            
            fused_results.append(fused_chunk)
        
        # 按融合得分排序
        fused_results.sort(key=lambda x: x.score or 0, reverse=True)
        
        return fused_results
    
    def _round_robin_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        轮询融合
        
        Args:
            result_lists: 检索结果列表的列表
            
        Returns:
            List[TextChunk]: 融合后的结果
        """
        fused_results = []
        chunk_ids = set()  # 用于去重
        
        # 取每个结果列表的最大长度
        max_len = max(len(results) for results in result_lists)
        
        # 轮询添加结果
        for i in range(max_len):
            for results in result_lists:
                if i < len(results):
                    chunk = results[i]
                    if chunk.id not in chunk_ids:
                        fused_results.append(chunk)
                        chunk_ids.add(chunk.id)
        
        return fused_results
    
    def _weighted_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        加权融合
        
        Args:
            result_lists: 检索结果列表的列表
            
        Returns:
            List[TextChunk]: 融合后的结果
        """
        if not self.weights:
            # 如果未提供权重，使用相等权重
            weights = [1.0 / len(result_lists)] * len(result_lists)
        else:
            # 归一化权重
            total = sum(self.weights)
            weights = [w / total for w in self.weights]
        
        # 创建ID到块的映射
        id_to_chunk = {}
        # 创建ID到得分的映射
        id_to_score = {}
        
        # 遍历所有结果列表
        for i, results in enumerate(result_lists):
            # 获取当前检索器的权重
            weight = weights[i]
            
            # 遍历当前列表中的每个结果
            for chunk in results:
                # 将块保存到映射
                id_to_chunk[chunk.id] = chunk
                
                # 计算加权得分
                weighted_score = (chunk.score or 0.5) * weight
                
                # 累加得分
                if chunk.id in id_to_score:
                    id_to_score[chunk.id] += weighted_score
                else:
                    id_to_score[chunk.id] = weighted_score
        
        # 创建融合结果
        fused_results = []
        for chunk_id, score in id_to_score.items():
            # 获取原始块
            chunk = id_to_chunk[chunk_id]
            
            # 创建新块，更新得分
            fused_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=score  # 使用加权得分
            )
            
            fused_results.append(fused_chunk)
        
        # 按融合得分排序
        fused_results.sort(key=lambda x: x.score or 0, reverse=True)
        
        return fused_results

@register_component(RAGComponentRegistry.RETRIEVER, "azure")
class AzureRetriever(Retriever[TextChunk]):
    """Azure专用检索器 - 针对Azure服务内容的优化检索"""
    
    def __init__(
        self,
        base_retriever: Retriever,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        service_terms: Optional[Dict[str, List[str]]] = None
    ):
        """
        初始化Azure专用检索器
        
        Args:
            base_retriever: 基础检索器
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            service_terms: 服务术语映射，例如{"VM": ["虚拟机", "Virtual Machine"]}
        """
        self.base_retriever = base_retriever
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.service_terms = service_terms or {
            "Virtual Machine": ["VM", "虚拟机"],
            "App Service": ["应用服务", "网站服务", "Web服务"],
            "Azure Kubernetes Service": ["AKS", "k8s", "kubernetes"],
            "Azure SQL Database": ["SQL DB", "SQLDB", "SQL数据库"],
            "Cosmos DB": ["宇宙数据库", "文档数据库"],
            "Storage Account": ["存储账户", "存储"],
        }
    
    async def retrieve(self, query: str, limit: int = None, **kwargs) -> List[TextChunk]:
        """
        检索相关内容
        
        Args:
            query: 查询文本
            limit: 结果数量限制，覆盖top_k
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 检索结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 使用传入的limit或默认的top_k
            k = limit if limit is not None else self.top_k
            
            # 扩展查询以增强对Azure服务的理解
            enhanced_query = self._enhance_query(query)
            
            # 使用基础检索器检索
            results = await self.base_retriever.retrieve(enhanced_query, limit=k, **kwargs)
            
            # 应用分数阈值
            if self.score_threshold is not None:
                results = [
                    result for result in results 
                    if result.score is None or result.score >= self.score_threshold
                ]
            
            # 执行Azure特定后处理
            processed_results = self._process_azure_results(query, results)
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"Azure检索耗时: {elapsed:.3f}秒, 返回 {len(processed_results)} 个结果")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Azure检索失败: {str(e)}")
            raise
    
    def _enhance_query(self, query: str) -> str:
        """增强查询，扩展Azure服务术语"""
        import re
        
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
            if is_pricing_query and any(term in chunk.content.lower() for term in ["价格", "定价", "成本", "费用"]):
                if processed_chunk.score is not None:
                    processed_chunk.score *= 1.2  # 提高定价内容的分数
            
            if is_comparison_query and any(term in chunk.content.lower() for term in ["比较", "对比", "vs", "versus"]):
                if processed_chunk.score is not None:
                    processed_chunk.score *= 1.15  # 提高比较内容的分数
            
            processed.append(processed_chunk)
        
        # 重新排序
        processed.sort(key=lambda x: x.score or 0, reverse=True)
        
        # 限制结果数量
        return processed[:len(results)]
    
    def _is_pricing_query(self, query: str) -> bool:
        """检查是否为定价查询"""
        pricing_terms = ["价格", "定价", "成本", "费用", "多少钱", "报价", "价格表"]
        return any(term in query.lower() for term in pricing_terms)
    
    def _is_comparison_query(self, query: str) -> bool:
        """检查是否为比较查询"""
        comparison_terms = ["比较", "对比", "区别", "差异", "优缺点", "vs", "versus", "哪个更好"]
        return any(term in query.lower() for term in comparison_terms)