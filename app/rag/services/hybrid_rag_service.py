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
from app.services.llm.base import BaseLLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class HybridRAGService(RAGService[Document, QueryResult]):
    """混合RAG服务 - 结合多种组件的可配置RAG系统"""
    
    def __init__(
        self,
        llm_service: BaseLLMService,
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
                - batch_size: 嵌入批处理大小
                - skip_embedding: 是否跳过嵌入处理
                - custom_chunks: 自定义提供的文本块

        Returns:
            str: 文档ID
        """
        logger.info(f"添加文档: {document.metadata.title or 'Untitled'}")

        try:
            # 检查是否提供了自定义块
            custom_chunks = kwargs.get("custom_chunks")
            if custom_chunks:
                logger.debug(f"使用 {len(custom_chunks)} 个提供的自定义块")
                chunks = custom_chunks
            else:
                # 使用分块器处理文档
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

            # 检查是否需要跳过嵌入处理
            skip_embedding = kwargs.get("skip_embedding", False)

            if not skip_embedding and self.embedder:
                # 获取批处理大小
                batch_size = kwargs.get("batch_size", 10)

                # 批量处理嵌入
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    texts = [chunk.content for chunk in batch]

                    try:
                        # 执行批量嵌入
                        embeddings = await self.embedder.get_embeddings(texts)

                        # 设置嵌入
                        for j, embedding in enumerate(embeddings):
                            batch[j].embedding = embedding

                        logger.debug(
                            f"执行批量嵌入: 处理批次 {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}, 大小: {len(batch)}")
                    except Exception as e:
                        logger.error(f"批量嵌入失败，批次 {i // batch_size + 1}: {str(e)}")
                        # 尝试逐个处理
                        for j, chunk in enumerate(batch):
                            try:
                                chunk.embedding = self.embedder.get_embedding(chunk.content)
                                logger.debug(f"单独处理块 {i + j + 1}/{len(chunks)} 成功")
                            except Exception as sub_e:
                                logger.error(f"处理块 {i + j + 1} 失败: {str(sub_e)}")

            # 将块添加到向量存储
            if self.vector_store:
                # 检查每个块是否有嵌入
                valid_chunks = [c for c in chunks if c.embedding is not None or skip_embedding]
                if valid_chunks:
                    chunk_ids = await self.vector_store.add(valid_chunks)
                    logger.debug(f"已添加 {len(chunk_ids)}/{len(chunks)} 个块到向量存储")

                    if len(valid_chunks) < len(chunks):
                        logger.warning(f"跳过了 {len(chunks) - len(valid_chunks)} 个没有嵌入的块")
                else:
                    logger.warning(f"没有有效块可添加到向量存储，所有 {len(chunks)} 个块都缺少嵌入")

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
            # 方法1: 使用向量存储的delete_by_document方法（如果可用）
            if self.vector_store and hasattr(self.vector_store, "delete_by_document"):
                success = await self.vector_store.delete_by_document(doc_id)
                if success:
                    logger.info(f"文档已删除: {doc_id}")
                    return True

            # 方法2: 使用检索器搜索文档相关块，然后删除这些块
            # 构造一个特殊查询以查找文档的块
            doc_query = f"docid:{doc_id}"
            try:
                chunks = await self.retriever.retrieve(doc_query, limit=100, filter={"doc_id": doc_id})
                if chunks:
                    chunk_ids = [chunk.id for chunk in chunks]
                    if self.vector_store:
                        success = await self.vector_store.delete(chunk_ids)
                        logger.info(f"已删除文档 {doc_id} 的 {len(chunk_ids)} 个块")
                        return success
            except Exception as e:
                logger.warning(f"通过检索删除文档 {doc_id} 的块失败: {str(e)}")

            # 方法3: 最后的回退策略 - 使用自定义查询从向量数据库中直接查找
            if self.vector_store:
                try:
                    # 尝试使用向量存储的底层搜索能力
                    deleted = await self._fallback_delete_by_metadata(doc_id)
                    if deleted:
                        logger.info(f"通过元数据查询删除文档 {doc_id} 成功")
                        return True
                except Exception as e:
                    logger.warning(f"通过元数据查询删除失败: {str(e)}")

            logger.warning(f"无法删除文档 {doc_id}，尝试了所有可用方法")
            return False

        except Exception as e:
            logger.error(f"删除文档失败: {doc_id}, 错误: {str(e)}")
            return False

    async def _fallback_delete_by_metadata(self, doc_id: str) -> bool:
        """
        尝试通过元数据查询删除文档相关的向量

        Args:
            doc_id: 文档ID

        Returns:
            bool: 是否成功删除
        """
        # 这是一个通用实现，具体实现可能需要根据向量存储类型调整
        try:
            # 假设向量存储支持某种形式的元数据查询
            # 例如，在Qdrant中使用filter参数
            if hasattr(self.vector_store, "delete") and hasattr(self.vector_store, "search"):
                # 搜索文档ID相关的所有向量
                dummy_vector = [0.0] * 1536  # 创建一个假向量，主要是为了使用filter参数
                results = await self.vector_store.search(
                    dummy_vector,
                    limit=1000,
                    filter={"doc_id": doc_id}  # 这种过滤器形式取决于具体向量存储的实现
                )

                if results:
                    # 提取ID并删除
                    ids_to_delete = [result.id for result in results]
                    return await self.vector_store.delete(ids_to_delete)

            return False
        except Exception as e:
            logger.error(f"通用元数据删除方法失败: {str(e)}")
            return False

    def _prepare_context(self, query: str, chunks: List[TextChunk]) -> str:
        """
        准备查询上下文，根据查询类型优化呈现

        Args:
            query: 查询
            chunks: 文本块列表

        Returns:
            str: 格式化的上下文文本
        """
        # 确定查询类型
        query_type = self._determine_query_type(query)

        # 根据不同查询类型组织上下文
        if query_type == "比较":
            return self._prepare_comparison_context(query, chunks)
        elif query_type == "定价":
            return self._prepare_pricing_context(query, chunks)
        elif query_type == "技术":
            return self._prepare_technical_context(query, chunks)
        else:
            # 默认上下文处理
            context_parts = []
            for i, chunk in enumerate(chunks):
                context_parts.append(f"内容 {i + 1}:\n{chunk.content}")

            return "\n\n".join(context_parts)

    def _determine_query_type(self, query: str) -> str:
        """
        确定查询类型

        Args:
            query: 查询文本

        Returns:
            str: 查询类型
        """
        query_lower = query.lower()

        # 比较查询
        if any(term in query_lower for term in ["比较", "对比", "区别", "差异", "优缺点", "vs", "versus", "哪个更好"]):
            return "比较"

        # 定价查询
        if any(term in query_lower for term in ["价格", "定价", "成本", "费用", "多少钱", "报价", "价格表"]):
            return "定价"

        # 技术查询
        if any(term in query_lower for term in ["怎么", "如何", "配置", "设置", "架构", "原理", "实现", "技术"]):
            return "技术"

        # 默认类型
        return "一般"

    def _prepare_comparison_context(self, query: str, chunks: List[TextChunk]) -> str:
        """准备比较查询的上下文"""
        # 查找要比较的服务
        import re
        services = re.findall(r'(Azure[a-zA-Z\s]+|[A-Z][a-zA-Z\s]+Service)', query)

        # 按服务分组
        service_chunks = {}
        for chunk in chunks:
            for service in services:
                if service.lower() in chunk.content.lower():
                    if service not in service_chunks:
                        service_chunks[service] = []
                    service_chunks[service].append(chunk)

        # 构建上下文
        context_parts = []

        # 先添加包含多个服务的块（可能是直接比较内容）
        multi_service_chunks = []
        for chunk in chunks:
            matched_services = [s for s in services if s.lower() in chunk.content.lower()]
            if len(matched_services) > 1:
                multi_service_chunks.append(chunk)

        if multi_service_chunks:
            context_parts.append("比较信息:")
            for i, chunk in enumerate(multi_service_chunks):
                context_parts.append(f"比较 {i + 1}:\n{chunk.content}")

        # 然后按服务添加专门的块
        for service in services:
            if service in service_chunks:
                context_parts.append(f"\n{service} 信息:")
                for i, chunk in enumerate(service_chunks[service][:3]):  # 限制每个服务最多3个块
                    context_parts.append(f"{service} {i + 1}:\n{chunk.content}")

        return "\n\n".join(context_parts)

    def _prepare_pricing_context(self, query: str, chunks: List[TextChunk]) -> str:
        """准备定价查询的上下文"""
        # 查找价格相关块并置顶
        pricing_chunks = []
        other_chunks = []

        for chunk in chunks:
            if any(term in chunk.content.lower() for term in
                   ["价格", "定价", "成本", "费用", "元", "美元", "人民币", "港币"]):
                pricing_chunks.append(chunk)
            else:
                other_chunks.append(chunk)

        # 构建上下文
        context_parts = []

        # 先添加价格相关块
        if pricing_chunks:
            context_parts.append("价格信息:")
            for i, chunk in enumerate(pricing_chunks):
                context_parts.append(f"价格 {i + 1}:\n{chunk.content}")

        # 再添加其他块
        if other_chunks:
            context_parts.append("\n其他相关信息:")
            for i, chunk in enumerate(other_chunks):
                context_parts.append(f"其他 {i + 1}:\n{chunk.content}")

        return "\n\n".join(context_parts)

    def _prepare_technical_context(self, query: str, chunks: List[TextChunk]) -> str:
        """准备技术查询的上下文"""
        # 这里可以添加特定的技术查询处理逻辑
        # 例如，可以优先考虑包含代码、配置示例和步骤说明的块

        # 简单示例实现
        context_parts = []

        # 识别并优先处理包含技术细节的块
        technical_chunks = []
        other_chunks = []

        for chunk in chunks:
            content_lower = chunk.content.lower()
            # 检查是否包含技术指标
            if any(term in content_lower for term in ["步骤", "配置", "参数", "命令", "代码", "示例", "如何", "操作"]):
                technical_chunks.append(chunk)
            else:
                other_chunks.append(chunk)

        # 先添加技术块
        if technical_chunks:
            context_parts.append("技术细节:")
            for i, chunk in enumerate(technical_chunks):
                context_parts.append(f"细节 {i + 1}:\n{chunk.content}")

        # 再添加其他块
        if other_chunks:
            context_parts.append("\n补充信息:")
            for i, chunk in enumerate(other_chunks):
                context_parts.append(f"信息 {i + 1}:\n{chunk.content}")

        return "\n\n".join(context_parts)