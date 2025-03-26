"""
共享数据模型 - 定义可在自定义组件和LlamaIndex之间转换的模型
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
import uuid

class Metadata(BaseModel):
    """文档元数据"""
    source: str
    title: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    modified_at: Optional[datetime] = None
    content_type: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "Azure Docs",
                "title": "Virtual Machines Overview",
                "author": "Microsoft",
                "content_type": "text/markdown"
            }
        }

class Document(BaseModel):
    """文档模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Metadata
    
    def __str__(self) -> str:
        title = self.metadata.title or "Untitled"
        return f"Document(id={self.id}, title={title}, len={len(self.content)})"

class TextChunk(BaseModel):
    """文本块模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    content: str
    metadata: Metadata
    embedding: Optional[List[float]] = None
    score: Optional[float] = None
    
    def __str__(self) -> str:
        return f"TextChunk(id={self.id}, doc_id={self.doc_id}, len={len(self.content)})"
    
class Source(BaseModel):
    """来源引用模型"""
    id: str
    document_id: str
    title: str
    source: str
    score: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class QueryResult(BaseModel):
    """查询结果模型"""
    query: str
    answer: str
    chunks: List[TextChunk]
    sources: List[Source]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"QueryResult(query={self.query}, chunks={len(self.chunks)}, sources={len(self.sources)})"