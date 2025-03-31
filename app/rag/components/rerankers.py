"""
重排序组件 - 对检索结果进行二次排序
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.models import TextChunk
from app.rag.core.interfaces import EmbeddingProvider
from app.core.logging import get_logger
import time

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