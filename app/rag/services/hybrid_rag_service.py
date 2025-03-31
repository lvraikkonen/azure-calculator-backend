"""
混合RAG服务 - 结合LlamaIndex和自定义逻辑的RAG服务
适配组件注册表和配置系统
"""

from typing import List, Dict, Any, Optional, Union
import time

from app.rag.core.interfaces import RAGService, DocumentLoader, Retriever, EmbeddingProvider, ContentProcessor
from app.rag.core.interfaces import QueryTransformer, Generator
from app.rag.core.models import Document, TextChunk, QueryResult, Source
from app.rag.core.config import RAGConfig, default_config
from app.rag.evaluation.evaluator import RAGEvaluator
from app.services.llm_service import LLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class HybridRAGService(RAGService[Document, QueryResult]):
    """混合RAG服务 - 结合多种组件的可配置RAG系统"""
    
    def __init__(
        self,
        llm_service: LLMService,
        config: RAGConfig = default_config,
        embedder: Optional[EmbeddingProvider] = None,
        chunker: Optional[ContentProcessor] = None,
        retriever: Optional[Retriever] = None,
        vector_store: Optional[Any] = None,
        generator: Optional[Generator] = None,
        document_loader: Optional[DocumentLoader] = None,
        query_transformer: Optional[QueryTransformer] = None,
        evaluator: Optional[RAGEvaluator] = None
    ):
        """
        初始化混合RAG服务
        
        Args:
            llm_service: LLM服务
            config: RAG配置
            embedder: 嵌入模型
            chunker: 分块器
            retriever: 检索器
            vector_store: 向量存储
            generator: 生成器
            document_loader: 文档加载器
            query_transformer: 查询转换器
            evaluator: 评估器
        """
        self.llm_service = llm_service
        self.config = config
        self.embedder = embedder
        self.chunker = chunker
        self.retriever = retriever
        self.vector_store = vector_store
        self.generator = generator
        self.document_loader = document_loader
        self.query_transformer = query_transformer
        self.evaluator = evaluator
        
        logger.info(f"初始化HybridRAGService, 模式: {config.mode}")
    
    async def query(self, query: str, **kwargs) -> QueryResult:
        """
        执行RAG查询
        
        Args:
            query: 查询文本
            **kwargs: 附加参数
            
        Returns:
            QueryResult: 查询结果
        """
        start_time = time.time()
        logger.info(f"RAG查询: {query}")
        
        # 记录查询指标
        metrics = {
            "start_time": start_time
        }
        
        # 1. 转换查询（如果启用）
        transformed_query = query
        if self.query_transformer:
            try:
                transform_start = time.time()
                transformed_query = await self.query_transformer.transform(query)
                metrics["transform_time"] = time.time() - transform_start
                
                if transformed_query != query:
                    logger.debug(f"查询转换: '{query}' -> '{transformed_query}'")
            except Exception as e:
                logger.error(f"查询转换失败: {str(e)}")
        
        # 2. 检索相关内容
        retrieve_start = time.time()
        top_k = kwargs.get("top_k", self.config.retriever.top_k)
        
        try:
            chunks = await self.retriever.retrieve(transformed_query, limit=top_k, **kwargs)
            metrics["retrieve_time"] = time.time() - retrieve_start
            
            logger.debug(f"检索到 {len(chunks)} 个块")
            
            if not chunks:
                logger.warning(f"未找到相关内容: {transformed_query}")
                
                # 使用普通LLM回复
                message = await self.llm_service.chat(
                    f"用户问了关于Azure云服务的问题，但我们没有找到相关内容。问题是：{query}",
                    conversation_history=kwargs.get("conversation_history", [])
                )
                
                # 构建结果
                result = QueryResult(
                    query=query,
                    chunks=[],
                    answer=message.content,
                    sources=[],
                    metadata={
                        "mode": "llm_only",
                        "retrieval_method": "none", 
                        "metrics": metrics
                    }
                )
                
                metrics["total_time"] = time.time() - start_time
                result.metadata["metrics"] = metrics
                
                return result
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            
            # 使用普通LLM回复
            message = await self.llm_service.chat(
                f"用户问了关于Azure云服务的问题，但检索过程出现问题。问题是：{query}",
                conversation_history=kwargs.get("conversation_history", [])
            )
            
            # 构建结果
            result = QueryResult(
                query=query,
                chunks=[],
                answer=message.content,
                sources=[],
                metadata={
                    "mode": "llm_only",
                    "retrieval_method": "error", 
                    "error": str(e),
                    "metrics": metrics
                }
            )
            
            metrics["total_time"] = time.time() - start_time
            result.metadata["metrics"] = metrics
            
            return result
        
        # 3. 生成回答
        if self.generator:
            try:
                generate_start = time.time()
                answer = await self.generator.generate(transformed_query, chunks, **kwargs)
                metrics["generate_time"] = time.time() - generate_start
            except Exception as e:
                logger.error(f"生成回答失败: {str(e)}")
                
                # 简单回退方案
                answer = "抱歉，我无法基于检索到的内容生成回答。请尝试重新表述您的问题。"
        else:
            # 使用简单提示词
            context = self._prepare_context(transformed_query, chunks)
            
            # 构造提示词
            prompt = f"""
            请基于以下内容回答用户的问题。如果提供的内容中没有相关信息，请说明无法回答，不要编造信息。
            
            内容:
            {context}
            
            用户问题: {query}
            
            在回答中，请引用内容的编号，例如"根据内容2..."。确保你的回答准确且基于提供的内容。特别注意Azure云服务的价格、特性和使用场景。
            """
            
            generate_start = time.time()
            message = await self.llm_service.chat(prompt, conversation_history=[])
            metrics["generate_time"] = time.time() - generate_start
            
            answer = message.content
        
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
        result = QueryResult(
            query=query,
            chunks=chunks,
            answer=answer,
            sources=sources,
            metadata={
                "mode": self.config.mode,
                "retrieval_method": self.config.retriever.type,
                "metrics": metrics
            }
        )
        
        # 记录总时间
        metrics["total_time"] = time.time() - start_time
        result.metadata["metrics"] = metrics
        
        # 评估结果（如果启用）
        if self.evaluator and self.config.evaluation.enabled:
            try:
                eval_start = time.time()
                eval_result = await self.evaluator.evaluate(
                    result, 
                    metrics=self.config.evaluation.metrics
                )
                metrics["evaluation_time"] = time.time() - eval_start
                
                # 添加评估结果
                result.metadata["evaluation"] = eval_result.to_dict()
                
            except Exception as e:
                logger.error(f"评估失败: {str(e)}")
        
        return result
    
    async def add_document(self, document: Document, **kwargs) -> str:
        """
        添加文档到知识库
        
        Args:
            document: 文档
            **kwargs: 附加参数
            
        Returns:
            str: 文档ID
        """
        logger.info(f"添加文档: {document.metadata.title or 'Untitled'}")
        
        try:
            # 1. 使用分块器处理文档
            if self.chunker:
                chunks = await self.chunker.process([document])
                logger.debug(f"文档分为 {len(chunks)} 个块")
            else:
                # 简单分块，将整个文档作为一个块
                chunks = [
                    TextChunk(
                        id=f"{document.id}_chunk_1",
                        doc_id=document.id,
                        content=document.content,
                        metadata=document.metadata
                    )
                ]
            
            # 2. 为每个块生成嵌入
            if self.embedder:
                texts = [chunk.content for chunk in chunks]
                embeddings = await self.embedder.get_embeddings(texts)
                
                # 设置嵌入
                for i, embedding in enumerate(embeddings):
                    chunks[i].embedding = embedding
            
            # 3. 将块添加到向量存储
            if self.vector_store:
                chunk_ids = await self.vector_store.add(chunks)
                logger.debug(f"已添加 {len(chunk_ids)} 个块到向量存储")
            
            logger.info(f"文档已添加: {document.id}")
            return document.id
            
        except Exception as e:
            logger.error(f"添加文档失败: {document.id}, 错误: {str(e)}")
            raise
    
    async def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """
        批量添加文档到知识库
        
        Args:
            documents: 文档列表
            **kwargs: 附加参数
            
        Returns:
            List[str]: 文档ID列表
        """
        logger.info(f"批量添加 {len(documents)} 个文档")
        
        doc_ids = []
        for doc in documents:
            try:
                doc_id = await self.add_document(doc, **kwargs)
                doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"添加文档失败: {doc.id}, 错误: {str(e)}")
        
        return doc_ids
    
    async def delete_document(self, doc_id: str, **kwargs) -> bool:
        """
        从知识库删除文档
        
        Args:
            doc_id: 文档ID
            **kwargs: 附加参数
            
        Returns:
            bool: 是否成功删除
        """
        logger.info(f"删除文档: {doc_id}")
        
        try:
            # 根据文档ID获取所有相关块ID
            # 这部分实现依赖于具体的向量存储
            # TODO: 实现更通用的方法
            
            if self.vector_store:
                # 假设向量存储有根据文档ID删除的方法
                if hasattr(self.vector_store, "delete_by_document"):
                    result = await self.vector_store.delete_by_document(doc_id)
                    logger.info(f"文档已删除: {doc_id}")
                    return result
                else:
                    logger.warning(f"向量存储不支持按文档ID删除，将尝试查找并删除块")
                    # 具体实现取决于向量存储支持的查询功能
            
            logger.warning(f"无法删除文档，未实现的功能: {doc_id}")
            return False
            
        except Exception as e:
            logger.error(f"删除文档失败: {doc_id}, 错误: {str(e)}")
            return False
    
    def _prepare_context(self, query: str, chunks: List[TextChunk]) -> str:
        """
        准备查询上下文
        
        Args:
            query: 查询
            chunks: 文本块列表
            
        Returns:
            str: 格式化的上下文文本
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            context_parts.append(f"内容 {i+1}:\n{chunk.content}")
        
        return "\n\n".join(context_parts)