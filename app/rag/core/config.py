"""
RAG系统配置
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Literal

class LlamaIndexConfig(BaseModel):
    """LlamaIndex配置"""
    
    embed_model: str = "text-embedding-ada-002"
    llm_model: str = "gpt-3.5-turbo"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    response_mode: Literal["compact", "refine", "tree_summarize"] = "compact"
    
    # 额外配置
    extra: Dict[str, Any] = Field(default_factory=dict)

class RAGConfig(BaseModel):
    """RAG系统配置"""
    
    # 应用模式
    mode: Literal["llama_index", "custom", "hybrid"] = "hybrid"
    
    # LlamaIndex配置
    llama_index: LlamaIndexConfig = Field(default_factory=LlamaIndexConfig)
    
    # 检索配置
    retriever_type: Literal["vector", "keyword", "hybrid"] = "vector"
    retriever_top_k: int = 5
    retriever_score_threshold: float = 0.7
    
    # 存储配置
    vector_store_type: Literal["memory", "qdrant"] = "memory"
    
    # 加载器配置
    loader_types: Dict[str, str] = Field(
        default_factory=lambda: {
            "web": "llama_index",
            "file": "llama_index",
            "azure_api": "custom"
        }
    )
    
    # 额外配置
    extra: Dict[str, Any] = Field(default_factory=dict)

# 默认配置
default_config = RAGConfig()