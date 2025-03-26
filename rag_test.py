# rag_test.py
import asyncio
import os
from app.core.logging import get_logger
from dotenv import load_dotenv
from app.services.llm_service import LLMService
from app.services.product import ProductService
from app.rag.services.rag_factory import create_rag_service
from app.rag.core.models import Document, Metadata

# 配置日志
logger = get_logger(__name__)

async def test_rag():
    # 加载.env文件
    load_dotenv()
    
    logger.info("初始化服务...")
    # 初始化服务（不依赖数据库）
    product_service = ProductService()  # 使用样本数据
    llm_service = LLMService(product_service)
    
    # 创建RAG服务
    logger.info("创建RAG服务...")
    rag_service = await create_rag_service(llm_service)
    
    # 创建示例文档
    logger.info("创建示例文档...")
    doc1 = Document(
        content="Azure虚拟机(VM)是Azure提供的按需、可扩展的计算资源。它提供了灵活的虚拟化选项，无需购买和维护运行VM的物理硬件。Azure提供多种VM大小和价格，适合不同工作负载。",
        metadata=Metadata(
            source="Microsoft文档",
            title="Azure虚拟机概述",
            created_at=None
        )
    )
    
    doc2 = Document(
        content="Azure存储账户提供了高度可扩展的对象存储，适用于云中的数据存储。它包括Blob存储、文件存储、队列存储和表存储服务。Blob存储针对存储海量非结构化数据进行了优化。",
        metadata=Metadata(
            source="Azure文档",
            title="Azure存储服务介绍",
            created_at=None
        )
    )
    
    # 添加文档
    logger.info("添加文档到知识库...")
    doc_id1 = await rag_service.add_document(doc1)
    doc_id2 = await rag_service.add_document(doc2)
    logger.info(f"添加文档成功，ID: {doc_id1}, {doc_id2}")
    
    # 执行查询
    logger.info("\n执行查询：什么是Azure虚拟机?")
    result = await rag_service.query("什么是Azure虚拟机?")
    logger.info("\n查询结果:")
    logger.info(f"问题: {result.query}")
    logger.info(f"回答: {result.answer}")
    
    # 显示来源
    logger.info("\n来源文档:")
    for source in result.sources:
        logger.info(f"- {source.title} ({source.source})")
    
    # 执行第二个查询
    logger.info("\n执行查询：Azure存储服务有哪些类型?")
    result2 = await rag_service.query("Azure存储服务有哪些类型?")
    logger.info("\n查询结果:")
    logger.info(f"问题: {result2.query}")
    logger.info(f"回答: {result2.answer}")
    
    # 显示来源
    logger.info("\n来源文档:")
    for source in result2.sources:
        logger.info(f"- {source.title} ({source.source})")

if __name__ == "__main__":
    asyncio.run(test_rag())