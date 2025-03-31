"""
重排序组件 - 对检索结果进行二次排序
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.models import TextChunk
from app.rag.core.interfaces import EmbeddingProvider
from app.core.logging import get_logger
import time
import re

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.RERANKER, "similarity")
class SimilarityReranker:
    """相似度重排序器 - 基于嵌入相似度重新排序"""
    
    def __init__(self, embedding_provider: EmbeddingProvider):
        """
        初始化相似度重排序器
        
        Args:
            embedding_provider: 嵌入提供者
        """
        self.embedding_provider = embedding_provider
    
    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果
        
        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            
        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 获取查询嵌入
            query_embedding = await self.embedding_provider.get_embedding(query)
            
            # 计算余弦相似度
            reranked_chunks = []
            for chunk in chunks:
                # 如果块没有嵌入，获取嵌入
                if chunk.embedding is None:
                    chunk.embedding = await self.embedding_provider.get_embedding(chunk.content)
                
                # 计算相似度
                similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                
                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=similarity
                )
                
                reranked_chunks.append(reranked_chunk)
            
            # 按相似度排序
            reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)
            
            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"相似度重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"相似度重排序失败: {str(e)}")
            # 返回原始结果
            return chunks
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 相似度，范围[0, 1]
        """
        import numpy as np
        
        # 转换为numpy数组
        a = np.array(vec1)
        b = np.array(vec2)
        
        # 计算余弦相似度
        cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        # 处理可能的数值错误
        if np.isnan(cos_sim):
            return 0.0
            
        return float(cos_sim)

@register_component(RAGComponentRegistry.RERANKER, "cross_encoder")
class CrossEncoderReranker:
    """交叉编码器重排序器 - 使用交叉编码器模型进行高精度重排序"""
    
    def __init__(
        self, 
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        batch_size: int = 8
    ):
        """
        初始化交叉编码器重排序器
        
        Args:
            model_name: 模型名称
            device: 设备，'cpu'或'cuda'
            batch_size: 批处理大小
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.model = None
        
    def _load_model(self):
        """加载模型（延迟加载）"""
        # 目前实现需要额外安装：pip install sentence-transformers
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info(f"已加载交叉编码器模型: {self.model_name}")
            except Exception as e:
                logger.error(f"加载交叉编码器模型失败: {str(e)}")
                raise
    
    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果
        
        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            
        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 加载模型
            self._load_model()
            
            # 准备输入对
            pairs = [(query, chunk.content) for chunk in chunks]
            
            # 计算分数
            scores = self.model.predict(pairs)
            
            # 创建重排序的结果
            reranked_chunks = []
            for i, chunk in enumerate(chunks):
                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=float(scores[i])
                )
                
                reranked_chunks.append(reranked_chunk)
            
            # 按分数排序
            reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)
            
            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"交叉编码器重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"交叉编码器重排序失败: {str(e)}")
            # 返回原始结果
            return chunks

@register_component(RAGComponentRegistry.RERANKER, "contextual")
class ContextualReranker:
    """上下文重排序器 - 考虑查询上下文进行重排序"""
    
    def __init__(self, embedding_provider: EmbeddingProvider, llm_service: Any):
        """
        初始化上下文重排序器
        
        Args:
            embedding_provider: 嵌入提供者
            llm_service: LLM服务，用于分析上下文
        """
        self.embedding_provider = embedding_provider
        self.llm_service = llm_service
    
    async def rerank(
        self, 
        query: str, 
        chunks: List[TextChunk], 
        top_k: int = None,
        conversation_history: List[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        重新排序检索结果，考虑对话上下文
        
        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            conversation_history: 对话历史
            
        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []
            
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 如果没有对话历史，简单地返回原始结果
            if not conversation_history:
                return chunks[:top_k] if top_k is not None else chunks
            
            # 分析上下文
            context_keywords = await self._extract_context_keywords(conversation_history)
            
            # 调整分数
            reranked_chunks = []
            for chunk in chunks:
                # 基础分数（原始分数或默认值）
                base_score = chunk.score or 0.5
                
                # 上下文相关性加成
                context_bonus = self._compute_context_bonus(chunk.content, context_keywords)
                
                # 最终分数
                final_score = base_score * (1 + context_bonus)
                
                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=final_score
                )
                
                reranked_chunks.append(reranked_chunk)
            
            # 按分数排序
            reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)
            
            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]
            
            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"上下文重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果, 上下文关键词: {context_keywords}")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"上下文重排序失败: {str(e)}")
            # 返回原始结果
            return chunks[:top_k] if top_k is not None else chunks
    
    async def _extract_context_keywords(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """
        从对话历史中提取上下文关键词
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            List[str]: 关键词列表
        """
        # 提取最近的对话内容
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        context = "\n".join([msg["content"] for msg in recent_messages])
        
        # 使用LLM提取关键词
        prompt = f"""
        请从以下对话中提取5个关键词，这些关键词将用于帮助检索相关内容。只返回关键词，用逗号分隔。
        
        对话:
        {context}
        
        关键词：
        """
        
        # 调用LLM
        response = await self.llm_service.chat(prompt)
        
        # 解析响应
        keywords_text = response.content.strip()
        
        # 分割关键词
        keywords = [kw.strip() for kw in keywords_text.split(",")]
        
        return keywords
    
    def _compute_context_bonus(self, text: str, keywords: List[str]) -> float:
        """
        计算上下文相关性加成
        
        Args:
            text: 文本内容
            keywords: 上下文关键词
            
        Returns:
            float: 加成分数，范围[0, 0.5]
        """
        if not keywords:
            return 0.0
            
        text_lower = text.lower()
        
        # 统计匹配的关键词数量
        matched = sum(1 for kw in keywords if kw.lower() in text_lower)
        
        # 计算加成，最高0.5（50%）
        bonus = 0.5 * (matched / len(keywords))
        
        return bonus

@register_component(RAGComponentRegistry.RERANKER, "llm_reranker")
class LLMReranker:
    """LLM重排序器 - 使用LLM评估文档与查询的相关性"""

    def __init__(
            self,
            llm_service: Any,
            batch_size: int = 5,
            max_input_tokens: int = 4000,
            detailed_scoring: bool = False
    ):
        """
        初始化LLM重排序器

        Args:
            llm_service: LLM服务
            batch_size: 批处理大小，一次评估多少个块
            max_input_tokens: 最大输入令牌数
            detailed_scoring: 是否返回详细评分
        """
        self.llm_service = llm_service
        self.batch_size = batch_size
        self.max_input_tokens = max_input_tokens
        self.detailed_scoring = detailed_scoring

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 如果结果很少，无需批处理
            if len(chunks) <= self.batch_size:
                reranked_chunks = await self._rerank_batch(query, chunks)
            else:
                # 分批处理
                all_reranked = []
                for i in range(0, len(chunks), self.batch_size):
                    batch = chunks[i:i + self.batch_size]
                    reranked_batch = await self._rerank_batch(query, batch)
                    all_reranked.extend(reranked_batch)

                # 再次排序以确保一致性
                reranked_chunks = sorted(all_reranked, key=lambda x: x.score or 0, reverse=True)

            # 限制结果数量
            if top_k is not None:
                reranked_chunks = reranked_chunks[:top_k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"LLM重排序耗时: {elapsed:.3f}秒, 返回 {len(reranked_chunks)} 个结果")

            return reranked_chunks

        except Exception as e:
            logger.error(f"LLM重排序失败: {str(e)}")
            # 返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    async def _rerank_batch(self, query: str, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        重排序单个批次

        Args:
            query: 查询文本
            chunks: 检索结果批次

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        # 准备提示词
        prompt = self._prepare_scoring_prompt(query, chunks)

        # 调用LLM
        response = await self.llm_service.chat(prompt)

        # 解析分数
        chunk_scores = self._parse_scores(response.content, chunks)

        # 创建重排序后的块
        reranked_chunks = []
        for chunk, new_score in zip(chunks, chunk_scores):
            # 仅当新分数有效时更新
            if new_score is not None:
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
            else:
                # 使用原始块
                reranked_chunks.append(chunk)

        # 按分数排序
        reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)

        return reranked_chunks

    def _prepare_scoring_prompt(self, query: str, chunks: List[TextChunk]) -> str:
        """
        准备评分提示词

        Args:
            query: 查询文本
            chunks: 检索结果批次

        Returns:
            str: 评分提示词
        """
        prompt = f"""
        请评估以下文本段落与查询的相关性。

        查询: {query}

        文本段落:
        """

        # 添加每个块
        for i, chunk in enumerate(chunks):
            # 截断过长的内容
            content = chunk.content
            if len(content) > self.max_input_tokens // len(chunks):
                content = content[:self.max_input_tokens // len(chunks)] + "..."

            prompt += f"\n[{i + 1}] {content}\n"

        # 添加评分指南
        if self.detailed_scoring:
            prompt += """
            为每个段落评分，打分范围为0-10，并解释评分理由。包括以下方面的评估:
            - 相关性：内容与查询的直接相关程度
            - 信息质量：信息的深度、准确性和专业性
            - 完整性：回答问题所需的信息完整度

            请使用以下格式返回分数:

            段落[1]: 分数=X.X
            理由：...

            段落[2]: 分数=X.X
            理由：...

            ...
            """
        else:
            prompt += """
            为每个段落的相关性评分，打分范围为0-10。

            请使用以下格式返回分数:

            段落[1]: X.X
            段落[2]: X.X
            ...
            """

        return prompt

    def _parse_scores(self, response: str, chunks: List[TextChunk]) -> List[float]:
        """
        解析LLM响应中的分数

        Args:
            response: LLM响应文本
            chunks: 原始块列表

        Returns:
            List[float]: 分数列表
        """
        # 初始化返回值
        scores = [None] * len(chunks)

        # 解析LLM评分
        import re

        if self.detailed_scoring:
            pattern = r'段落\[(\d+)\]:\s*分数=(\d+(?:\.\d+)?)'
        else:
            pattern = r'段落\[(\d+)\]:\s*(\d+(?:\.\d+)?)'

        # 查找所有匹配
        for match in re.finditer(pattern, response):
            idx = int(match.group(1)) - 1  # 段落编号从1开始
            score = float(match.group(2))

            # 确保索引有效
            if 0 <= idx < len(chunks):
                # 将0-10分转换为0-1分
                scores[idx] = score / 10.0

        # 处理未找到分数的情况
        for i, score in enumerate(scores):
            if score is None:
                # 使用现有的分数或默认值
                scores[i] = chunks[i].score or 0.5

        return scores

@register_component(RAGComponentRegistry.RERANKER, "multistage_reranker")
class MultistageReranker:
    """多阶段重排序器 - 结合多种重排序策略"""

    def __init__(
            self,
            rerankers: List[Any],
            weights: Optional[List[float]] = None,
            top_k: int = 5
    ):
        """
        初始化多阶段重排序器

        Args:
            rerankers: 重排序器列表
            weights: 重排序器权重，为None则使用公平权重
            top_k: 返回结果数量
        """
        self.rerankers = rerankers

        # 确保权重有效，否则使用公平权重
        if weights and len(weights) == len(rerankers):
            total = sum(weights)
            self.weights = [w / total for w in weights]
        else:
            # 公平权重
            self.weights = [1.0 / len(rerankers)] * len(rerankers)

        self.top_k = top_k

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量，覆盖初始设置

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 使用传入的top_k或默认值
            k = top_k if top_k is not None else self.top_k

            # 对于每个重排序器，获取其重排序结果
            stage_results = []
            for reranker in self.rerankers:
                try:
                    # 每个阶段保持较多的结果
                    stage_k = min(k * 2, len(chunks))
                    reranked = await reranker.rerank(query, chunks, stage_k)
                    stage_results.append(reranked)
                except Exception as e:
                    logger.error(f"重排序阶段失败: {type(reranker).__name__}, 错误: {str(e)}")
                    # 如果这个阶段失败，使用原始结果
                    stage_results.append(chunks[:stage_k])

            # 融合多阶段结果
            final_results = await self._fuse_results(stage_results)

            # 限制结果数量
            final_results = final_results[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"多阶段重排序耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果")

            return final_results

        except Exception as e:
            logger.error(f"多阶段重排序失败: {str(e)}")
            # 返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    async def _fuse_results(self, result_lists: List[List[TextChunk]]) -> List[TextChunk]:
        """
        融合多阶段结果

        Args:
            result_lists: 多阶段结果列表

        Returns:
            List[TextChunk]: 融合后的结果
        """
        # 创建ID到块的映射
        id_to_chunk = {}
        # 创建ID到得分的映射
        id_to_score = {}

        # 遍历所有阶段结果
        for stage, (results, weight) in enumerate(zip(result_lists, self.weights)):
            # 对每个结果应用权重
            for rank, chunk in enumerate(results):
                # 将块保存到映射
                id_to_chunk[chunk.id] = chunk

                # 计算得分
                score = (chunk.score or 0.5) * weight

                # 应用排名因子 - 排名越高分数越高
                rank_factor = 1.0 - (rank / (len(results) or 1))
                score = score * 0.7 + rank_factor * weight * 0.3

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

        # 按得分排序
        fused_results.sort(key=lambda x: x.score or 0, reverse=True)

        return fused_results

@register_component(RAGComponentRegistry.RERANKER, "hybrid_relevance_reranker")
class HybridRelevanceReranker:
    """混合相关性重排序器 - 结合语义和关键词相关性"""

    def __init__(
            self,
            embedding_provider: EmbeddingProvider,
            semantic_weight: float = 0.6,
            keyword_weight: float = 0.4,
            context_weight: float = 0.2,
            metadata_fields: List[str] = ["title", "source", "summary"],
            top_k: int = 5
    ):
        """
        初始化混合相关性重排序器

        Args:
            embedding_provider: 嵌入提供者
            semantic_weight: 语义相关性权重
            keyword_weight: 关键词相关性权重
            context_weight: 上下文相关性权重
            metadata_fields: 要检查的元数据字段
            top_k: 返回结果数量
        """
        self.embedding_provider = embedding_provider
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.context_weight = context_weight
        self.metadata_fields = metadata_fields
        self.top_k = top_k

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None, **kwargs) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            **kwargs: 其他参数，可能包含上下文信息

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 使用传入的top_k或默认值
            k = top_k if top_k is not None else self.top_k

            # 获取查询嵌入
            query_embedding = await self.embedding_provider.get_embedding(query)

            # 计算多种相关性分数并重排序
            reranked_chunks = []
            for chunk in chunks:
                # 1. 计算语义相似度
                semantic_score = self._compute_semantic_similarity(
                    query_embedding,
                    chunk.embedding
                ) if chunk.embedding else 0.5

                # 2. 计算关键词相关性
                keyword_score = self._compute_keyword_relevance(query, chunk.content)

                # 3. 检查元数据匹配
                metadata_score = self._compute_metadata_match(query, chunk.metadata)

                # 4. 考虑上下文（如果提供）
                context_score = 0.0
                conversation_history = kwargs.get("conversation_history", [])
                if conversation_history:
                    context_score = self._compute_context_relevance(
                        chunk.content,
                        conversation_history
                    )

                # 5. 计算加权综合得分
                final_score = (
                        semantic_score * self.semantic_weight +
                        keyword_score * self.keyword_weight +
                        metadata_score * 0.1 +  # 元数据固定较低权重
                        context_score * self.context_weight
                )

                # 创建新块，更新得分
                reranked_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata={
                        **chunk.metadata.dict(),
                        "semantic_score": semantic_score,
                        "keyword_score": keyword_score,
                        "metadata_score": metadata_score,
                        "context_score": context_score
                    },
                    embedding=chunk.embedding,
                    score=final_score
                )

                reranked_chunks.append(reranked_chunk)

            # 按最终得分排序
            reranked_chunks.sort(key=lambda x: x.score or 0, reverse=True)

            # 限制结果数量
            final_results = reranked_chunks[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(f"混合相关性重排序耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果")

            return final_results

        except Exception as e:
            logger.error(f"混合相关性重排序失败: {str(e)}")
            # 返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    def _compute_semantic_similarity(self, query_embedding: List[float], chunk_embedding: List[float]) -> float:
        """
        计算语义相似度

        Args:
            query_embedding: 查询嵌入
            chunk_embedding: 块嵌入

        Returns:
            float: 相似度分数
        """
        if query_embedding is None or chunk_embedding is None:
            return 0.5  # 默认中等相关性

        try:
            # 计算余弦相似度
            import numpy as np

            # 转换为numpy数组
            a = np.array(query_embedding)
            b = np.array(chunk_embedding)

            # 计算余弦相似度
            cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            # 处理可能的数值错误
            if np.isnan(cos_sim):
                return 0.5

            return float(cos_sim)
        except:
            return 0.5

    def _compute_keyword_relevance(self, query: str, content: str) -> float:
        """
        计算关键词相关性

        Args:
            query: 查询文本
            content: 内容文本

        Returns:
            float: 相关性分数
        """
        # 提取查询关键词
        import re

        # 分词
        query_words = re.findall(r'\w+', query.lower())

        # 停用词（简化版）
        stopwords = {"and", "or", "the", "a", "an", "is", "are", "in", "on", "at", "to", "for", "with"}

        # 过滤停用词
        keywords = [word for word in query_words if word not in stopwords and len(word) > 1]

        if not keywords:
            return 0.5  # 没有有效关键词

        # 统计关键词匹配
        content_lower = content.lower()

        # 统计每个关键词出现的次数
        keyword_counts = {}
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, content_lower)
            keyword_counts[keyword] = len(matches)

        # 计算加权得分
        total_matches = sum(keyword_counts.values())
        unique_matches = sum(1 for count in keyword_counts.values() if count > 0)

        if len(keywords) == 0:
            return 0.5

        # 计算得分
        # 1. 关键词覆盖率
        coverage = unique_matches / len(keywords)

        # 2. 关键词密度
        words_count = len(content_lower.split())
        if words_count == 0:
            density = 0
        else:
            density = total_matches / words_count

        # 综合得分
        score = 0.7 * coverage + 0.3 * min(1.0, density * 20)

        return score

    def _compute_metadata_match(self, query: str, metadata: Any) -> float:
        """
        计算元数据匹配度

        Args:
            query: 查询文本
            metadata: 元数据

        Returns:
            float: 匹配度分数
        """
        query_lower = query.lower()
        score = 0.0
        count = 0

        # 检查所有指定的元数据字段
        for field in self.metadata_fields:
            if hasattr(metadata, field):
                value = getattr(metadata, field)
                if value and isinstance(value, str):
                    # 简单字符串匹配
                    if query_lower in value.lower():
                        score += 1.0

                    # 关键词匹配
                    import re
                    query_words = set(re.findall(r'\w+', query_lower))
                    value_words = set(re.findall(r'\w+', value.lower()))

                    # 计算交集大小
                    overlap = len(query_words.intersection(value_words))
                    if overlap > 0:
                        score += overlap / len(query_words) if query_words else 0

                    count += 1

            # 也检查额外元数据
            elif hasattr(metadata, "extra") and field in metadata.extra:
                value = metadata.extra[field]
                if value and isinstance(value, str):
                    if query_lower in value.lower():
                        score += 1.0

                    # 关键词匹配
                    import re
                    query_words = set(re.findall(r'\w+', query_lower))
                    value_words = set(re.findall(r'\w+', value.lower()))

                    # 计算交集大小
                    overlap = len(query_words.intersection(value_words))
                    if overlap > 0:
                        score += overlap / len(query_words) if query_words else 0

                    count += 1

        # 计算平均分
        return score / (count or 1)

    def _compute_context_relevance(self, content: str, conversation_history: List[Dict[str, Any]]) -> float:
        """
        计算与对话上下文的相关性

        Args:
            content: 内容文本
            conversation_history: 对话历史

        Returns:
            float: 相关性分数
        """
        # 只考虑最近的几条消息
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history

        # 提取消息文本
        context_text = " ".join([msg.get("content", "") for msg in recent_messages])

        # 提取上下文关键词
        import re

        # 分词
        context_words = re.findall(r'\w+', context_text.lower())

        # 停用词（简化版）
        stopwords = {"and", "or", "the", "a", "an", "is", "are", "in", "on", "at", "to", "for", "with"}

        # 过滤停用词
        keywords = [word for word in context_words if word not in stopwords and len(word) > 1]

        if not keywords:
            return 0.5  # 没有有效关键词

        # 统计关键词匹配
        content_lower = content.lower()

        # 统计每个关键词出现的次数
        keyword_counts = {}
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, content_lower)
            keyword_counts[keyword] = len(matches)

        # 计算加权得分
        total_matches = sum(keyword_counts.values())
        unique_matches = sum(1 for count in keyword_counts.values() if count > 0)

        # 关键词覆盖率（考虑前20个关键词）
        top_keywords = sorted(keywords, key=lambda k: keyword_counts.get(k, 0), reverse=True)[:20]
        coverage = sum(1 for k in top_keywords if keyword_counts.get(k, 0) > 0) / len(top_keywords)

        # 关键词密度
        words_count = len(content_lower.split())
        if words_count == 0:
            density = 0
        else:
            density = total_matches / words_count

        # 综合得分
        score = 0.7 * coverage + 0.3 * min(1.0, density * 10)

        return score

@register_component(RAGComponentRegistry.RERANKER, "azure_specialized_reranker")
class AzureSpecializedReranker:
    """Azure专用重排序器 - 针对Azure文档的特定重排序逻辑"""

    def __init__(
            self,
            base_reranker: Any,
            pricing_keywords: List[str] = None,
            comparison_keywords: List[str] = None,
            service_mappings: Dict[str, List[str]] = None,
            boost_recent: bool = True,
            top_k: int = 5
    ):
        """
        初始化Azure专用重排序器

        Args:
            base_reranker: 基础重排序器
            pricing_keywords: 定价相关关键词
            comparison_keywords: 比较相关关键词
            service_mappings: 服务映射，用于标准化服务名称
            boost_recent: 是否提升最近文档
            top_k: 返回结果数量
        """
        self.base_reranker = base_reranker
        self.pricing_keywords = pricing_keywords or [
            "价格", "定价", "费用", "成本", "计费", "价格表",
            "price", "pricing", "cost", "billing", "expense", "charge"
        ]
        self.comparison_keywords = comparison_keywords or [
            "比较", "对比", "区别", "差异", "优缺点", "何时使用",
            "compare", "comparison", "difference", "versus", "vs", "pros and cons"
        ]
        self.service_mappings = service_mappings or {
            "vm": ["虚拟机", "virtual machine", "azure vm", "compute", "计算实例"],
            "storage": ["存储", "blob", "文件", "file", "table", "queue", "数据存储"],
            "database": ["数据库", "sql", "cosmos", "mysql", "postgresql", "nosql"],
            "kubernetes": ["容器", "container", "aks", "k8s"],
            "app service": ["应用服务", "网站", "web app", "webapp"],
            "functions": ["函数", "function app", "无服务器", "serverless"]
        }
        self.boost_recent = boost_recent
        self.top_k = top_k

    async def rerank(self, query: str, chunks: List[TextChunk], top_k: int = None, **kwargs) -> List[TextChunk]:
        """
        重新排序检索结果

        Args:
            query: 查询文本
            chunks: 检索结果
            top_k: 返回结果数量
            **kwargs: 其他参数

        Returns:
            List[TextChunk]: 重排序后的结果
        """
        if not chunks:
            return []

        try:
            # 记录开始时间
            start_time = time.time()

            # 使用传入的top_k或默认值
            k = top_k if top_k is not None else self.top_k

            # 使用基础重排序器获取初始排序
            reranked_chunks = await self.base_reranker.rerank(query, chunks, k, **kwargs)

            # 分析查询类型
            query_type = self._analyze_query_type(query)

            # 应用Azure特定的调整
            final_chunks = self._apply_azure_adjustments(reranked_chunks, query, query_type)

            # 限制结果数量
            final_results = final_chunks[:k]

            # 记录性能
            elapsed = time.time() - start_time
            logger.debug(
                f"Azure专用重排序耗时: {elapsed:.3f}秒, 返回 {len(final_results)} 个结果, 查询类型: {query_type}")

            return final_results

        except Exception as e:
            logger.error(f"Azure专用重排序失败: {str(e)}")
            # 如果基础重排序器成功，返回其结果
            if self.base_reranker:
                try:
                    return await self.base_reranker.rerank(query, chunks, top_k)
                except:
                    pass
            # 否则返回原始结果
            return chunks[:top_k] if top_k is not None else chunks

    def _analyze_query_type(self, query: str) -> str:
        """
        分析查询类型

        Args:
            query: 查询文本

        Returns:
            str: 查询类型
        """
        query_lower = query.lower()

        # 检查是否为定价查询
        if any(keyword in query_lower for keyword in self.pricing_keywords):
            return "pricing"

        # 检查是否为比较查询
        if any(keyword in query_lower for keyword in self.comparison_keywords):
            return "comparison"

        # 检查是否为配置查询
        if any(term in query_lower for term in
               ["如何", "怎么", "配置", "设置", "创建", "部署", "how to", "setup", "configure"]):
            return "configuration"

        # 默认为一般查询
        return "general"

    def _apply_azure_adjustments(self, chunks: List[TextChunk], query: str, query_type: str) -> List[TextChunk]:
        """
        应用Azure特定的重排序调整

        Args:
            chunks: 重排序块
            query: 查询文本
            query_type: 查询类型

        Returns:
            List[TextChunk]: 调整后的块
        """
        adjusted_chunks = []

        # 提取查询中的服务引用
        referenced_services = self._extract_services(query)

        for chunk in chunks:
            # 基础分数
            score = chunk.score or 0.5

            # 获取调整后的分数
            adjusted_score = self._adjust_score_by_type(
                score,
                chunk,
                query_type,
                referenced_services
            )

            # 创建新块，更新得分
            adjusted_chunk = TextChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
                score=adjusted_score
            )

            adjusted_chunks.append(adjusted_chunk)

        # 按调整后的分数排序
        adjusted_chunks.sort(key=lambda x: x.score or 0, reverse=True)

        return adjusted_chunks

    def _extract_services(self, query: str) -> List[str]:
        """
        从查询中提取服务引用

        Args:
            query: 查询文本

        Returns:
            List[str]: 引用的服务列表
        """
        query_lower = query.lower()
        referenced = []

        # 检查每个服务和其别名
        for service, aliases in self.service_mappings.items():
            if service in query_lower:
                referenced.append(service)
            else:
                # 检查别名
                for alias in aliases:
                    if alias in query_lower:
                        referenced.append(service)
                        break

        return referenced

    def _adjust_score_by_type(
            self,
            score: float,
            chunk: TextChunk,
            query_type: str,
            referenced_services: List[str]
    ) -> float:
        """
        根据查询类型调整分数

        Args:
            score: 原始分数
            chunk: 文本块
            query_type: 查询类型
            referenced_services: 引用的服务

        Returns:
            float: 调整后的分数
        """
        # 检查内容类型
        content_lower = chunk.content.lower()

        # 基于查询类型进行调整
        if query_type == "pricing":
            # 如果内容包含价格相关关键词，提升分数
            if any(keyword in content_lower for keyword in self.pricing_keywords):
                score *= 1.3

            # 如果包含具体数字（可能是价格），提升分数
            if re.search(r'\$\d+|\d+\s*(元|美元|欧元)', content_lower):
                score *= 1.2

        elif query_type == "comparison":
            # 如果内容包含比较关键词，提升分数
            if any(keyword in content_lower for keyword in self.comparison_keywords):
                score *= 1.25

            # 如果内容同时包含多个被引用的服务，大幅提升分数
            mentioned_services = 0
            for service in referenced_services:
                if service in content_lower or any(
                        alias in content_lower for alias in self.service_mappings.get(service, [])):
                    mentioned_services += 1

            if mentioned_services >= 2:
                score *= 1.3
            elif mentioned_services == 1 and len(referenced_services) >= 2:
                # 包含部分被引用的服务，适度提升
                score *= 1.1

        elif query_type == "configuration":
            # 如果内容包含步骤指南特征，提升分数
            if re.search(r'步骤|第.步|首先|然后|接下来|最后|步骤|step|first|then|next|finally', content_lower):
                score *= 1.2

            # 如果包含代码或命令样例，提升分数
            if re.search(r'```|az\s+|azcli|powershell|cmd|bash', content_lower):
                score *= 1.15

        # 通用调整：提升包含引用服务的结果
        if referenced_services:
            for service in referenced_services:
                if service in content_lower or any(
                        alias in content_lower for alias in self.service_mappings.get(service, [])):
                    score *= 1.1
                    break

        # 如果启用了时效性提升
        if self.boost_recent and hasattr(chunk.metadata, "created_at"):
            import datetime

            # 获取创建日期
            created_at = chunk.metadata.created_at
            modified_at = chunk.metadata.modified_at or created_at

            if modified_at:
                # 计算天数差异
                now = datetime.datetime.now()
                try:
                    # 日期可能是字符串
                    if isinstance(modified_at, str):
                        modified_at = datetime.datetime.fromisoformat(modified_at.replace('Z', '+00:00'))

                    delta = now - modified_at
                    days = delta.days

                    # 根据时效性调整分数
                    if days <= 30:  # 一个月内
                        score *= 1.15
                    elif days <= 90:  # 三个月内
                        score *= 1.08
                    elif days <= 180:  # 六个月内
                        score *= 1.04
                except:
                    # 忽略解析错误
                    pass

        return score