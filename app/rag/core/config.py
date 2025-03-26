"""
RAG system configuration
"""
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from app.core.config import get_settings

settings = get_settings()

class LlamaIndexConfig(BaseModel):
    """LlamaIndex configuration"""
    
    embed_model: str = Field(default=settings.LLAMA_INDEX_EMBED_MODEL)
    llm_model: str = Field(default=settings.LLAMA_INDEX_LLM_MODEL)  
    chunk_size: int = Field(default=settings.LLAMA_INDEX_CHUNK_SIZE)
    chunk_overlap: int = Field(default=settings.LLAMA_INDEX_CHUNK_OVERLAP)
    response_mode: str = Field(default=settings.LLAMA_INDEX_RESPONSE_MODE)
    
    # Additional configuration
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('response_mode')
    @classmethod
    def validate_response_mode(cls, v):
        valid_modes = ["compact", "refine", "tree_summarize"]
        if v not in valid_modes:
            raise ValueError(f"response_mode must be one of {valid_modes}")
        return v

class RAGConfig(BaseModel):
    """RAG system configuration"""
    
    # Application mode
    mode: str = Field(default=settings.RAG_MODE)
    
    # LlamaIndex configuration
    llama_index: LlamaIndexConfig = Field(default_factory=LlamaIndexConfig)
    
    # Retriever configuration
    retriever_type: str = Field(default=settings.RAG_RETRIEVER_TYPE)
    retriever_top_k: int = Field(default=settings.RAG_RETRIEVER_TOP_K)
    retriever_score_threshold: float = Field(default=settings.RAG_RETRIEVER_SCORE_THRESHOLD)
    
    # Vector store configuration
    vector_store_type: str = Field(default=settings.RAG_VECTOR_STORE_TYPE)
    
    # Loader types configuration
    loader_types: Dict[str, str] = Field(
        default_factory=lambda: {
            "web": "llama_index",
            "file": "llama_index", 
            "azure_api": "custom"
        }
    )
    
    # Additional configuration
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        valid_modes = ["llama_index", "custom", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}")
        return v
        
    @field_validator('retriever_type')
    @classmethod
    def validate_retriever_type(cls, v):
        valid_types = ["vector", "keyword", "hybrid"]
        if v not in valid_types:
            raise ValueError(f"retriever_type must be one of {valid_types}")
        return v
        
    @field_validator('vector_store_type')
    @classmethod
    def validate_vector_store_type(cls, v):
        valid_types = ["memory", "qdrant"]
        if v not in valid_types:
            raise ValueError(f"vector_store_type must be one of {valid_types}")
        return v

# Create default configuration
default_config = RAGConfig()