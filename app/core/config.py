from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载环境变量文件
base_path = Path(__file__).resolve().parent.parent.parent
env_path = base_path / ".env"

try:
    loaded = load_dotenv(env_path)
    if loaded:
        logging.info(f"已加载环境变量文件: {env_path}")
    else:
        logging.warning(f"警告: 未能加载环境变量文件 {env_path}，将使用默认值或系统环境变量")
except Exception as e:
    logging.error(f"加载环境变量文件出错: {e}")


class Settings(BaseSettings):
    """
    Application settings using Pydantic v2 settings management
    
    Now using python-dotenv to load environment variables
    """
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # 标准OpenAI API配置
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    OPENAI_API_BASE: Optional[str] = Field(None, env="OPENAI_API_BASE")  # 可选，默认使用标准OpenAI API端点
    OPENAI_CHAT_MODEL: str = Field("gpt-3.5-turbo", env="OPENAI_CHAT_MODEL")

    # Deepseek配置
    DEEPSEEK_API_KEY: str = Field("", env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE: Optional[str] = Field(None, env="DEEPSEEK_API_BASE")
    DEEPSEEK_R1_MODEL: str = Field("deepseek-reasoner", env="DEEPSEEK_R1_MODEL")
    DEEPSEEK_V3_MODEL: str = Field("deepseek-chat", env="DEEPSEEK_V3_MODEL")
    
    # 保留Azure OpenAI配置作为备选方案
    AZURE_OPENAI_API_KEY: str = Field("", env="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = Field("2023-05-15", env="AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_API_BASE: str = Field("", env="AZURE_OPENAI_API_BASE")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field("", env="AZURE_OPENAI_DEPLOYMENT_NAME")

    DEFAULT_MODEL_TYPE: str = Field("deepseek", env="DEFAULT_MODEL_TYPE")

    API_KEY_ENCRYPTION_KEY: Optional[str] = Field(
        None,
        env="API_KEY_ENCRYPTION_KEY",
        description="用于加密API密钥的Fernet密钥（32字节base64编码）"
    )

    # 意图分析专用模型配置
    INTENT_ANALYSIS_MODEL_TYPE: str = Field("deepseek", env="INTENT_ANALYSIS_MODEL_TYPE")
    INTENT_ANALYSIS_MODEL: str = Field("deepseek-chat", env="INTENT_ANALYSIS_MODEL")
    INTENT_ANALYSIS_TEMPERATURE: float = Field(0.3, env="INTENT_ANALYSIS_TEMPERATURE")  # 新增温度控制
    INTENT_ANALYSIS_MAX_TOKENS: int = Field(500, env="INTENT_ANALYSIS_MAX_TOKENS")  # 新增token限制
    INTENT_CACHE_TTL: int = Field(10, env="INTENT_CACHE_TTL")
    INTENT_CACHE_ENABLED: bool = Field(True, env="INTENT_CACHE_ENABLED")
    INTENT_SIMILARITY_THRESHOLD: float = Field(0.3, env="INTENT_SIMILARITY_THRESHOLD")  # 新增相似度阈值

    # LDAP配置
    LDAP_ENABLED: bool = Field(False, env="LDAP_ENABLED")
    LDAP_SERVER: str = Field(..., env="LDAP_SERVER")
    LDAP_PORT: int = Field(389, env="LDAP_PORT")
    LDAP_DOMAIN: str = Field(..., env="LDAP_DOMAIN")
    LDAP_BASE_DN: str = Field(..., env="LDAP_BASE_DN")
    LDAP_BIND_DN: str = Field(..., env="LDAP_BIND_DN")
    LDAP_BIND_PASSWORD: str = Field(..., env="LDAP_BIND_PASSWORD")
    LDAP_GROUP_MAPPINGS: Dict[str, str] = Field(default_factory=dict, env="LDAP_GROUP_MAPPINGS")

    # API设置
    API_V1_STR: str = Field("/api/v1", env="API_V1_STR")
    PROJECT_NAME: str = Field("Azure Calculator backend API", env="PROJECT_NAME")
    
    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="BACKEND_CORS_ORIGINS"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 安全设置
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 数据库设置 - PostgreSQL for development
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    SQLALCHEMY_DATABASE_URI: Optional[str] = Field(None, env="SQLALCHEMY_DATABASE_URI")
    
    # 数据库设置 - MS SQL Server for production
    MSSQL_SERVER: Optional[str] = Field(None, env="MSSQL_SERVER")
    MSSQL_USER: Optional[str] = Field(None, env="MSSQL_USER")
    MSSQL_PASSWORD: Optional[str] = Field(None, env="MSSQL_PASSWORD")
    MSSQL_DB: Optional[str] = Field(None, env="MSSQL_DB")
    MSSQL_DRIVER: Optional[str] = Field("ODBC Driver 17 for SQL Server", env="MSSQL_DRIVER")
    
    # Celery设置
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # 日志设置
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>", env="LOG_FORMAT")
    LOG_FILE: str = Field("logs/app.log", env="LOG_FILE")
    LOG_ROTATION: str = Field("500 MB", env="LOG_ROTATION")
    LOG_RETENTION: str = Field("10 days", env="LOG_RETENTION")

    # RAG 设置
    RAG_MODE: str = Field("hybrid", env="RAG_MODE")
    RAG_RETRIEVER_TYPE: str = Field("vector", env="RAG_RETRIEVER_TYPE")
    RAG_RETRIEVER_TOP_K: int = Field(5, env="RAG_RETRIEVER_TOP_K") 
    RAG_RETRIEVER_SCORE_THRESHOLD: float = Field(0.7, env="RAG_RETRIEVER_SCORE_THRESHOLD")
    RAG_VECTOR_STORE_TYPE: str = Field("memory", env="RAG_VECTOR_STORE_TYPE")

    # LlamaIndex 设置
    LLAMA_INDEX_EMBED_URL: str = Field("https://api.siliconflow.cn/v1/embeddings", env="LLAMA_INDEX_EMBED_URL")
    LLAMA_INDEX_EMBED_MODEL: str = Field("BAAI/bge-large-zh-v1.5", env="LLAMA_INDEX_EMBED_MODEL")
    LLAMA_INDEX_EMBED_APIKEY: str = Field("", env="LLAMA_INDEX_EMBED_APIKEY")

    LLAMA_INDEX_LLM_BASEURL: str = Field("https://api.deepseek.com", env="LLAMA_INDEX_LLM_BASEURL")
    LLAMA_INDEX_LLM_MODEL: str = Field("BAAI/bge-large-zh-v1.5", env="LLAMA_INDEX_LLM_MODEL")
    LLAMA_INDEX_LLM_APIKEY: str = Field("", env="LLAMA_INDEX_LLM_APIKEY")

    LLAMA_INDEX_CHUNK_SIZE: int = Field(1000, env="LLAMA_INDEX_CHUNK_SIZE")
    LLAMA_INDEX_CHUNK_OVERLAP: int = Field(200, env="LLAMA_INDEX_CHUNK_OVERLAP")
    LLAMA_INDEX_RESPONSE_MODE: str = Field("compact", env="LLAMA_INDEX_RESPONSE_MODE")

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="after")
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        if v:
            return v
            
        values = info.data
        
        # Check if MSSQL configuration is available
        if all([
            values.get("MSSQL_SERVER"),
            values.get("MSSQL_USER"),
            values.get("MSSQL_PASSWORD"),
            values.get("MSSQL_DB")
        ]):
            # Production configuration - use MSSQL
            driver = values.get("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
            return f"mssql+pymssql://{values.get('MSSQL_USER')}:{values.get('MSSQL_PASSWORD')}@{values.get('MSSQL_SERVER')}/{values.get('MSSQL_DB')}"
        
        # 直接手动构建 PostgreSQL 连接 URL，避免 PostgresDsn.build() 可能的问题
        postgres_user = values.get("POSTGRES_USER")
        postgres_password = values.get("POSTGRES_PASSWORD")
        postgres_server = values.get("POSTGRES_SERVER")
        postgres_port = values.get("POSTGRES_PORT")
        postgres_db = values.get("POSTGRES_DB")
        
        # 确保端口是整数
        if postgres_port and not isinstance(postgres_port, int):
            try:
                postgres_port = int(postgres_port)
            except (ValueError, TypeError):
                postgres_port = 5432
        
        # 手动构建连接 URL
        return f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

    def get_log_path(self) -> Path:
        """获取日志文件目录路径"""
        log_path = Path(self.LOG_FILE).parent
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings to avoid reloading .env file on each request
    """
    return Settings()