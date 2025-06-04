"""
模型管理服务工厂
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .model_configuration_service import (
    ModelConfigurationService, ModelCacheManager, 
    ModelValidator, ModelEventPublisher
)
from .config import (
    ModelConfigurationServiceConfig, get_service_config,
    create_development_config, create_production_config, create_test_config
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelManagementServiceFactory:
    """模型管理服务工厂类"""
    
    def __init__(self, config: Optional[ModelConfigurationServiceConfig] = None):
        """
        初始化工厂
        
        Args:
            config: 服务配置，如果为None则使用默认配置
        """
        self.config = config or get_service_config()
        self._cache_manager = None
        self._validator = None
        self._event_publisher = None
    
    def get_cache_manager(self) -> ModelCacheManager:
        """获取缓存管理器实例（单例）"""
        if self._cache_manager is None:
            cache_config = self.config.cache
            if cache_config.enabled:
                self._cache_manager = ModelCacheManager(
                    max_size=cache_config.max_size,
                    ttl_seconds=cache_config.ttl_seconds
                )
                logger.info(f"创建缓存管理器: max_size={cache_config.max_size}, ttl={cache_config.ttl_seconds}s")
            else:
                # 创建一个禁用的缓存管理器
                self._cache_manager = ModelCacheManager(max_size=0, ttl_seconds=0)
                logger.info("缓存已禁用")
        
        return self._cache_manager
    
    def get_validator(self) -> ModelValidator:
        """获取验证器实例（单例）"""
        if self._validator is None:
            self._validator = ModelValidator()
            logger.info("创建模型验证器")
        
        return self._validator
    
    def get_event_publisher(self) -> ModelEventPublisher:
        """获取事件发布器实例（单例）"""
        if self._event_publisher is None:
            event_config = self.config.events
            self._event_publisher = ModelEventPublisher(enabled=event_config.enabled)
            logger.info(f"创建事件发布器: enabled={event_config.enabled}")
        
        return self._event_publisher
    
    def create_service(self, db: AsyncSession) -> ModelConfigurationService:
        """
        创建模型配置服务实例
        
        Args:
            db: 数据库会话
            
        Returns:
            配置好的模型配置服务实例
        """
        cache_manager = self.get_cache_manager()
        validator = self.get_validator()
        event_publisher = self.get_event_publisher()
        
        service = ModelConfigurationService(
            db=db,
            cache_manager=cache_manager,
            validator=validator,
            event_publisher=event_publisher
        )
        
        logger.info("创建模型配置服务实例")
        return service
    
    def reset(self) -> None:
        """重置工厂状态，清除所有单例实例"""
        self._cache_manager = None
        self._validator = None
        self._event_publisher = None
        logger.info("工厂状态已重置")


# 全局工厂实例
_factory_instance: Optional[ModelManagementServiceFactory] = None


def get_factory(config: Optional[ModelConfigurationServiceConfig] = None) -> ModelManagementServiceFactory:
    """
    获取全局工厂实例
    
    Args:
        config: 可选的配置，仅在首次调用时有效
        
    Returns:
        工厂实例
    """
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = ModelManagementServiceFactory(config)
        logger.info("创建全局模型管理服务工厂")
    
    return _factory_instance


def reset_factory() -> None:
    """重置全局工厂实例"""
    global _factory_instance
    
    if _factory_instance:
        _factory_instance.reset()
        _factory_instance = None
        logger.info("全局工厂已重置")


def create_service(
    db: AsyncSession, 
    config: Optional[ModelConfigurationServiceConfig] = None
) -> ModelConfigurationService:
    """
    便捷函数：创建模型配置服务实例
    
    Args:
        db: 数据库会话
        config: 可选的配置
        
    Returns:
        配置好的模型配置服务实例
    """
    factory = get_factory(config)
    return factory.create_service(db)


def create_development_service(db: AsyncSession) -> ModelConfigurationService:
    """
    创建开发环境的服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        开发环境配置的服务实例
    """
    config = create_development_config()
    factory = ModelManagementServiceFactory(config)
    return factory.create_service(db)


def create_production_service(db: AsyncSession) -> ModelConfigurationService:
    """
    创建生产环境的服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        生产环境配置的服务实例
    """
    config = create_production_config()
    factory = ModelManagementServiceFactory(config)
    return factory.create_service(db)


def create_test_service(db: AsyncSession) -> ModelConfigurationService:
    """
    创建测试环境的服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        测试环境配置的服务实例
    """
    config = create_test_config()
    factory = ModelManagementServiceFactory(config)
    return factory.create_service(db)


# 上下文管理器支持
class ServiceContext:
    """服务上下文管理器"""
    
    def __init__(
        self, 
        db: AsyncSession, 
        config: Optional[ModelConfigurationServiceConfig] = None
    ):
        self.db = db
        self.config = config
        self.service: Optional[ModelConfigurationService] = None
    
    async def __aenter__(self) -> ModelConfigurationService:
        """进入上下文"""
        self.service = create_service(self.db, self.config)
        return self.service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        # 这里可以添加清理逻辑
        if self.service and hasattr(self.service, 'cache_manager'):
            # 可选：清理缓存或执行其他清理操作
            pass


# 装饰器支持
def with_model_service(config: Optional[ModelConfigurationServiceConfig] = None):
    """
    装饰器：为函数注入模型配置服务
    
    Args:
        config: 可选的配置
        
    Usage:
        @with_model_service()
        async def my_function(db: AsyncSession, model_service: ModelConfigurationService):
            # 使用 model_service
            pass
    """
    def decorator(func):
        async def wrapper(db: AsyncSession, *args, **kwargs):
            service = create_service(db, config)
            return await func(db, service, *args, **kwargs)
        return wrapper
    return decorator


# 健康检查函数
async def health_check(db: AsyncSession) -> dict:
    """
    执行模型管理服务健康检查
    
    Args:
        db: 数据库会话
        
    Returns:
        健康检查结果
    """
    try:
        service = create_service(db)
        
        # 检查数据库连接
        stats = await service.get_model_statistics()
        
        # 检查缓存
        cache_stats = service.cache_manager.get_stats()
        
        # 检查指标
        metrics = service.metrics
        
        return {
            "status": "healthy",
            "database": "connected",
            "cache": cache_stats,
            "metrics": metrics,
            "model_count": stats.get("total_models", 0)
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
