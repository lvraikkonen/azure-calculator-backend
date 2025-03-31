"""
嵌入模型组件 - 提供文本向量表示服务
"""
from typing import List, Dict, Any, Optional
from app.rag.core.registry import register_component, RAGComponentRegistry
from app.rag.core.interfaces import EmbeddingProvider
from app.core.logging import get_logger

logger = get_logger(__name__)

@register_component(RAGComponentRegistry.EMBEDDER, "silicon_flow")
class SiliconFlowEmbedder(EmbeddingProvider[List[float]]):
    """SiliconFlow嵌入模型"""
    
    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        """
        初始化SiliconFlow嵌入模型
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: 可选的API基础URL
        """
        from llama_index.embeddings.siliconflow import SiliconFlowEmbedding
        
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        
        self.embed_model = SiliconFlowEmbedding(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取单个文本嵌入"""
        try:
            embedding = await self.embed_model.aget_text_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"获取嵌入失败: {str(e)}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取多个文本嵌入"""
        try:
            embeddings = await self.embed_model.aget_text_embedding_batch(texts)
            return embeddings
        except Exception as e:
            logger.error(f"批量获取嵌入失败: {str(e)}")
            raise

@register_component(RAGComponentRegistry.EMBEDDER, "openai")
class OpenAIEmbedder(EmbeddingProvider[List[float]]):
    """OpenAI嵌入模型"""
    
    def __init__(self, model: str, api_key: str, api_base: Optional[str] = None):
        """
        初始化OpenAI嵌入模型
        
        Args:
            model: 模型名称
            api_key: API密钥
            api_base: 可选的API基础URL
        """
        from llama_index.embeddings.openai import OpenAIEmbedding
        
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        
        self.embed_model = OpenAIEmbedding(
            model=model,
            api_key=api_key,
            api_base=api_base,
        )
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取单个文本嵌入"""
        try:
            embedding = await self.embed_model.aget_text_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"获取嵌入失败: {str(e)}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取多个文本嵌入"""
        try:
            embeddings = await self.embed_model.aget_text_embedding_batch(texts)
            return embeddings
        except Exception as e:
            logger.error(f"批量获取嵌入失败: {str(e)}")
            raise