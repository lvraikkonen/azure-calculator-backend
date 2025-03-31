"""
向量存储组件 - 存储和检索向量化内容
"""
from typing import List, Dict, Any, Optional, Union
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import VectorStore, EmbeddingProvider
from app.rag.core.models import TextChunk
from app.core.logging import get_logger

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.VECTOR_STORE, "memory")
class InMemoryVectorStore(VectorStore[TextChunk, List[float]]):
    """内存向量存储 - 使用内存存储向量，适用于开发和小型数据集"""
    
    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        """
        初始化内存向量存储
        
        Args:
            embedding_provider: 嵌入提供者，用于获取嵌入
        """
        self.embedding_provider = embedding_provider
        self.chunks = {}  # 块存储，键为ID，值为块
        self.embeddings = {}  # 嵌入存储，键为ID，值为嵌入
    
    async def add(self, chunks: List[TextChunk], **kwargs) -> List[str]:
        """
        添加块到向量存储
        
        Args:
            chunks: 块列表
            **kwargs: 其他参数
            
        Returns:
            List[str]: 块ID列表
        """
        if not chunks:
            return []
            
        try:
            chunk_ids = []
            
            # 处理每个块
            for chunk in chunks:
                # 获取嵌入（如果需要）
                if chunk.embedding is None and self.embedding_provider:
                    chunk.embedding = await self.embedding_provider.get_embedding(chunk.content)
                
                # 存储块和嵌入
                self.chunks[chunk.id] = chunk
                if chunk.embedding:
                    self.embeddings[chunk.id] = chunk.embedding
                
                chunk_ids.append(chunk.id)
            
            logger.debug(f"已添加 {len(chunk_ids)} 个块到内存向量存储，总块数: {len(self.chunks)}")
            
            return chunk_ids
            
        except Exception as e:
            logger.error(f"添加块到内存向量存储失败: {str(e)}")
            raise
    
    async def search(self, query_embedding: List[float], limit: int = 5, **kwargs) -> List[TextChunk]:
        """
        搜索相似向量
        
        Args:
            query_embedding: 查询向量
            limit: 结果数量限制
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 相似块列表
        """
        if not self.chunks or not self.embeddings:
            return []
            
        try:
            # 计算所有嵌入的相似度
            similarities = {}
            for chunk_id, embedding in self.embeddings.items():
                similarity = self._cosine_similarity(query_embedding, embedding)
                similarities[chunk_id] = similarity
            
            # 按相似度排序
            sorted_ids = sorted(similarities.keys(), key=lambda x: similarities[x], reverse=True)
            
            # 取前limit个结果
            top_ids = sorted_ids[:limit]
            
            # 构建结果
            results = []
            for chunk_id in top_ids:
                # 获取块
                chunk = self.chunks[chunk_id]
                
                # 创建结果块
                result_chunk = TextChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                    score=similarities[chunk_id]
                )
                
                results.append(result_chunk)
            
            logger.debug(f"内存向量搜索返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"内存向量搜索失败: {str(e)}")
            raise
    
    async def delete(self, ids: List[str], **kwargs) -> bool:
        """
        删除向量
        
        Args:
            ids: 块ID列表
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功删除
        """
        if not ids:
            return True
            
        try:
            # 删除每个块
            for chunk_id in ids:
                if chunk_id in self.chunks:
                    del self.chunks[chunk_id]
                if chunk_id in self.embeddings:
                    del self.embeddings[chunk_id]
            
            logger.debug(f"已从内存向量存储删除 {len(ids)} 个块，剩余块数: {len(self.chunks)}")
            
            return True
            
        except Exception as e:
            logger.error(f"从内存向量存储删除块失败: {str(e)}")
            raise
    
    async def delete_by_document(self, doc_id: str, **kwargs) -> bool:
        """
        删除文档的所有块
        
        Args:
            doc_id: 文档ID
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功删除
        """
        try:
            # 查找属于该文档的所有块
            chunk_ids = [
                chunk_id for chunk_id, chunk in self.chunks.items()
                if chunk.doc_id == doc_id
            ]
            
            # 删除这些块
            return await self.delete(chunk_ids, **kwargs)
            
        except Exception as e:
            logger.error(f"删除文档块失败: {doc_id}, 错误: {str(e)}")
            return False
    
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

@register_component(RAGComponentRegistry.VECTOR_STORE, "qdrant")
class QdrantVectorStore(VectorStore[TextChunk, List[float]]):
    """Qdrant向量存储 - 使用Qdrant存储向量，适用于生产环境"""
    
    def __init__(
        self, 
        embedding_provider: Optional[EmbeddingProvider] = None,
        collection_name: str = "azure_docs",
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: int = 1536
    ):
        """
        初始化Qdrant向量存储
        
        Args:
            embedding_provider: 嵌入提供者，用于获取嵌入
            collection_name: 集合名称
            url: Qdrant服务URL
            api_key: Qdrant API密钥
            vector_size: 向量大小
        """
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.url = url
        self.api_key = api_key
        self.vector_size = vector_size
        self.client = None
        self.initialized = False
    
    async def _initialize(self):
        """初始化Qdrant客户端和集合"""
        if self.initialized:
            return
            
        try:
            # 安装包：pip install qdrant-client
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            
            # 创建客户端
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
            
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # 创建集合
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"已创建Qdrant集合: {self.collection_name}")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"初始化Qdrant客户端失败: {str(e)}")
            raise
    
    async def add(self, chunks: List[TextChunk], **kwargs) -> List[str]:
        """
        添加块到向量存储
        
        Args:
            chunks: 块列表
            **kwargs: 其他参数
            
        Returns:
            List[str]: 块ID列表
        """
        if not chunks:
            return []
            
        try:
            # 初始化
            await self._initialize()
            
            # 从qdrant_client导入需要的模型
            from qdrant_client.http import models
            
            chunk_ids = []
            points = []
            
            # 处理每个块
            for chunk in chunks:
                # 获取嵌入（如果需要）
                if chunk.embedding is None and self.embedding_provider:
                    chunk.embedding = await self.embedding_provider.get_embedding(chunk.content)
                
                if chunk.embedding:
                    # 准备元数据
                    metadata = {
                        "doc_id": chunk.doc_id,
                        "content": chunk.content,
                        "source": chunk.metadata.source,
                        "title": chunk.metadata.title or "",
                        "created_at": str(chunk.metadata.created_at) if chunk.metadata.created_at else "",
                        "modified_at": str(chunk.metadata.modified_at) if chunk.metadata.modified_at else "",
                    }
                    
                    # 添加额外元数据
                    for k, v in chunk.metadata.extra.items():
                        if isinstance(v, (str, int, float, bool)):
                            metadata[k] = v
                    
                    # 创建Qdrant点
                    point = models.PointStruct(
                        id=chunk.id,
                        vector=chunk.embedding,
                        payload=metadata
                    )
                    
                    points.append(point)
                    chunk_ids.append(chunk.id)
            
            # 批量添加点
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            
            logger.debug(f"已添加 {len(chunk_ids)} 个块到Qdrant向量存储")
            
            return chunk_ids
            
        except Exception as e:
            logger.error(f"添加块到Qdrant向量存储失败: {str(e)}")
            raise
    
    async def search(self, query_embedding: List[float], limit: int = 5, **kwargs) -> List[TextChunk]:
        """
        搜索相似向量
        
        Args:
            query_embedding: 查询向量
            limit: 结果数量限制
            **kwargs: 其他参数
            
        Returns:
            List[TextChunk]: 相似块列表
        """
        try:
            # 初始化
            await self._initialize()
            
            # 处理过滤器
            filter_expr = None
            if "filter" in kwargs:
                filter_expr = kwargs["filter"]
            
            # 执行搜索
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                filter=filter_expr
            )
            
            # 构建结果
            results = []
            for scored_point in search_result:
                # 从payload中获取数据
                payload = scored_point.payload
                
                # 创建元数据
                metadata = {
                    "source": payload.get("source", "unknown"),
                    "title": payload.get("title", ""),
                    "extra": {}
                }
                
                # 添加额外元数据
                for k, v in payload.items():
                    if k not in ["doc_id", "content", "source", "title", "created_at", "modified_at"]:
                        metadata["extra"][k] = v
                
                # 创建结果块
                result_chunk = TextChunk(
                    id=str(scored_point.id),
                    doc_id=payload.get("doc_id", "unknown"),
                    content=payload.get("content", ""),
                    metadata=metadata,
                    score=scored_point.score
                )
                
                results.append(result_chunk)
            
            logger.debug(f"Qdrant向量搜索返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant向量搜索失败: {str(e)}")
            raise
    
    async def delete(self, ids: List[str], **kwargs) -> bool:
        """
        删除向量
        
        Args:
            ids: 块ID列表
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功删除
        """
        if not ids:
            return True
            
        try:
            # 初始化
            await self._initialize()
            
            # 删除点
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            
            logger.debug(f"已从Qdrant向量存储删除 {len(ids)} 个块")
            
            return True
            
        except Exception as e:
            logger.error(f"从Qdrant向量存储删除块失败: {str(e)}")
            raise
    
    async def delete_by_document(self, doc_id: str, **kwargs) -> bool:
        """
        删除文档的所有块
        
        Args:
            doc_id: 文档ID
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功删除
        """
        try:
            # 初始化
            await self._initialize()
            
            # 创建过滤器
            from qdrant_client.http import models
            
            filter_expr = models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",
                        match=models.MatchValue(value=doc_id)
                    )
                ]
            )
            
            # 删除匹配的点
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_expr
            )
            
            logger.debug(f"已删除文档 {doc_id} 的块")
            
            return True
            
        except Exception as e:
            logger.error(f"删除文档块失败: {doc_id}, 错误: {str(e)}")
            return False