"""
LlamaIndex存储适配器 - 将LlamaIndex存储适配到自定义接口
"""

from typing import List, Dict, Any, Optional, cast

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode, BaseNode, NodeWithScore
from llama_index.core.vector_stores.types import VectorStore as LlamaVectorStore

from app.rag.core.interfaces import VectorStore
from app.rag.core.models import TextChunk
from app.rag.adapters.llama_converters import to_llama_node, from_llama_nodes
from app.core.logging import get_logger

logger = get_logger(__name__)

class LlamaVectorStoreAdapter(VectorStore[TextChunk, List[float]]):
    """LlamaIndex向量存储适配器"""
    
    def __init__(self, index: VectorStoreIndex):
        """
        初始化LlamaIndex向量存储适配器
        
        Args:
            index: LlamaIndex向量索引
        """
        self.index = index
        self.vector_store = index._vector_store
        self.docstore = index._docstore
    
    async def add(self, chunks: List[TextChunk], **kwargs) -> List[str]:
        """
        添加块到向量存储
        
        Args:
            chunks: 块列表
            **kwargs: 额外参数
            
        Returns:
            List[str]: 块ID列表
        """
        if not chunks:
            return []
            
        logger.debug(f"添加 {len(chunks)} 个块到LlamaIndex向量存储")
        
        # 转换为LlamaIndex节点
        nodes = [to_llama_node(chunk) for chunk in chunks]
        
        # 添加到LlamaIndex索引
        try:
            # 添加到docstore
            self.docstore.add_documents(nodes)
            
            # 添加到向量存储
            node_ids = [node.id_ for node in nodes]
            node_embeddings = [node.embedding for node in nodes]
            
            # 检查所有节点是否都有嵌入
            for i, (node_id, embedding) in enumerate(zip(node_ids, node_embeddings)):
                if embedding is None:
                    logger.warning(f"节点 {node_id} 没有嵌入，将跳过")
                    node_ids.pop(i)
                    node_embeddings.pop(i)
            
            # 添加到向量存储
            if node_ids and node_embeddings:
                self.vector_store.add(node_ids, node_embeddings, nodes)
            
            logger.debug(f"已添加 {len(node_ids)} 个块到LlamaIndex向量存储")
            return node_ids
            
        except Exception as e:
            logger.error(f"添加块到LlamaIndex向量存储失败: {str(e)}")
            raise
    
    async def search(self, query_embedding: List[float], limit: int = 5, **kwargs) -> List[TextChunk]:
        """
        搜索相似向量
        
        Args:
            query_embedding: 查询向量
            limit: 返回结果数量上限
            **kwargs: 额外参数
            
        Returns:
            List[TextChunk]: 相似块列表
        """
        logger.debug(f"LlamaIndex向量搜索")
        
        try:
            # 使用LlamaIndex向量存储搜索
            node_ids_with_scores = self.vector_store.similarity_search(
                query_embedding, 
                similarity_top_k=limit,
                **kwargs
            )
            
            # 获取节点
            nodes_with_scores = []
            for node_id, score in node_ids_with_scores:
                node = self.docstore.get_node(node_id)
                nodes_with_scores.append((node, score))
            
            # 转换为带分数的节点
            nodes_with_score = [
                NodeWithScore(node=node, score=score)
                for node, score in nodes_with_scores
            ]
            
            # 转换为自定义块
            chunks = from_llama_nodes(nodes_with_score)
            
            logger.debug(f"LlamaIndex向量搜索结果: {len(chunks)} 个块")
            return chunks
            
        except Exception as e:
            logger.error(f"LlamaIndex向量搜索失败: {str(e)}")
            raise
    
    async def delete(self, ids: List[str], **kwargs) -> bool:
        """
        删除向量
        
        Args:
            ids: 块ID列表
            **kwargs: 额外参数
            
        Returns:
            bool: 是否成功删除
        """
        if not ids:
            return True
            
        logger.debug(f"从LlamaIndex向量存储删除 {len(ids)} 个块")
        
        try:
            # 从向量存储删除
            self.vector_store.delete(ids)
            
            # 从docstore删除
            for node_id in ids:
                try:
                    self.docstore.delete_document(node_id)
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"从LlamaIndex向量存储删除块失败: {str(e)}")
            raise