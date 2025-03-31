"""
RAG系统配置 - 增强的模块化配置系统
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, root_validator
import os
import json
import yaml
from pathlib import Path
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

class EmbedderConfig(BaseModel):
    """嵌入模型配置"""
    
    type: str = Field(default="silicon_flow")
    model: str = Field(default=settings.LLAMA_INDEX_EMBED_MODEL)
    api_key: str = Field(default=settings.LLAMA_INDEX_EMBED_APIKEY)
    base_url: Optional[str] = Field(default=settings.LLAMA_INDEX_EMBED_URL)
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @root_validator(pre=True)
    def resolve_env_vars(cls, values):
        """解析环境变量引用"""
        for key, value in values.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                values[key] = os.getenv(env_var, "")
        return values

class ChunkerConfig(BaseModel):
    """文本分块器配置"""
    
    type: str = Field(default="sentence_window")
    chunk_size: int = Field(default=settings.LLAMA_INDEX_CHUNK_SIZE)
    chunk_overlap: int = Field(default=settings.LLAMA_INDEX_CHUNK_OVERLAP)
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)

class RetrieverConfig(BaseModel):
    """检索器配置"""
    
    type: str = Field(default=settings.RAG_RETRIEVER_TYPE)
    top_k: int = Field(default=settings.RAG_RETRIEVER_TOP_K)
    score_threshold: float = Field(default=settings.RAG_RETRIEVER_SCORE_THRESHOLD)
    
    # 混合检索配置
    hybrid_retrieval: Optional[Dict[str, Any]] = None
    
    # 重排序配置
    reranking: Optional[Dict[str, Any]] = None
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('type')
    @classmethod
    def validate_retriever_type(cls, v):
        valid_types = ["vector", "keyword", "hybrid", "azure"]
        if v not in valid_types:
            raise ValueError(f"retriever_type必须是以下之一: {valid_types}")
        return v

class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    
    type: str = Field(default=settings.RAG_VECTOR_STORE_TYPE)
    
    # Qdrant配置
    qdrant: Optional[Dict[str, Any]] = None
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('type')
    @classmethod
    def validate_vector_store_type(cls, v):
        valid_types = ["memory", "qdrant", "pinecone", "chroma"]
        if v not in valid_types:
            raise ValueError(f"vector_store_type必须是以下之一: {valid_types}")
        return v

class QueryTransformerConfig(BaseModel):
    """查询转换器配置"""
    
    enabled: bool = Field(default=False)
    transformers: List[Dict[str, Any]] = Field(default_factory=list)

class GeneratorConfig(BaseModel):
    """生成器配置"""
    
    type: str = Field(default="default")
    prompt_templates: Dict[str, str] = Field(default_factory=dict)
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)

class EvaluationConfig(BaseModel):
    """评估配置"""
    
    enabled: bool = Field(default=False)
    metrics: List[str] = Field(default_factory=lambda: ["relevance", "faithfulness"])
    
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)

class RAGConfig(BaseModel):
    """增强的RAG系统配置"""
    
    # 基本配置
    name: str = Field(default="default")
    description: Optional[str] = None
    
    # 应用模式
    mode: str = Field(default=settings.RAG_MODE)
    
    # 组件配置
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    query_transformer: QueryTransformerConfig = Field(default_factory=QueryTransformerConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    
    # 评估配置
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    
    # 其他配置
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        valid_modes = ["llama_index", "custom", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"mode必须是以下之一: {valid_modes}")
        return v
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "RAGConfig":
        """从文件加载配置"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
            
        suffix = file_path.suffix.lower()
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if suffix == ".json":
                    config_data = json.load(f)
                elif suffix in [".yaml", ".yml"]:
                    config_data = yaml.safe_load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {suffix}")
                    
            return cls(**config_data)
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {file_path}, 错误: {str(e)}")
            raise

# 创建默认配置
default_config = RAGConfig()