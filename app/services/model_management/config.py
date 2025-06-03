"""
模型管理服务配置
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class ModelCacheConfig(BaseModel):
    """模型缓存配置"""
    max_size: int = Field(1000, description="缓存最大大小")
    ttl_seconds: int = Field(3600, description="缓存TTL（秒）")
    enabled: bool = Field(True, description="是否启用缓存")


class ModelValidationConfig(BaseModel):
    """模型验证配置"""
    strict_mode: bool = Field(True, description="是否启用严格验证模式")
    allowed_model_types: list = Field(
        default=["openai", "deepseek", "anthropic", "azure", "custom"],
        description="允许的模型类型列表"
    )
    max_name_length: int = Field(100, description="模型名称最大长度")
    max_description_length: int = Field(500, description="描述最大长度")


class ModelEventConfig(BaseModel):
    """模型事件配置"""
    enabled: bool = Field(True, description="是否启用事件发布")
    async_mode: bool = Field(True, description="是否异步发布事件")
    retry_attempts: int = Field(3, description="事件发布重试次数")
    retry_delay: float = Field(1.0, description="重试延迟（秒）")


class ModelPerformanceConfig(BaseModel):
    """模型性能配置"""
    connection_timeout: int = Field(30, description="连接超时时间（秒）")
    max_retry_attempts: int = Field(3, description="最大重试次数")
    retry_delay: float = Field(1.0, description="重试延迟（秒）")
    batch_size: int = Field(100, description="批量操作大小")


class ModelSecurityConfig(BaseModel):
    """模型安全配置"""
    encrypt_api_keys: bool = Field(True, description="是否加密API密钥")
    mask_api_keys_in_logs: bool = Field(True, description="是否在日志中掩码API密钥")
    api_key_rotation_days: int = Field(90, description="API密钥轮换天数")


class ModelConfigurationServiceConfig(BaseModel):
    """模型配置服务总配置"""
    cache: ModelCacheConfig = Field(default_factory=ModelCacheConfig)
    validation: ModelValidationConfig = Field(default_factory=ModelValidationConfig)
    events: ModelEventConfig = Field(default_factory=ModelEventConfig)
    performance: ModelPerformanceConfig = Field(default_factory=ModelPerformanceConfig)
    security: ModelSecurityConfig = Field(default_factory=ModelSecurityConfig)
    
    # 数据库配置
    db_pool_size: int = Field(20, description="数据库连接池大小")
    db_max_overflow: int = Field(30, description="数据库连接池最大溢出")
    db_pool_timeout: int = Field(30, description="数据库连接池超时")
    
    # 监控配置
    enable_metrics: bool = Field(True, description="是否启用指标收集")
    metrics_export_interval: int = Field(60, description="指标导出间隔（秒）")
    
    # 日志配置
    log_level: str = Field("INFO", description="日志级别")
    log_sql_queries: bool = Field(False, description="是否记录SQL查询")
    
    class Config:
        env_prefix = "MODEL_SERVICE_"
        case_sensitive = False


# 默认配置实例
default_config = ModelConfigurationServiceConfig()


def get_service_config() -> ModelConfigurationServiceConfig:
    """获取服务配置"""
    return default_config


def update_service_config(config_dict: Dict[str, Any]) -> None:
    """更新服务配置"""
    global default_config
    
    # 创建新的配置实例
    new_config_data = default_config.model_dump()
    
    # 递归更新配置
    def update_nested_dict(target: dict, source: dict):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    update_nested_dict(new_config_data, config_dict)
    default_config = ModelConfigurationServiceConfig(**new_config_data)


# 配置验证函数
def validate_config(config: ModelConfigurationServiceConfig) -> list:
    """
    验证配置的有效性
    
    Args:
        config: 配置对象
        
    Returns:
        错误列表，空列表表示配置有效
    """
    errors = []
    
    # 验证缓存配置
    if config.cache.max_size <= 0:
        errors.append("缓存最大大小必须大于0")
    
    if config.cache.ttl_seconds <= 0:
        errors.append("缓存TTL必须大于0")
    
    # 验证性能配置
    if config.performance.connection_timeout <= 0:
        errors.append("连接超时时间必须大于0")
    
    if config.performance.max_retry_attempts < 0:
        errors.append("最大重试次数不能为负数")
    
    if config.performance.batch_size <= 0:
        errors.append("批量操作大小必须大于0")
    
    # 验证验证配置
    if config.validation.max_name_length <= 0:
        errors.append("模型名称最大长度必须大于0")
    
    if config.validation.max_description_length <= 0:
        errors.append("描述最大长度必须大于0")
    
    # 验证数据库配置
    if config.db_pool_size <= 0:
        errors.append("数据库连接池大小必须大于0")
    
    if config.db_max_overflow < 0:
        errors.append("数据库连接池最大溢出不能为负数")
    
    return errors


# 配置工厂函数
def create_development_config() -> ModelConfigurationServiceConfig:
    """创建开发环境配置"""
    return ModelConfigurationServiceConfig(
        cache=ModelCacheConfig(max_size=100, ttl_seconds=300),
        validation=ModelValidationConfig(strict_mode=False),
        events=ModelEventConfig(enabled=False),
        performance=ModelPerformanceConfig(connection_timeout=10),
        log_level="DEBUG",
        log_sql_queries=True
    )


def create_production_config() -> ModelConfigurationServiceConfig:
    """创建生产环境配置"""
    return ModelConfigurationServiceConfig(
        cache=ModelCacheConfig(max_size=5000, ttl_seconds=7200),
        validation=ModelValidationConfig(strict_mode=True),
        events=ModelEventConfig(enabled=True, async_mode=True),
        performance=ModelPerformanceConfig(
            connection_timeout=30,
            max_retry_attempts=5,
            batch_size=200
        ),
        db_pool_size=50,
        db_max_overflow=100,
        log_level="INFO",
        log_sql_queries=False
    )


def create_test_config() -> ModelConfigurationServiceConfig:
    """创建测试环境配置"""
    return ModelConfigurationServiceConfig(
        cache=ModelCacheConfig(max_size=10, ttl_seconds=60, enabled=False),
        validation=ModelValidationConfig(strict_mode=True),
        events=ModelEventConfig(enabled=False),
        performance=ModelPerformanceConfig(connection_timeout=5),
        db_pool_size=5,
        enable_metrics=False,
        log_level="WARNING"
    )
