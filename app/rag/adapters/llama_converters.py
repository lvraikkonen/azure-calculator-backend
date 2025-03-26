"""
LlamaIndex转换器 - 在自定义模型和LlamaIndex模型之间转换
"""

from typing import List, Dict, Any, Optional, Union, cast

# LlamaIndex导入
from llama_index.core.schema import Document as LlamaDocument
from llama_index.core.schema import NodeWithScore, TextNode

# 自定义模型导入
from app.rag.core.models import Document, TextChunk, Metadata

def to_llama_document(doc: Document) -> LlamaDocument:
    """将自定义Document转换为LlamaDocument"""
    return LlamaDocument(
        text=doc.content,
        metadata={
            **doc.metadata.dict(),
            "doc_id": doc.id,
        },
        doc_id=doc.id,
    )

def from_llama_document(llama_doc: LlamaDocument) -> Document:
    """将LlamaDocument转换为自定义Document"""
    # 提取元数据
    meta_dict = dict(llama_doc.metadata) if llama_doc.metadata else {}
    doc_id = meta_dict.pop("doc_id", llama_doc.doc_id)
    
    # 创建元数据对象
    metadata = Metadata(
        source=meta_dict.pop("source", "unknown"),
        title=meta_dict.pop("title", None),
        author=meta_dict.pop("author", None),
        created_at=meta_dict.pop("created_at", None),
        modified_at=meta_dict.pop("modified_at", None),
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
    return TextNode(
        text=chunk.content,
        metadata={
            **chunk.metadata.dict(),
            "doc_id": chunk.doc_id,
            "chunk_id": chunk.id,
        },
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
        created_at=meta_dict.pop("created_at", None),
        modified_at=meta_dict.pop("modified_at", None),
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