"""
ModelPerformanceService 性能基准测试
用于验证服务在高负载下的性能表现
"""

import pytest
import uuid
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from app.services.model_management.model_performance_service import (
    ModelPerformanceService, PerformanceTestConfig
)


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """高性能模拟数据库会话"""
        session = AsyncMock()
        
        # 模拟快速查询响应
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one.return_value = 0
        
        session.execute.return_value = mock_result
        return session
        
    @pytest.fixture
    def service(self, mock_db_session):
        """创建服务实例"""
        return ModelPerformanceService(mock_db_session)
        
    @pytest.fixture
    def fast_mock_llm_service(self):
        """快速模拟LLM服务"""
        llm_service = AsyncMock()
        
        async def fast_chat_stream(*args, **kwargs):
            # 模拟快速响应
            yield {"content": "Fast response"}
            await asyncio.sleep(0.001)  # 1ms延迟
                
        llm_service.chat_stream = fast_chat_stream
        return llm_service
        
    @pytest.mark.asyncio
    async def test_cache_performance(self, service):
        """测试缓存性能"""
        model_id = uuid.uuid4()
        
        # 模拟模型配置
        mock_config = MagicMock()
        mock_config.id = model_id
        mock_config.model_type = "openai"
        mock_config.model_name = "gpt-4"
        
        # 预热缓存
        service._model_config_cache[str(model_id)] = mock_config
        
        # 测试缓存命中性能
        start_time = time.perf_counter()
        
        for _ in range(1000):
            result = await service._get_model_config(model_id)
            assert result == mock_config
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 验证性能：1000次缓存命中应该在100ms内完成
        assert total_time < 0.1, f"缓存性能不佳: {total_time:.3f}s for 1000 hits"
        
        # 验证缓存命中率
        metrics = service.get_performance_metrics()
        assert metrics["cache_hit_rate"] == 100.0
        
    @pytest.mark.asyncio
    async def test_concurrent_test_execution(self, service, fast_mock_llm_service):
        """测试并发测试执行性能"""
        # 创建多个测试记录
        test_records = []
        for i in range(10):
            mock_record = MagicMock()
            mock_record.id = uuid.uuid4()
            mock_record.model_id = uuid.uuid4()
            test_records.append(mock_record)
            
            # 为每个模型添加配置
            mock_config = MagicMock()
            mock_config.id = mock_record.model_id
            mock_config.model_type = "openai"
            mock_config.model_name = f"gpt-4-{i}"
            mock_config.input_price = 0.03
            mock_config.output_price = 0.06
            service._model_config_cache[str(mock_record.model_id)] = mock_config
        
        with patch('app.utils.token_counter.count_tokens') as mock_count_tokens:
            mock_count_tokens.return_value = 10
            
            # 并发执行测试
            start_time = time.perf_counter()
            
            tasks = []
            for record in test_records:
                task = service._execute_standard_test(
                    llm_service=fast_mock_llm_service,
                    test_record=record,
                    prompt="性能测试",
                    rounds=3
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # 验证所有测试都成功
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 10
            
            # 验证并发性能：10个测试应该在合理时间内完成
            assert total_time < 5.0, f"并发测试性能不佳: {total_time:.3f}s for 10 tests"
            
            # 验证性能指标
            metrics = service.get_performance_metrics()
            assert metrics["counters"]["total_tests"] == 10
            assert metrics["counters"]["successful_tests"] == 10
            
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, service, fast_mock_llm_service):
        """测试高负载下的内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量测试
        for batch in range(5):  # 5批次
            tasks = []
            for i in range(20):  # 每批20个测试
                mock_record = MagicMock()
                mock_record.id = uuid.uuid4()
                mock_record.model_id = uuid.uuid4()
                
                # 添加模型配置
                mock_config = MagicMock()
                mock_config.id = mock_record.model_id
                mock_config.model_type = "openai"
                mock_config.model_name = f"gpt-4-batch{batch}-{i}"
                mock_config.input_price = 0.03
                mock_config.output_price = 0.06
                service._model_config_cache[str(mock_record.model_id)] = mock_config
                
                with patch('app.utils.token_counter.count_tokens') as mock_count_tokens:
                    mock_count_tokens.return_value = 10
                    
                    task = service._execute_standard_test(
                        llm_service=fast_mock_llm_service,
                        test_record=mock_record,
                        prompt="内存测试",
                        rounds=2
                    )
                    tasks.append(task)
            
            # 执行当前批次
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查内存使用
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # 内存增长不应该超过100MB
            assert memory_increase < 100, f"内存使用过高: {memory_increase:.2f}MB increase"
            
    @pytest.mark.asyncio
    async def test_progress_tracking_performance(self, service):
        """测试进度跟踪性能"""
        # 创建大量进度跟踪对象
        test_ids = [uuid.uuid4() for _ in range(1000)]
        
        start_time = time.perf_counter()
        
        # 创建进度跟踪
        for test_id in test_ids:
            from app.services.model_management.model_performance_service import TestProgress
            progress = TestProgress(test_id, 10)
            service._test_progress[str(test_id)] = progress
            
        # 更新所有进度
        for test_id in test_ids:
            progress = service._test_progress[str(test_id)]
            progress.start_test()
            for round_num in range(1, 11):
                progress.start_round(round_num)
                progress.complete_round(round_num, success=True)
            progress.complete_test(success=True)
            
        # 获取所有进度
        for test_id in test_ids:
            result = service.get_test_progress(test_id)
            assert result is not None
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 验证性能：1000个进度跟踪操作应该在1秒内完成
        assert total_time < 1.0, f"进度跟踪性能不佳: {total_time:.3f}s for 1000 operations"
        
    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self, service):
        """测试指标收集性能"""
        start_time = time.perf_counter()
        
        # 大量指标记录
        for i in range(10000):
            service._performance_metrics.record_metric("test_duration", i * 0.1)
            service._performance_metrics.record_metric("round_duration", i * 0.05)
            service._performance_metrics.increment_counter("total_tests")
            if i % 10 == 0:
                service._performance_metrics.increment_counter("successful_tests")
                
        # 获取统计信息
        for _ in range(100):
            stats = service.get_performance_metrics()
            assert "test_duration" in stats
            assert stats["counters"]["total_tests"] == 10000
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 验证性能：大量指标操作应该在合理时间内完成
        assert total_time < 2.0, f"指标收集性能不佳: {total_time:.3f}s"
        
    def test_configuration_access_performance(self):
        """测试配置访问性能"""
        start_time = time.perf_counter()
        
        # 大量配置访问
        for _ in range(100000):
            _ = PerformanceTestConfig.DEFAULT_SLEEP_INTERVAL
            _ = PerformanceTestConfig.MAX_ROUNDS
            _ = PerformanceTestConfig.MAX_CONCURRENT_TESTS
            _ = PerformanceTestConfig.DEFAULT_PROMPTS
            
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 验证性能：配置访问应该非常快
        assert total_time < 0.1, f"配置访问性能不佳: {total_time:.3f}s for 100k accesses"
        
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, service, mock_db_session):
        """测试错误处理性能"""
        # 模拟会抛出异常的LLM服务
        error_llm_service = AsyncMock()
        
        async def error_chat_stream(*args, **kwargs):
            await asyncio.sleep(0.001)
            raise Exception("模拟错误")
                
        error_llm_service.chat_stream = error_chat_stream
        
        # 创建测试记录
        mock_record = MagicMock()
        mock_record.id = uuid.uuid4()
        mock_record.model_id = uuid.uuid4()
        
        # 添加模型配置
        mock_config = MagicMock()
        mock_config.id = mock_record.model_id
        mock_config.model_type = "openai"
        mock_config.model_name = "gpt-4"
        mock_config.input_price = 0.03
        mock_config.output_price = 0.06
        service._model_config_cache[str(mock_record.model_id)] = mock_config
        
        with patch('app.utils.token_counter.count_tokens') as mock_count_tokens:
            mock_count_tokens.return_value = 10
            
            start_time = time.perf_counter()
            
            # 执行会失败的测试
            result = await service._execute_standard_test(
                llm_service=error_llm_service,
                test_record=mock_record,
                prompt="错误测试",
                rounds=5
            )
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # 验证错误处理：即使有错误，也应该快速完成
            assert total_time < 2.0, f"错误处理性能不佳: {total_time:.3f}s"
            
            # 验证结果
            assert result["success_rate"] == 0.0  # 所有轮次都失败
            assert len(result["detailed_results"]["errors"]) == 5  # 5个错误
            
            # 验证进度跟踪
            progress = service.get_test_progress(mock_record.id)
            assert progress["status"] == "failed"
            assert progress["failed_rounds"] == 5
