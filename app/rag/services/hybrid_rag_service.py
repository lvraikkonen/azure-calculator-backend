"""
混合RAG服务 - 结合LlamaIndex和自定义逻辑的RAG服务
"""

from typing import List, Dict, Any, Optional, Union, cast
import json

from llama_index.core import VectorStoreIndex, ServiceContext

from app.rag.core.interfaces import RAGService, DocumentLoader, Retriever, VectorStore
from app.rag.core.models import Document, TextChunk, QueryResult, Source
from app.rag.core.config import RAGConfig, default_config
from app.rag.adapters.llama_converters import to_llama_document, from_llama_nodes
from app.services.llm_service import LLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class HybridRAGService(RAGService[Document, QueryResult]):
    """混合RAG服务 - 结合LlamaIndex和自定义逻辑"""
    
    def __init__(
        self,
        llm_service: LLMService,
        llama_index: VectorStoreIndex,
        service_context: ServiceContext,
        web_loader: DocumentLoader[Document],
        retriever: Retriever[TextChunk],
        vector_store: VectorStore[TextChunk, List[float]],
        config: RAGConfig = default_config,
    ):
        """
        初始化混合RAG服务
        
        Args:
            llm_service: LLM服务
            llama_index: LlamaIndex向量索引
            service_context: LlamaIndex服务上下文
            web_loader: 网页加载器
            retriever: 检索器
            vector_store: 向量存储
            config: RAG配置
        """
        self.llm_service = llm_service
        self.llama_index = llama_index
        self.service_context = service_context
        self.web_loader = web_loader
        self.retriever = retriever
        self.vector_store = vector_store
        self.config = config
    
    async def query(self, query: str, **kwargs) -> QueryResult:
        """
        执行RAG查询
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            QueryResult: 查询结果
        """
        logger.info(f"RAG查询: {query}")
        
        # 使用设置的检索器检索内容
        top_k = kwargs.get("top_k", self.config.retriever_top_k)
        chunks = await self.retriever.retrieve(query, limit=top_k)
        
        if not chunks:
            logger.warning(f"未找到相关内容: {query}")
            
            # 使用普通LLM回复
            message = await self.llm_service.chat(
                f"用户问了关于Azure云服务的问题，但我们没有找到相关内容。问题是：{query}",
                conversation_history=kwargs.get("conversation_history", [])
            )
            
            return QueryResult(
                query=query,
                chunks=[],
                answer=message.content,
                sources=[],
                metadata={"retrieval_method": "none"}
            )
        
        # 根据配置选择RAG方法
        if self.config.mode == "llama_index":
            return await self._llama_index_query(query, chunks, **kwargs)
        elif self.config.mode == "custom":
            return await self._custom_query(query, chunks, **kwargs)
        else:  # hybrid模式
            return await self._hybrid_query(query, chunks, **kwargs)
    
    async def add_document(self, document: Document, **kwargs) -> str:
        """
        添加文档到知识库
        
        Args:
            document: 文档
            **kwargs: 额外参数
            
        Returns:
            str: 文档ID
        """
        # 使用LlamaIndex处理和索引文档
        logger.info(f"添加文档到知识库: {document.metadata.title or 'Untitled'}")
        
        # 转换为LlamaIndex文档
        llama_doc = to_llama_document(document)
        
        # 使用LlamaIndex索引文档
        self.llama_index.insert(llama_doc)
        
        logger.info(f"文档已添加: {document.id}")
        return document.id
    
    async def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """
        批量添加文档到知识库
        
        Args:
            documents: 文档列表
            **kwargs: 额外参数
            
        Returns:
            List[str]: 文档ID列表
        """
        # 批量添加文档
        logger.info(f"批量添加 {len(documents)} 个文档到知识库")
        
        doc_ids = []
        for doc in documents:
            doc_id = await self.add_document(doc, **kwargs)
            doc_ids.append(doc_id)
        
        return doc_ids
    
    async def delete_document(self, doc_id: str, **kwargs) -> bool:
        """
        从知识库删除文档
        
        Args:
            doc_id: 文档ID
            **kwargs: 额外参数
            
        Returns:
            bool: 是否成功删除
        """
        logger.info(f"删除文档: {doc_id}")
        
        try:
            # LlamaIndex目前没有直接删除文档的API
            # 我们需要通过向量存储删除
            # 1. 找到所有与该文档关联的块
            # 2. 删除这些块
            
            # 获取该文档的所有块ID
            # 需要获取docstore中的所有节点，过滤出doc_id=doc_id的节点
            docstore = self.llama_index._docstore
            chunk_ids = []
            
            # 遍历docstore中的所有节点
            for node_id, node in docstore._nodes.items():
                if node.metadata and node.metadata.get("doc_id") == doc_id:
                    chunk_ids.append(node_id)
            
            if not chunk_ids:
                logger.warning(f"未找到与文档 {doc_id} 相关的块")
                return False
            
            # 删除这些块
            await self.vector_store.delete(chunk_ids)
            
            logger.info(f"文档已删除: {doc_id}, 删除了 {len(chunk_ids)} 个块")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {doc_id}, 错误: {str(e)}")
            return False
    
    async def _llama_index_query(self, query: str, chunks: List[TextChunk], **kwargs) -> QueryResult:
        """使用LlamaIndex执行查询"""
        try:
            # 使用LlamaIndex查询引擎
            query_engine = self.llama_index.as_query_engine(
                response_mode=self.config.llama_index.response_mode,
                streaming=False,
            )
            
            # 执行查询
            response = await query_engine.aquery(query)
            
            # 转换检索到的节点
            retrieved_chunks = from_llama_nodes(response.source_nodes)
            
            # 准备来源引用
            sources = []
            for i, chunk in enumerate(retrieved_chunks):
                source = Source(
                    id=str(i+1),
                    document_id=chunk.doc_id,
                    title=chunk.metadata.title or "未知标题",
                    source=chunk.metadata.source,
                    score=chunk.score
                )
                sources.append(source)
            
            # 构建查询结果
            result = QueryResult(
                query=query,
                chunks=retrieved_chunks,
                answer=response.response,
                sources=sources,
                raw_response=None,
                metadata={
                    "mode": "llama_index",
                    "response_mode": self.config.llama_index.response_mode,
                    "chunks_found": len(retrieved_chunks)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LlamaIndex查询失败: {str(e)}")
            # 回退到自定义查询
            return await self._custom_query(query, chunks, **kwargs)
    
    async def _custom_query(self, query: str, chunks: List[TextChunk], **kwargs) -> QueryResult:
        """使用自定义逻辑执行查询"""
        # 准备上下文
        context = self._prepare_context(query, chunks)
        
        # 构造提示词
        prompt = f"""
        请基于以下内容回答用户的问题。如果提供的内容中没有相关信息，请说明无法回答，不要编造信息。
        
        内容:
        {context}
        
        用户问题: {query}
        
        在回答中，请引用内容的编号，例如"根据内容2..."。确保你的回答准确且基于提供的内容。特别注意Azure云服务的价格、特性和使用场景。
        """
        
        # 调用LLM
        try:
            message = await self.llm_service.chat(
                prompt,
                conversation_history=[]  # 不使用历史，这是一个独立查询
            )
            
            # 准备来源引用
            sources = []
            for i, chunk in enumerate(chunks):
                source = Source(
                    id=str(i+1),
                    document_id=chunk.doc_id,
                    title=chunk.metadata.title or "未知标题",
                    source=chunk.metadata.source,
                    score=chunk.score
                )
                sources.append(source)
            
            # 构建查询结果
            return QueryResult(
                query=query,
                chunks=chunks,
                answer=message.content,
                sources=sources,
                metadata={
                    "mode": "custom",
                    "chunks_found": len(chunks)
                }
            )
            
        except Exception as e:
            logger.error(f"自定义查询失败: {str(e)}")
            raise
    
    async def _hybrid_query(self, query: str, chunks: List[TextChunk], **kwargs) -> QueryResult:
        """使用混合方法执行查询，选择最佳策略"""
        # 分析查询类型，选择合适的方法
        if self._is_comparison_query(query):
            # 比较查询通常需要更结构化的回答，使用自定义逻辑
            logger.debug(f"检测到比较查询，使用自定义查询: {query}")
            return await self._custom_query(query, chunks, **kwargs)
        elif self._is_pricing_query(query):
            # 定价查询需要提取和计算价格信息，也使用自定义逻辑
            logger.debug(f"检测到定价查询，使用自定义查询: {query}")
            return await self._custom_query(query, chunks, **kwargs)
        else:
            # 其他类型的查询使用LlamaIndex
            logger.debug(f"使用LlamaIndex查询: {query}")
            try:
                return await self._llama_index_query(query, chunks, **kwargs)
            except Exception:
                # 如果LlamaIndex查询失败，回退到自定义查询
                logger.warning(f"LlamaIndex查询失败，回退到自定义查询: {query}")
                return await self._custom_query(query, chunks, **kwargs)
    
    def _prepare_context(self, query: str, chunks: List[TextChunk]) -> str:
        """准备查询上下文"""
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            context_parts.append(f"内容 {i+1}:\n{chunk.content}")
        
        return "\n\n".join(context_parts)
    
    def _is_comparison_query(self, query: str) -> bool:
        """检查是否为比较查询"""
        comparison_terms = ["比较", "对比", "区别", "差异", "优缺点", "vs", "versus", "哪个更好"]
        return any(term in query for term in comparison_terms)
    
    def _is_pricing_query(self, query: str) -> bool:
        """检查是否为定价查询"""
        pricing_terms = ["价格", "定价", "成本", "费用", "多少钱", "报价", "价格表"]
        return any(term in query for term in pricing_terms)