"""
文档处理工具函数
"""
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import os
import glob

from app.rag.core.models import Document, Metadata
from app.rag.core.registry import RAGComponentRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

async def load_document(
    source: str, 
    loader_type: Optional[str] = None,
    **kwargs
) -> List[Document]:
    """
    加载单个文档
    
    Args:
        source: 文档源(URL、文件路径等)
        loader_type: 加载器类型，如果为None则自动检测
        **kwargs: 附加参数
        
    Returns:
        List[Document]: 文档列表
    """
    # 如果未指定加载器类型，自动检测
    if loader_type is None:
        loader_type = _detect_loader_type(source)
    
    try:
        # 创建加载器
        loader = RAGComponentRegistry.create(
            RAGComponentRegistry.DOCUMENT_LOADER,
            loader_type,
            **kwargs.get("loader_params", {})
        )
        
        # 加载文档
        return await loader.load(source, **kwargs)
        
    except Exception as e:
        logger.error(f"加载文档失败: {source}, 错误: {str(e)}")
        return []

async def load_documents_from_directory(
    directory: Union[str, Path],
    pattern: str = "*.*",
    recursive: bool = True,
    loader_type: str = "file",
    **kwargs
) -> List[Document]:
    """
    从目录加载多个文档
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归搜索子目录
        loader_type: 加载器类型
        **kwargs: 附加参数
        
    Returns:
        List[Document]: 文档列表
    """
    directory = Path(directory)
    
    if not directory.exists() or not directory.is_dir():
        logger.error(f"目录不存在: {directory}")
        return []
    
    # 查找文件
    if recursive:
        file_paths = glob.glob(str(directory / "**" / pattern), recursive=True)
    else:
        file_paths = glob.glob(str(directory / pattern))
    
    logger.info(f"在目录 {directory} 中找到 {len(file_paths)} 个文件")
    
    # 创建加载器
    try:
        loader = RAGComponentRegistry.create(
            RAGComponentRegistry.DOCUMENT_LOADER,
            loader_type,
            base_dir=directory,
            **kwargs.get("loader_params", {})
        )
    except Exception as e:
        logger.error(f"创建加载器失败: {loader_type}, 错误: {str(e)}")
        return []
    
    # 加载文档
    all_documents = []
    for file_path in file_paths:
        # 获取相对路径
        rel_path = os.path.relpath(file_path, directory)
        
        try:
            # 加载文档
            docs = await loader.load(rel_path, **kwargs)
            all_documents.extend(docs)
        except Exception as e:
            logger.error(f"加载文件失败: {file_path}, 错误: {str(e)}")
    
    logger.info(f"从目录加载了总计 {len(all_documents)} 个文档")
    return all_documents

async def load_documents_from_urls(
    urls: List[str],
    loader_type: str = "web",
    **kwargs
) -> List[Document]:
    """
    从URL列表加载多个文档
    
    Args:
        urls: URL列表
        loader_type: 加载器类型
        **kwargs: 附加参数
        
    Returns:
        List[Document]: 文档列表
    """
    logger.info(f"从 {len(urls)} 个URL加载文档")
    
    # 创建加载器
    try:
        loader = RAGComponentRegistry.create(
            RAGComponentRegistry.DOCUMENT_LOADER,
            loader_type,
            **kwargs.get("loader_params", {})
        )
    except Exception as e:
        logger.error(f"创建加载器失败: {loader_type}, 错误: {str(e)}")
        return []
    
    # 加载文档
    all_documents = []
    for url in urls:
        try:
            # 加载文档
            docs = await loader.load(url, **kwargs)
            all_documents.extend(docs)
        except Exception as e:
            logger.error(f"加载URL失败: {url}, 错误: {str(e)}")
    
    logger.info(f"从URL列表加载了总计 {len(all_documents)} 个文档")
    return all_documents

def _detect_loader_type(source: str) -> str:
    """
    检测适合的加载器类型
    
    Args:
        source: 文档源
        
    Returns:
        str: 加载器类型
    """
    if source.startswith(("http://", "https://")):
        return "web"
    elif os.path.exists(source):
        return "file"
    elif "azure.com" in source or source.startswith(("subscriptions/", "providers/Microsoft")):
        return "azure_api"
    else:
        return "web"  # 默认为网页