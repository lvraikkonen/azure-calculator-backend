"""
ModelConfigurationService 改进版本的单元测试
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.model_management.model_configuration_service import (
    ModelConfigurationService, ModelCacheManager, ModelValidator, 
    ModelEventPublisher, get_utc_now
)
from app.schemas.model_management.configuration import ModelCreate, ModelUpdate
from app.models.model_configuration import ModelConfiguration
from app.core.exceptions import ModelValidationError, DatabaseError


class TestModelCacheManager:
    """测试模型缓存管理器"""
    
    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = ModelCacheManager(max_size=100, ttl_seconds=300)
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert len(cache._cache) == 0
    
    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = ModelCacheManager(max_size=10, ttl_seconds=3600)
        
        # 创建模拟模型
        model = MagicMock(spec=ModelConfiguration)
        model.id = uuid.uuid4()
        model.name = "test-model"
        
        # 设置缓存
        cache.set("test-key", model)
        
        # 获取缓存
        cached_model = cache.get("test-key")
        assert cached_model == model
    
    def test_cache_ttl_expiry(self):
        """测试缓存TTL过期"""
        cache = ModelCacheManager(max_size=10, ttl_seconds=0)  # 立即过期
        
        model = MagicMock(spec=ModelConfiguration)
        cache.set("test-key", model)
        
        # 应该立即过期
        cached_model = cache.get("test-key")
        assert cached_model is None
    
    def test_cache_lru_eviction(self):
        """测试LRU缓存淘汰"""
        cache = ModelCacheManager(max_size=2, ttl_seconds=3600)
        
        model1 = MagicMock(spec=ModelConfiguration)
        model2 = MagicMock(spec=ModelConfiguration)
        model3 = MagicMock(spec=ModelConfiguration)
        
        cache.set("key1", model1)
        cache.set("key2", model2)
        cache.set("key3", model3)  # 应该淘汰key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == model2
        assert cache.get("key3") == model3
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = ModelCacheManager(max_size=10, ttl_seconds=3600)
        
        model = MagicMock(spec=ModelConfiguration)
        cache.set("test-key", model)
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["ttl_seconds"] == 3600
        assert stats["usage_ratio"] == 0.1


class TestModelValidator:
    """测试模型验证器"""
    
    def test_validate_model_type_valid(self):
        """测试有效的模型类型验证"""
        validator = ModelValidator()
        assert validator.validate_model_type("openai") == True
    
    def test_validate_model_type_invalid(self):
        """测试无效的模型类型验证"""
        validator = ModelValidator()
        assert validator.validate_model_type("invalid_type") == False
    
    def test_validate_price_valid(self):
        """测试有效的价格验证"""
        validator = ModelValidator()
        assert validator.validate_price(0.0) == True
        assert validator.validate_price(10.5) == True
    
    def test_validate_price_invalid(self):
        """测试无效的价格验证"""
        validator = ModelValidator()
        assert validator.validate_price(-1.0) == False
    
    def test_validate_model_data_success(self):
        """测试模型数据验证成功"""
        validator = ModelValidator()
        model_data = {
            "model_type": "openai",
            "input_price": 0.03,
            "output_price": 0.06,
            "rate_limit": 100,
            "user_rate_limit": 10
        }
        
        errors = validator.validate_model_data(model_data)
        assert len(errors) == 0
    
    def test_validate_model_data_errors(self):
        """测试模型数据验证失败"""
        validator = ModelValidator()
        model_data = {
            "model_type": "invalid",
            "input_price": -1.0,
            "output_price": -2.0,
            "rate_limit": -5,
            "user_rate_limit": 0
        }
        
        errors = validator.validate_model_data(model_data)
        assert len(errors) > 0
        assert any("无效的模型类型" in error for error in errors)


class TestModelEventPublisher:
    """测试模型事件发布器"""
    
    @pytest.mark.asyncio
    async def test_event_publisher_disabled(self):
        """测试禁用事件发布器"""
        publisher = ModelEventPublisher(enabled=False)
        model = MagicMock(spec=ModelConfiguration)
        
        # 应该不会抛出异常
        await publisher.publish_model_created(model)
        await publisher.publish_model_updated(model, {})
        await publisher.publish_model_deleted(uuid.uuid4(), "test")
    
    @pytest.mark.asyncio
    async def test_event_publisher_import_error(self):
        """测试Celery模块导入错误处理"""
        publisher = ModelEventPublisher(enabled=True)
        model = MagicMock(spec=ModelConfiguration)
        model.id = uuid.uuid4()
        model.name = "test-model"
        
        # 应该优雅处理ImportError
        await publisher.publish_model_created(model)


class TestModelConfigurationServiceImproved:
    """测试改进的模型配置服务"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def cache_manager(self):
        """缓存管理器"""
        return ModelCacheManager(max_size=10, ttl_seconds=60)
    
    @pytest.fixture
    def validator(self):
        """验证器"""
        return ModelValidator()
    
    @pytest.fixture
    def event_publisher(self):
        """事件发布器"""
        return ModelEventPublisher(enabled=False)  # 测试时禁用
    
    @pytest.fixture
    def service(self, mock_db, cache_manager, validator, event_publisher):
        """创建服务实例"""
        return ModelConfigurationService(
            db=mock_db,
            cache_manager=cache_manager,
            validator=validator,
            event_publisher=event_publisher
        )
    
    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.db is not None
        assert isinstance(service.cache_manager, ModelCacheManager)
        assert isinstance(service.validator, ModelValidator)
        assert isinstance(service.event_publisher, ModelEventPublisher)
        assert "events_published" in service.metrics
    
    @pytest.mark.asyncio
    async def test_get_model_with_cache_hit(self, service):
        """测试缓存命中"""
        model_id = uuid.uuid4()
        mock_model = MagicMock(spec=ModelConfiguration)
        mock_model.id = model_id
        
        # 预先设置缓存
        service.cache_manager.set(str(model_id), mock_model)
        
        result = await service._get_model_with_cache(model_id)
        
        assert result == mock_model
        assert service.metrics["cache_hits"] == 1
        assert service.metrics["cache_misses"] == 0
    
    @pytest.mark.asyncio
    async def test_get_model_with_cache_miss(self, service, mock_db):
        """测试缓存未命中"""
        model_id = uuid.uuid4()
        mock_model = MagicMock(spec=ModelConfiguration)
        mock_model.id = model_id
        
        # 模拟数据库查询
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_db.execute.return_value = mock_result
        
        result = await service._get_model_with_cache(model_id)
        
        assert result == mock_model
        assert service.metrics["cache_hits"] == 0
        assert service.metrics["cache_misses"] == 1
        assert service.metrics["db_queries"] == 1
    
    @pytest.mark.asyncio
    async def test_validate_model_data_success(self, service):
        """测试模型数据验证成功"""
        model_data = {
            "model_type": "openai",
            "input_price": 0.03,
            "output_price": 0.06
        }
        
        # 应该不抛出异常
        service._validate_model_data(model_data)
    
    @pytest.mark.asyncio
    async def test_validate_model_data_failure(self, service):
        """测试模型数据验证失败"""
        model_data = {
            "model_type": "invalid",
            "input_price": -1.0
        }
        
        with pytest.raises(ModelValidationError):
            service._validate_model_data(model_data)
        
        assert service.metrics["validation_errors"] == 1


def test_get_utc_now():
    """测试UTC时间获取函数"""
    now = get_utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc


if __name__ == "__main__":
    pytest.main([__file__])
