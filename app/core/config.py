from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载根目录下的 .env 文件
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)


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
    
    # 保留Azure OpenAI配置作为备选方案
    AZURE_OPENAI_API_KEY: str = Field("", env="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION: str = Field("2023-05-15", env="AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_API_BASE: str = Field("", env="AZURE_OPENAI_API_BASE")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field("", env="AZURE_OPENAI_DEPLOYMENT_NAME")

    # LDAP configuration
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str
    LDAP_PORT: int
    LDAP_DOMAIN: str
    LDAP_BASE_DN: str
    LDAP_BIND_DN: str
    LDAP_BIND_PASSWORD: str

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Azure Calculator backend API"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Security settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database settings - PostgreSQL for development
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Database settings - MS SQL Server for production
    MSSQL_SERVER: Optional[str] = None
    MSSQL_USER: Optional[str] = None
    MSSQL_PASSWORD: Optional[str] = None
    MSSQL_DB: Optional[str] = None
    MSSQL_DRIVER: Optional[str] = "ODBC Driver 17 for SQL Server"
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "500 MB"  # 日志文件达到一定大小后轮转
    LOG_RETENTION: str = "10 days"  # 保留日志的时间

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