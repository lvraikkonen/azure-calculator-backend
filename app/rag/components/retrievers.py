"""
检索器组件 - 检索相关内容
"""
from typing import List, Dict, Any, Optional, Union, Tuple
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import Retriever, VectorStore, QueryTransformer
from app.rag.core.models import TextChunk
from app.core.logging import get_logger
import time
import asyncio
import numpy as np

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

@register_component(RAGComponentRegistry.RETRIEVER, "multi_query_fusion")
class MultiQueryFusionRetriever(Retriever[TextChunk]):
    """多查询融合检索器 - 使用多个转换后的查询提高召回率"""

    def __init__(
            self,
            base_retriever: Retriever,
            query_transformer: QueryTransformer,
            fusion_method: str = "reciprocal_rank",
            max_queries: int = 3,
            top_k: int = 5
    ):
        """
        初始化多查询融合检索器

        Args:
            base_retriever: 基础检索器
            query_transformer: 查询转换器，用于生成多个查询变体
            fusion_method: 融合方法，支持 "reciprocal_rank", "rrf", "round_robin", "weighted_sum"
            max_queries: 最大查询数量
            top_k: 返回结果数量
        """
        self.base_retriever = base_retriever
        self.query_transformer = query_transformer
        self.fusion_method = fusion_method
        self.max_queries = max_queries
        self.top_k = top_k

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

            # 生成多个查询变体
            queries = await self._generate_query_variants(query)
            logger.debug(f"生成 {len(queries)} 个查询变体")

            # 并行执行所有查询
            all_results = []
            for q in queries:
                results = await self.base_retriever.retrieve(q, limit=k, **kwargs)
                all_results.append(results)

            # 融合结果
            fused_results = await self._fuse_results(all_results, fusion_method=self.fusion_method)

            # 限制结果数量
            final_results = fused_results[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"多查询融合检索耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果")

            return final_results

        except Exception as e:
            logger.error(f"多查询融合检索失败: {str(e)}")

            # 如果发生错误，回退到基本检索
            try:
                return await self.base_retriever.retrieve(query, limit=limit, **kwargs)
            except:
                # 如果仍然失败，返回空结果
                return []

    async def _generate_query_variants(self, query: str) -> List[str]:
        """
        生成查询变体

        Args:
            query: 原始查询

        Returns:
            List[str]: 查询变体列表，包括原始查询
        """
        # 始终包含原始查询
        variants = [query]

        try:
            # 使用查询转换器生成变体
            transformed = await self.query_transformer.transform(query)

            # 如果转换器返回的是字符串，添加为一个变体
            if isinstance(transformed, str) and transformed != query:
                variants.append(transformed)

            # 如果转换器支持子查询（如分解转换器），获取子查询
            if hasattr(self.query_transformer, "get_sub_queries"):
                sub_queries = await self.query_transformer.get_sub_queries()
                variants.extend(sub_queries)

            # 如果支持子查询和策略的组合
            if hasattr(self.query_transformer, "get_sub_queries_with_strategies"):
                sub_queries_with_strategies = await self.query_transformer.get_sub_queries_with_strategies()
                variants.extend([item["query"] for item in sub_queries_with_strategies])

            # 限制变体数量
            variants = variants[:self.max_queries]

            return variants

        except Exception as e:
            logger.error(f"生成查询变体失败: {str(e)}")
            return variants  # 返回仅包含原始查询的列表

    async def _fuse_results(
            self,
            all_results: List[List[TextChunk]],
            fusion_method: str
    ) -> List[TextChunk]:
        """
        融合多个检索结果

        Args:
            all_results: 多个检索结果的列表
            fusion_method: 融合方法

        Returns:
            List[TextChunk]: 融合后的结果
        """
        if not all_results:
            return []

        # 如果只有一个结果集，直接返回
        if len(all_results) == 1:
            return all_results[0]

        # 选择融合方法
        if fusion_method in ["reciprocal_rank", "rrf"]:
            return await self._reciprocal_rank_fusion(all_results)
        elif fusion_method == "round_robin":
            return await self._round_robin_fusion(all_results)
        elif fusion_method == "weighted_sum":
            return await self._weighted_sum_fusion(all_results)
        else:
            # 默认使用倒数排名融合
            return await self._reciprocal_rank_fusion(all_results)

    async def _reciprocal_rank_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        倒数排名融合 (RRF)

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
        for results in result_lists:
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

    async def _round_robin_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
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

    async def _weighted_sum_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        加权和融合

        Args:
            result_lists: 检索结果列表的列表

        Returns:
            List[TextChunk]: 融合后的结果
        """
        # 创建ID到块的映射
        id_to_chunk = {}
        # 创建ID到得分的映射
        id_to_score = {}

        # 确保所有结果都有分数
        normalized_results = []
        for results in result_lists:
            # 给没有分数的结果分配默认分数
            scored_results = []
            for rank, chunk in enumerate(results):
                score = chunk.score if chunk.score is not None else 1.0 - (rank / (len(results) or 1))
                new_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=score
                )
                scored_results.append(new_chunk)

            # 归一化分数
            max_score = max((r.score or 0) for r in scored_results) if scored_results else 1.0
            normalized = [
                TextChunk(
                    id=r.id,
                    doc_id=r.doc_id,
                    content=r.content,
                    metadata=r.metadata,
                    embedding=r.embedding,
                    score=(r.score or 0) / max_score if max_score > 0 else 0
                )
                for r in scored_results
            ]

            normalized_results.append(normalized)

        # 计算加权和
        for results in normalized_results:
            for chunk in results:
                # 将块保存到映射
                id_to_chunk[chunk.id] = chunk

                # 使用标准化后的分数
                score = chunk.score or 0

                # 累加得分
                if chunk.id in id_to_score:
                    id_to_score[chunk.id] += score
                else:
                    id_to_score[chunk.id] = score

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
                score=score
            )

            fused_results.append(fused_chunk)

        # 按融合得分排序
        fused_results.sort(key=lambda x: x.score or 0, reverse=True)

        return fused_results

@register_component(RAGComponentRegistry.RETRIEVER, "rag_fusion")
class RAGFusionRetriever(Retriever[TextChunk]):
    """RAG-Fusion检索器 - 专为RAG系统优化的融合检索"""

    def __init__(
            self,
            vector_retriever: Retriever,
            keyword_retriever: Optional[Retriever] = None,
            query_transformer: Optional[QueryTransformer] = None,
            fusion_method: str = "reciprocal_rank",
            top_k: int = 5,
            auto_rerank: bool = True,
            vector_weight: float = 0.7,
            keyword_weight: float = 0.3
    ):
        """
        初始化RAG-Fusion检索器

        Args:
            vector_retriever: 向量检索器
            keyword_retriever: 关键词检索器（可选）
            query_transformer: 查询转换器（可选）
            fusion_method: 融合方法，支持 "reciprocal_rank", "weighted"
            top_k: 返回结果数量
            auto_rerank: 是否自动重排序结果
            vector_weight: 向量检索结果权重
            keyword_weight: 关键词检索结果权重
        """
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.query_transformer = query_transformer
        self.fusion_method = fusion_method
        self.top_k = top_k
        self.auto_rerank = auto_rerank
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

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

            # 确定是否有查询分解
            use_decomposition = self.query_transformer is not None

            # 存储所有结果
            all_results = []

            # 1. 使用原始查询进行基本检索
            vector_results = await self.vector_retriever.retrieve(query, limit=k * 2)
            all_results.append(vector_results)

            # 如果有关键词检索器，添加关键词检索结果
            if self.keyword_retriever:
                keyword_results = await self.keyword_retriever.retrieve(query, limit=k * 2)
                all_results.append(keyword_results)

            # 2. 如果启用了查询转换，获取转换后的查询
            if use_decomposition:
                # 转换查询
                await self.query_transformer.transform(query)

                # 获取子查询
                if hasattr(self.query_transformer, "get_sub_queries_with_strategies"):
                    sub_queries_with_strategies = await self.query_transformer.get_sub_queries_with_strategies()

                    # 对每个子查询使用适当的检索器
                    for item in sub_queries_with_strategies:
                        sub_query = item["query"]
                        strategy = item["strategy"]

                        if strategy == "vector":
                            results = await self.vector_retriever.retrieve(sub_query, limit=k)
                            all_results.append(results)
                        elif strategy == "keyword" and self.keyword_retriever:
                            results = await self.keyword_retriever.retrieve(sub_query, limit=k)
                            all_results.append(results)
                        else:
                            # 默认使用向量检索
                            results = await self.vector_retriever.retrieve(sub_query, limit=k)
                            all_results.append(results)

                # 对于旧版本查询转换器，获取普通子查询
                elif hasattr(self.query_transformer, "get_sub_queries"):
                    sub_queries = await self.query_transformer.get_sub_queries()

                    # 使用向量检索器检索每个子查询
                    for sub_query in sub_queries:
                        results = await self.vector_retriever.retrieve(sub_query, limit=k)
                        all_results.append(results)

            # 如果没有任何结果，直接返回
            if not all_results or all(not results for results in all_results):
                logger.warning(f"RAG-Fusion未找到任何结果: {query}")
                return []

            # 3. 融合结果
            if self.fusion_method == "reciprocal_rank":
                fused_results = await self._reciprocal_rank_fusion(all_results)
            elif self.fusion_method == "weighted":
                fused_results = await self._weighted_fusion(all_results)
            else:
                # 默认使用RRF
                fused_results = await self._reciprocal_rank_fusion(all_results)

            # 4. 自动重排序（如果启用）
            if self.auto_rerank and len(fused_results) > 1:
                reranked_results = await self._auto_rerank(fused_results, query)
            else:
                reranked_results = fused_results

            # 限制结果数量
            final_results = reranked_results[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"RAG-Fusion检索耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果")

            return final_results

        except Exception as e:
            logger.error(f"RAG-Fusion检索失败: {str(e)}")

            # 如果发生错误，回退到基本向量检索
            try:
                return await self.vector_retriever.retrieve(query, limit=limit, **kwargs)
            except:
                # 如果仍然失败，返回空结果
                return []

    async def _reciprocal_rank_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        倒数排名融合 (RRF)

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
            # 跳过空结果
            if not results:
                continue

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

    async def _weighted_fusion(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        加权融合

        Args:
            result_lists: 检索结果列表的列表

        Returns:
            List[TextChunk]: 融合后的结果
        """
        # 如果结果列表为空，返回空列表
        if not result_lists:
            return []

        # 过滤空结果列表
        result_lists = [results for results in result_lists if results]
        if not result_lists:
            return []

        # 创建ID到块的映射
        id_to_chunk = {}
        # 创建ID到得分的映射
        id_to_score = {}

        # 确定每个结果列表的权重
        if len(result_lists) == 1:
            weights = [1.0]
        elif len(result_lists) == 2 and self.keyword_retriever:
            # 假设第一个是向量结果，第二个是关键词结果
            weights = [self.vector_weight, self.keyword_weight]
        else:
            # 默认权重：均分
            weights = [1.0 / len(result_lists)] * len(result_lists)

        # 遍历所有结果列表
        for i, (results, weight) in enumerate(zip(result_lists, weights)):
            # 遍历当前列表中的每个结果
            for chunk in results:
                # 将块保存到映射
                id_to_chunk[chunk.id] = chunk

                # 计算加权得分
                score = (chunk.score or 0.5) * weight

                # 累加得分
                if chunk.id in id_to_score:
                    id_to_score[chunk.id] += score
                else:
                    id_to_score[chunk.id] = score

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

    async def _auto_rerank(self, chunks: List[TextChunk], query: str) -> List[TextChunk]:
        """
        自动重排序结果

        Args:
            chunks: 检索块
            query: 查询文本

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        # 简化的重排序实现
        # 实际应用中可能需要更复杂的重排序逻辑

        # 创建重排序特征
        reranked_chunks = []
        for chunk in chunks:
            # 计算附加特征
            features = self._compute_rerank_features(chunk, query)

            # 计算新得分
            new_score = chunk.score or 0.5  # 基础得分

            # 应用特征加权
            for feature, value in features.items():
                if feature == "title_match":
                    new_score *= (1 + value * 0.2)  # 标题匹配提升20%
                elif feature == "freshness":
                    new_score *= (1 + value * 0.1)  # 新鲜度提升10%
                elif feature == "content_length":
                    new_score *= (1 + value * 0.05)  # 内容长度提升5%

            # 创建新块，更新得分
            reranked_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=new_score
            )

            reranked_chunks.append(reranked_chunk)

        # 按新得分排序
        reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)

        return reranked_chunks

    def _compute_rerank_features(self, chunk: TextChunk, query: str) -> Dict[str, float]:
        """
        计算重排序特征

        Args:
            chunk: 文本块
            query: 查询文本

        Returns:
            Dict[str, float]: 特征字典
        """
        features = {}

        # 标题匹配特征
        title = chunk.metadata.title or ""
        if any(term.lower() in title.lower() for term in query.lower().split()):
            features["title_match"] = 1.0
        else:
            features["title_match"] = 0.0

        # 内容长度特征（偏好中等长度）
        content_length = len(chunk.content)
        if 200 <= content_length <= 1000:
            features["content_length"] = 1.0
        elif content_length < 200:
            features["content_length"] = content_length / 200
        else:
            features["content_length"] = 1000 / content_length

        # 新鲜度特征（如果有修改日期）
        if chunk.metadata.modified_at:
            import datetime
            now = datetime.datetime.now()
            diff = now - chunk.metadata.modified_at

            # 一周内的内容获得满分
            if diff.days <= 7:
                features["freshness"] = 1.0
            # 一个月内的内容得分递减
            elif diff.days <= 30:
                features["freshness"] = 1.0 - (diff.days - 7) / 23
            # 超过一个月的内容得分较低
            else:
                features["freshness"] = 0.2
        else:
            # 没有修改日期，默认中等新鲜度
            features["freshness"] = 0.5

        return features