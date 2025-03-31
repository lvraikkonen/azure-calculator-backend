"""
抽象接口层 - 定义框架无关的RAG接口
允许LlamaIndex和自定义组件的无缝交互
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Generic, TypeVar

# 类型变量，用于泛型
T = TypeVar('T')
D = TypeVar('D')  # 文档类型
C = TypeVar('C')  # 块类型
E = TypeVar('E')  # 嵌入类型
R = TypeVar('R')  # 结果类型

class DocumentLoader(ABC, Generic[D]):
    """文档加载器接口 - 从不同来源加载文档"""
    
    @abstractmethod
    async def load(self, source: str, **kwargs) -> List[D]:
        """加载文档"""
        pass

class ContentProcessor(ABC, Generic[D, C]):
    """内容处理器接口 - 将文档处理为可索引单元"""
    
    @abstractmethod
    async def process(self, documents: List[D], **kwargs) -> List[C]:
        """处理文档"""
        pass

class EmbeddingProvider(ABC, Generic[E]):
    """嵌入提供者接口 - 将文本转换为向量表示"""
    
    @abstractmethod
    async def get_embedding(self, text: str) -> E:
        """获取单个文本嵌入"""
        pass
    
    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[E]:
        """获取多个文本嵌入"""
        pass

class VectorStore(ABC, Generic[C, E]):
    """向量存储接口 - 存储和检索内容向量"""
    
    @abstractmethod
    async def add(self, chunks: List[C], **kwargs) -> List[str]:
        """添加块到向量存储"""
        pass
    
    @abstractmethod
    async def search(self, query_embedding: E, limit: int = 5, **kwargs) -> List[C]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str], **kwargs) -> bool:
        """删除向量"""
        pass


class QueryTransformer(ABC):
    """查询转换器接口 - 增强和转换用户查询"""

    @abstractmethod
    async def transform(self, query: str) -> str:
        """
        转换查询

        Args:
            query: 原始查询

        Returns:
            str: 转换后的查询
        """
        pass


class Generator(ABC, Generic[C]):
    """生成器接口 - 基于检索内容生成回答"""

    @abstractmethod
    async def generate(self, query: str, chunks: List[C], **kwargs) -> str:
        """
        生成回答

        Args:
            query: 查询文本
            chunks: 检索结果
            **kwargs: 其他参数

        Returns:
            str: 生成的回答
        """
        pass

class Retriever(ABC, Generic[C]):
    """检索器接口 - 检索相关内容"""
    
    @abstractmethod
    async def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[C]:
        """检索相关内容"""
        pass

class PromptBuilder(ABC):
    """提示词构建器接口 - 构建RAG提示词"""
    
    @abstractmethod
    async def build(self, query: str, contexts: List[Any], **kwargs) -> str:
        """构建提示词"""
        pass

class RAGService(ABC, Generic[D, R]):
    """RAG服务接口 - 提供整合的RAG功能"""
    
    @abstractmethod
    async def query(self, query: str, **kwargs) -> R:
        """执行RAG查询"""
        pass
    
    @abstractmethod
    async def add_document(self, document: D, **kwargs) -> str:
        """添加文档到知识库"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[D], **kwargs) -> List[str]:
        """批量添加文档到知识库"""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str, **kwargs) -> bool:
        """从知识库删除文档"""
        pass