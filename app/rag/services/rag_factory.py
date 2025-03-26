"""
RAG服务工厂 - 创建RAG服务实例
"""

from typing import Optional, Dict, Any

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.siliconflow import SiliconFlowEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.llms.openrouter import OpenRouter
from llama_index.llms.deepseek import DeepSeek

from app.rag.core.config import RAGConfig, default_config
from app.rag.core.models import QueryResult, Document
from app.rag.adapters.llama_loaders import LlamaWebLoader
from app.rag.adapters.llama_retrievers import LlamaVectorRetriever
from app.rag.adapters.llama_stores import LlamaVectorStoreAdapter
from app.rag.custom.azure_retriever import AzureServiceRetriever
from app.rag.services.hybrid_rag_service import HybridRAGService
from app.services.llm_service import LLMService
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# 服务缓存
_service_instance = None

async def create_rag_service(
    llm_service: LLMService,
    config: Optional[RAGConfig] = None,
) -> HybridRAGService:
    """
    创建RAG服务实例，支持重用已缓存的实例
    
    Args:
        llm_service: LLM服务
        config: RAG配置，为None则使用默认配置
        
    Returns:
        HybridRAGService: 混合RAG服务
    """
    global _service_instance
    
    if _service_instance is not None:
        logger.debug("返回已缓存的RAG服务实例")
        return _service_instance
    
    # 使用提供的配置或默认配置
    config = config or default_config
    logger.info(f"创建新的RAG服务实例，模式: {config.mode}")
    
    embed_model = SiliconFlowEmbedding(
        model=config.llama_index.embed_model,
        api_key=settings.LLAMA_INDEX_EMBED_APIKEY,
        base_url=settings.LLAMA_INDEX_EMBED_URL,
    )
    
    # llm = OpenAI(
    #     model=config.llama_index.llm_model,
    #     api_key=settings.OPENAI_API_KEY,
    #     api_base=settings.OPENAI_API_BASE,
    # )
    llm = DeepSeek(
        model=config.llama_index.llm_model,
        api_key=settings.LLAMA_INDEX_LLM_APIKEY,
        api_base=settings.LLAMA_INDEX_LLM_BASEURL,
    )
    
    # 创建LlamaIndex节点解析器
    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=config.llama_index.chunk_size,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )
    
    # 创建LlamaIndex服务上下文
    LlamaSettings.llm = llm
    LlamaSettings.embed_model = embed_model
    LlamaSettings.node_parser = node_parser
    
    # 创建LlamaIndex存储上下文和索引
    index = VectorStoreIndex([])
    
    # 创建文档加载器
    web_loader = LlamaWebLoader()
    
    # 创建检索器
    vector_retriever = LlamaVectorRetriever(
        index=index,
        similarity_top_k=config.retriever_top_k,
        score_threshold=config.retriever_score_threshold,
    )
    
    # 创建Azure特定检索器
    azure_service_terms = {
        "Virtual Machine": ["VM", "虚拟机"],
        "App Service": ["应用服务", "网站服务", "Web服务"],
        "Azure Kubernetes Service": ["AKS", "k8s", "kubernetes"],
        "Azure SQL Database": ["SQL DB", "SQLDB", "SQL数据库"],
        "Cosmos DB": ["宇宙数据库", "文档数据库"],
        "Storage Account": ["存储账户", "存储"],
    }
    
    azure_retriever = AzureServiceRetriever(
        base_retriever=vector_retriever,
        service_terms=azure_service_terms,
    )
    
    # 创建向量存储适配器
    vector_store = LlamaVectorStoreAdapter(index=index)
    
    # 创建混合RAG服务
    service = HybridRAGService(
        llm_service=llm_service,
        llama_index=index,
        service_context=LlamaSettings,
        web_loader=web_loader,
        retriever=azure_retriever,
        vector_store=vector_store,
        config=config,
    )
    
    # 缓存服务实例
    _service_instance = service
    
    return service