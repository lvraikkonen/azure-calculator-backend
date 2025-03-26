"""
LlamaIndex转换器 - 在自定义模型和LlamaIndex模型之间转换
"""

from typing import List, Dict, Any, Optional, Union, cast
from datetime import datetime

# LlamaIndex导入
from llama_index.core.schema import Document as LlamaDocument
from llama_index.core.schema import NodeWithScore, TextNode

# 自定义模型导入
from app.rag.core.models import Document, TextChunk, Metadata
from app.core.logging import get_logger

logger = get_logger(__name__)

def _convert_datetime(value):
    """将datetime转换为ISO格式字符串"""
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def _process_metadata_dict(metadata_dict: Dict[str, Any]) -> Dict[str, Any]:
    """处理元数据字典，将datetime对象转换为字符串"""
    result = {}
    for key, value in metadata_dict.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _process_metadata_dict(value)
        else:
            result[key] = value
    return result

def to_llama_document(doc: Document) -> LlamaDocument:
    """将自定义Document转换为LlamaDocument"""
    # 获取元数据并处理datetime
    try:
        metadata_dict = doc.metadata.dict()
        # 处理元数据中的datetime
        metadata_dict = _process_metadata_dict(metadata_dict)
        # 添加doc_id
        metadata_dict["doc_id"] = doc.id
        
        return LlamaDocument(
            text=doc.content,
            metadata=metadata_dict,
            id_=doc.id,
        )
    except Exception as e:
        logger.error(f"转换Document到LlamaDocument失败: {str(e)}")
        # 创建一个最小化的元数据
        simple_metadata = {
            "source": getattr(doc.metadata, "source", "unknown"),
            "title": getattr(doc.metadata, "title", None),
            "doc_id": doc.id
        }
        return LlamaDocument(
            text=doc.content,
            metadata=simple_metadata,
            id_=doc.id,
        )

def from_llama_document(llama_doc: LlamaDocument) -> Document:
    """将LlamaDocument转换为自定义Document"""
    # 提取元数据
    meta_dict = dict(llama_doc.metadata) if llama_doc.metadata else {}
    doc_id = meta_dict.pop("doc_id", llama_doc.id_)
    
    # 创建元数据对象
    metadata = Metadata(
        source=meta_dict.pop("source", "unknown"),
        title=meta_dict.pop("title", None),
        author=meta_dict.pop("author", None),
        content_type=meta_dict.pop("content_type", None),
        extra=meta_dict,  # 剩余字段作为extra
    )
    
    # 创建文档对象
    return Document(
        id=doc_id,
        content=llama_doc.text,
        metadata=metadata,
    )

def to_llama_node(chunk: TextChunk) -> TextNode:
    """将自定义TextChunk转换为LlamaIndex TextNode"""
    try:
        metadata_dict = chunk.metadata.dict()
        # 处理元数据中的datetime
        metadata_dict = _process_metadata_dict(metadata_dict)
        # 添加基本字段
        metadata_dict["doc_id"] = chunk.doc_id
        metadata_dict["chunk_id"] = chunk.id
        
        return TextNode(
            text=chunk.content,
            metadata=metadata_dict,
            embedding=chunk.embedding,
            id_=chunk.id,
        )
    except Exception as e:
        logger.error(f"转换TextChunk到TextNode失败: {str(e)}")
        # 创建一个最小化的元数据
        simple_metadata = {
            "source": getattr(chunk.metadata, "source", "unknown"),
            "doc_id": chunk.doc_id,
            "chunk_id": chunk.id
        }
        return TextNode(
            text=chunk.content,
            metadata=simple_metadata,
            embedding=chunk.embedding,
            id_=chunk.id,
        )

def from_llama_node(node: Union[TextNode, NodeWithScore]) -> TextChunk:
    """将LlamaIndex Node转换为自定义TextChunk"""
    # 处理NodeWithScore类型
    score = None
    if isinstance(node, NodeWithScore):
        score = node.score
        node = node.node
    
    # 提取元数据
    meta_dict = dict(node.metadata) if node.metadata else {}
    doc_id = meta_dict.pop("doc_id", "unknown")
    chunk_id = meta_dict.pop("chunk_id", node.id_)
    
    # 创建元数据对象
    metadata = Metadata(
        source=meta_dict.pop("source", "unknown"),
        title=meta_dict.pop("title", None),
        author=meta_dict.pop("author", None),
        content_type=meta_dict.pop("content_type", None),
        extra=meta_dict,  # 剩余字段作为extra
    )
    
    # 创建块对象
    return TextChunk(
        id=chunk_id,
        doc_id=doc_id,
        content=node.text,
        metadata=metadata,
        embedding=node.embedding,
        score=score,
    )

def from_llama_nodes(nodes: List[Union[TextNode, NodeWithScore]]) -> List[TextChunk]:
    """将LlamaIndex Node列表转换为自定义TextChunk列表"""
    return [from_llama_node(node) for node in nodes]