"""
RAG服务工厂 - 使用新的组件注册表和配置系统
"""
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from app.rag.core.registry import RAGComponentRegistry
from app.rag.core.config import RAGConfig, default_config
from app.rag.services.hybrid_rag_service import HybridRAGService
from app.rag.evaluation.evaluator import RAGEvaluator
from app.services.llm_service import LLMService
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# 服务缓存
_service_instance = None
_evaluator_instance = None

async def create_rag_service(
    llm_service: LLMService,
    config: Optional[Union[RAGConfig, str, Path]] = None,
    component_overrides: Optional[Dict[str, Any]] = None,
    force_new: bool = False
) -> HybridRAGService:
    """
    创建RAG服务实例，支持重用已缓存的实例
    
    Args:
        llm_service: LLM服务
        config: RAG配置，为None则使用默认配置
        component_overrides: 组件覆盖，用于自定义组件
        force_new: 强制创建新实例，不使用缓存
        
    Returns:
        HybridRAGService: 混合RAG服务
    """
    global _service_instance
    
    if _service_instance is not None and not force_new:
        logger.debug("返回已缓存的RAG服务实例")
        return _service_instance
    
    # 处理配置
    if isinstance(config, (str, Path)):
        # 从文件加载配置
        config = RAGConfig.from_file(config)
    elif config is None:
        # 使用默认配置
        config = default_config
    
    # 应用组件覆盖
    overrides = component_overrides or {}
    
    logger.info(f"创建新的RAG服务实例，模式: {config.mode}")
    
    # 创建组件
    try:
        # 创建嵌入模型
        embedder = overrides.get("embedder") or RAGComponentRegistry.create(
            RAGComponentRegistry.EMBEDDER,
            config.embedder.type,
            model=config.embedder.model,
            api_key=config.embedder.api_key,
            base_url=config.embedder.base_url
        )
        
        # 创建分块器
        chunker = overrides.get("chunker") or RAGComponentRegistry.create(
            RAGComponentRegistry.CHUNKER,
            config.chunker.type,
            chunk_size=config.chunker.chunk_size,
            chunk_overlap=config.chunker.chunk_overlap
        )
        
        # 创建向量存储
        vector_store = overrides.get("vector_store") or RAGComponentRegistry.create(
            RAGComponentRegistry.VECTOR_STORE,
            config.vector_store.type,
            embedding_provider=embedder
        )
        
        # 创建检索器
        retriever = overrides.get("retriever") or RAGComponentRegistry.create(
            RAGComponentRegistry.RETRIEVER,
            config.retriever.type,
            vector_store=vector_store,
            top_k=config.retriever.top_k,
            score_threshold=config.retriever.score_threshold
        )
        
        # 创建查询转换器（如果启用）
        query_transformer = None
        if config.query_transformer.enabled:
            transformers = []
            for transformer_config in config.query_transformer.transformers:
                if transformer_config.get("enabled", True):
                    transformer = RAGComponentRegistry.create(
                        RAGComponentRegistry.QUERY_TRANSFORMER,
                        transformer_config["type"],
                        **transformer_config.get("params", {})
                    )
                    transformers.append(transformer)
            
            if transformers:
                query_transformer = RAGComponentRegistry.create(
                    RAGComponentRegistry.QUERY_TRANSFORMER,
                    "pipeline",
                    transformers=transformers
                )
        
        # 创建生成器
        generator = overrides.get("generator") or RAGComponentRegistry.create(
            RAGComponentRegistry.GENERATOR,
            config.generator.type,
            llm_service=llm_service,
            prompt_templates=config.generator.prompt_templates
        )
        
        # 创建文档加载器
        document_loader = overrides.get("document_loader") or RAGComponentRegistry.create(
            RAGComponentRegistry.DOCUMENT_LOADER,
            "web",  # 默认使用网页加载器
            html_to_text=True
        )
        
        # 创建服务
        service = HybridRAGService(
            llm_service=llm_service,
            config=config,
            embedder=embedder,
            chunker=chunker,
            retriever=retriever,
            vector_store=vector_store,
            generator=generator,
            document_loader=document_loader,
            query_transformer=query_transformer
        )
        
        # 缓存服务实例
        _service_instance = service
        
        return service
        
    except Exception as e:
        logger.error(f"创建RAG服务实例失败: {str(e)}", exc_info=True)
        raise

async def get_evaluator(
    llm_service: LLMService,
    force_new: bool = False
) -> RAGEvaluator:
    """
    获取RAG评估器实例
    
    Args:
        llm_service: LLM服务
        force_new: 强制创建新实例，不使用缓存
        
    Returns:
        RAGEvaluator: RAG评估器
    """
    global _evaluator_instance
    
    if _evaluator_instance is not None and not force_new:
        return _evaluator_instance
        
    evaluator = RAGEvaluator(llm_service)
    _evaluator_instance = evaluator
    
    return evaluator