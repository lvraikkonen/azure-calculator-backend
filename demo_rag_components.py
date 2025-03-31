"""
测试RAG组件注册表、配置系统和评估框架
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from app.core.logging import get_logger
from app.services.llm_service import LLMService
from app.services.product import ProductService
from app.rag.core.registry import RAGComponentRegistry
from app.rag.core.config import RAGConfig
from app.rag.core.models import Document, Metadata, QueryResult, TextChunk, Source
from app.rag.services.rag_factory import create_rag_service, get_evaluator

# 配置日志
logger = get_logger(__name__)

async def demo_components():
    # 加载.env文件
    load_dotenv()
    
    logger.info("=== 测试RAG组件注册表 ===")
    
    # 列出所有注册的组件
    components = RAGComponentRegistry.list_components()
    for component_type, names in components.items():
        logger.info(f"{component_type}: {', '.join(names) if names else '无'}")
    
    logger.info("\n=== 测试配置系统 ===")
    
    # 创建配置
    config = RAGConfig(
        name="test_config",
        description="测试配置",
        mode="hybrid",
        embedder={
            "type": "silicon_flow",
            "model": "text-embedding-3-large"
        },
        chunker={
            "type": "sentence_window",
            "chunk_size": 512
        }
    )
    
    logger.info(f"配置名称: {config.name}")
    logger.info(f"嵌入模型: {config.embedder.type}, {config.embedder.model}")
    logger.info(f"分块器: {config.chunker.type}, 块大小: {config.chunker.chunk_size}")
    
    # 尝试从文件加载配置
    config_path = Path("config/rag_config.json")
    if config_path.exists():
        logger.info(f"\n从文件加载配置: {config_path}")
        config = RAGConfig.from_file(config_path)
        logger.info(f"配置名称: {config.name}")
        logger.info(f"描述: {config.description}")
        
    logger.info("\n=== 测试评估框架 ===")
    
    # 创建服务
    product_service = ProductService()
    llm_service = LLMService(product_service)
    
    # 获取评估器
    evaluator = await get_evaluator(llm_service)
    
    # 创建模拟查询结果
    mock_result = QueryResult(
        query="什么是Azure虚拟机?",
        answer="Azure虚拟机是微软Azure云平台提供的可扩展计算资源。它提供了灵活的虚拟化选项，无需购买和维护物理硬件。",
        chunks=[
            TextChunk(
                id="chunk1",
                doc_id="doc1",
                content="Azure虚拟机(VM)是Azure提供的按需、可扩展的计算资源。它提供了灵活的虚拟化选项，无需购买和维护运行VM的物理硬件。",
                metadata=Metadata(source="Azure文档", title="虚拟机概述"),
                score=0.92
            ),
            TextChunk(
                id="chunk2",
                doc_id="doc2",
                content="Azure提供多种VM大小和价格，适合不同工作负载。从小型应用到大型数据库，可以找到适合需求的配置。",
                metadata=Metadata(source="Azure文档", title="虚拟机定价"),
                score=0.85
            )
        ],
        sources=[
            Source(id="1", document_id="doc1", title="虚拟机概述", source="Azure文档", score=0.92),
            Source(id="2", document_id="doc2", title="虚拟机定价", source="Azure文档", score=0.85)
        ]
    )
    
    # 评估查询结果
    logger.info("评估查询结果...")
    eval_result = await evaluator.evaluate(mock_result)
    
    # 输出评估结果
    logger.info(f"总体评分: {eval_result.overall_score:.2f}")
    for metric_name, score in eval_result.metrics.items():
        logger.info(f"{metric_name}: {score:.2f}")

if __name__ == "__main__":
    asyncio.run(demo_components())