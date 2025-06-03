"""
ModelPerformanceService 单元测试
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.model_management.model_performance_service import (
    ModelPerformanceService, PerformanceTestConfig, TestProgress, 
    PerformanceMetrics, TestStatus
)
from app.schemas.model_management.performance import (
    TestCreate, SpeedTestRequest, LatencyTestRequest, BatchTestRequest
)
from app.models.model_configuration import ModelConfiguration


class TestPerformanceTestConfig:
    """测试配置常量"""
    
    def test_config_constants(self):
        """测试配置常量存在且合理"""
        assert PerformanceTestConfig.DEFAULT_SLEEP_INTERVAL > 0
        assert PerformanceTestConfig.MAX_ROUNDS > 0
        assert PerformanceTestConfig.MAX_CONCURRENT_TESTS > 0
        assert len(PerformanceTestConfig.DEFAULT_PROMPTS) > 0
        assert PerformanceTestConfig.DEFAULT_TIMEOUT > 0


class TestTestProgress:
    """测试进度跟踪类"""
    
    def test_progress_initialization(self):
        """测试进度初始化"""
        test_id = uuid.uuid4()
        progress = TestProgress(test_id, 5)
        
        assert progress.test_id == test_id
        assert progress.total_rounds == 5
        assert progress.completed_rounds == 0
        assert progress.failed_rounds == 0
        assert progress.status == TestStatus.PENDING
        
    def test_progress_lifecycle(self):
        """测试进度生命周期"""
        test_id = uuid.uuid4()
        progress = TestProgress(test_id, 3)
        
        # 开始测试
        progress.start_test()
        assert progress.status == TestStatus.RUNNING
        assert progress.start_time is not None
        
        # 完成轮次
        progress.start_round(1)
        progress.complete_round(1, success=True)
        assert progress.completed_rounds == 1
        assert progress.failed_rounds == 0
        
        # 失败轮次
        progress.start_round(2)
        progress.complete_round(2, success=False, error="测试错误")
        assert progress.completed_rounds == 1
        assert progress.failed_rounds == 1
        assert len(progress.error_details) == 1
        
        # 完成测试
        progress.complete_test(success=True)
        assert progress.status == TestStatus.COMPLETED
        assert progress.end_time is not None
        
    def test_progress_percentage(self):
        """测试进度百分比计算"""
        progress = TestProgress(uuid.uuid4(), 10)
        
        assert progress.get_progress_percentage() == 0.0
        
        progress.completed_rounds = 3
        progress.failed_rounds = 2
        assert progress.get_progress_percentage() == 50.0
        
    def test_progress_to_dict(self):
        """测试进度转换为字典"""
        progress = TestProgress(uuid.uuid4(), 5)
        progress.start_test()
        progress.completed_rounds = 2
        progress.failed_rounds = 1
        
        result = progress.to_dict()
        
        assert "test_id" in result
        assert "status" in result
        assert "total_rounds" in result
        assert "completed_rounds" in result
        assert "failed_rounds" in result
        assert "progress_percentage" in result
        assert result["total_rounds"] == 5
        assert result["completed_rounds"] == 2
        assert result["failed_rounds"] == 1


class TestPerformanceMetrics:
    """测试性能指标收集器"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = PerformanceMetrics()
        
        assert "test_duration" in metrics.metrics
        assert "total_tests" in metrics.counters
        assert metrics.counters["total_tests"] == 0
        
    def test_record_metric(self):
        """测试记录指标"""
        metrics = PerformanceMetrics()
        
        metrics.record_metric("test_duration", 1.5)
        metrics.record_metric("test_duration", 2.0)
        
        assert len(metrics.metrics["test_duration"]) == 2
        assert 1.5 in metrics.metrics["test_duration"]
        assert 2.0 in metrics.metrics["test_duration"]
        
    def test_increment_counter(self):
        """测试增加计数器"""
        metrics = PerformanceMetrics()
        
        metrics.increment_counter("total_tests")
        metrics.increment_counter("total_tests", 3)
        
        assert metrics.counters["total_tests"] == 4
        
    def test_get_statistics(self):
        """测试获取统计信息"""
        metrics = PerformanceMetrics()
        
        # 添加一些数据
        metrics.record_metric("test_duration", 1.0)
        metrics.record_metric("test_duration", 2.0)
        metrics.record_metric("test_duration", 3.0)
        
        metrics.increment_counter("total_tests", 10)
        metrics.increment_counter("successful_tests", 8)
        metrics.increment_counter("cache_hits", 15)
        metrics.increment_counter("cache_misses", 5)
        
        stats = metrics.get_statistics()
        
        # 检查指标统计
        assert "test_duration" in stats
        assert stats["test_duration"]["count"] == 3
        assert stats["test_duration"]["avg"] == 2.0
        assert stats["test_duration"]["min"] == 1.0
        assert stats["test_duration"]["max"] == 3.0
        
        # 检查计数器
        assert "counters" in stats
        assert stats["counters"]["total_tests"] == 10
        
        # 检查派生指标
        assert "test_success_rate" in stats
        assert stats["test_success_rate"] == 80.0
        
        assert "cache_hit_rate" in stats
        assert stats["cache_hit_rate"] == 75.0


class TestModelPerformanceService:
    """测试模型性能服务"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        return db
        
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ModelPerformanceService(mock_db)
        
    @pytest.fixture
    def mock_model_config(self):
        """模拟模型配置"""
        config = MagicMock(spec=ModelConfiguration)
        config.id = uuid.uuid4()
        config.model_type = "openai"
        config.model_name = "gpt-4"
        config.display_name = "GPT-4"
        config.input_price = 0.03
        config.output_price = 0.06
        return config
        
    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.db is not None
        assert isinstance(service._model_config_cache, dict)
        assert isinstance(service._test_progress, dict)
        assert service._performance_metrics is not None
        assert isinstance(service._active_tests, dict)
        
    @pytest.mark.asyncio
    async def test_get_model_config_cache_hit(self, service, mock_model_config):
        """测试模型配置缓存命中"""
        model_id = mock_model_config.id
        cache_key = str(model_id)
        
        # 预先放入缓存
        service._model_config_cache[cache_key] = mock_model_config
        
        result = await service._get_model_config(model_id)
        
        assert result == mock_model_config
        assert service._performance_metrics.counters["cache_hits"] == 1
        assert service._performance_metrics.counters["cache_misses"] == 0
        
    @pytest.mark.asyncio
    async def test_get_model_config_cache_miss(self, service, mock_model_config, mock_db):
        """测试模型配置缓存未命中"""
        model_id = mock_model_config.id
        
        # 模拟数据库查询
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_model_config
        mock_db.execute.return_value = mock_result
        
        result = await service._get_model_config(model_id)
        
        assert result == mock_model_config
        assert service._performance_metrics.counters["cache_hits"] == 0
        assert service._performance_metrics.counters["cache_misses"] == 1
        
        # 验证缓存已更新
        cache_key = str(model_id)
        assert cache_key in service._model_config_cache
        assert service._model_config_cache[cache_key] == mock_model_config
        
    def test_clear_model_config_cache(self, service):
        """测试清除模型配置缓存"""
        # 添加一些缓存项
        service._model_config_cache["test1"] = "config1"
        service._model_config_cache["test2"] = "config2"
        
        # 清除特定项
        test_id = uuid.uuid4()
        service._model_config_cache[str(test_id)] = "config3"
        service._clear_model_config_cache(test_id)
        
        assert str(test_id) not in service._model_config_cache
        assert "test1" in service._model_config_cache
        assert "test2" in service._model_config_cache
        
        # 清除所有
        service._clear_model_config_cache()
        assert len(service._model_config_cache) == 0
        
    def test_get_test_progress(self, service):
        """测试获取测试进度"""
        test_id = uuid.uuid4()
        
        # 没有进度时
        result = service.get_test_progress(test_id)
        assert result is None
        
        # 有进度时
        progress = TestProgress(test_id, 5)
        service._test_progress[str(test_id)] = progress
        
        result = service.get_test_progress(test_id)
        assert result is not None
        assert result["test_id"] == str(test_id)
        
    def test_get_performance_metrics(self, service):
        """测试获取性能指标"""
        # 添加一些指标
        service._performance_metrics.record_metric("test_duration", 1.5)
        service._performance_metrics.increment_counter("total_tests", 5)
        
        result = service.get_performance_metrics()
        
        assert "test_duration" in result
        assert "counters" in result
        assert result["counters"]["total_tests"] == 5
        
    @pytest.mark.asyncio
    async def test_cancel_test(self, service):
        """测试取消测试"""
        test_id = uuid.uuid4()
        
        # 创建模拟任务和进度
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        service._active_tests[str(test_id)] = mock_task
        
        progress = TestProgress(test_id, 5)
        progress.start_test()
        service._test_progress[str(test_id)] = progress
        
        # 取消测试
        result = await service.cancel_test(test_id)
        
        assert result is True
        mock_task.cancel.assert_called_once()
        assert progress.status == TestStatus.CANCELLED
