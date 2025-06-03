"""
Celery 性能测试任务的测试
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from celery_tasks.tasks.performance_tasks import (
    run_performance_test, run_batch_performance_test, 
    scheduled_performance_test, send_test_notification
)


class TestCeleryPerformanceTasks:
    """测试 Celery 性能测试任务"""
    
    @pytest.fixture
    def mock_test_request_data(self):
        """模拟测试请求数据"""
        return {
            "model_id": str(uuid.uuid4()),
            "test_type": "standard",
            "rounds": 3,
            "prompt": "测试提示词"
        }
    
    @pytest.fixture
    def mock_batch_request_data(self):
        """模拟批量测试请求数据"""
        return {
            "model_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "test_type": "standard",
            "rounds": 3,
            "prompt": "批量测试提示词"
        }
    
    @pytest.fixture
    def mock_schedule_config(self):
        """模拟调度配置"""
        return {
            "schedule_id": str(uuid.uuid4()),
            "model_ids": [str(uuid.uuid4())],
            "test_type": "standard",
            "rounds": 3,
            "prompt": "定时测试提示词",
            "notify_on_completion": True,
            "notify_on_failure": True,
            "notification_emails": ["test@example.com"]
        }
    
    def test_run_performance_test_task_structure(self, mock_test_request_data):
        """测试性能测试任务结构"""
        # 检查任务是否正确注册
        assert run_performance_test.name == "run_performance_test"
        assert run_performance_test.bind is True
        assert run_performance_test.max_retries == 3
        
        # 检查任务参数
        task_info = run_performance_test.s(mock_test_request_data, "standard")
        assert task_info.args == (mock_test_request_data, "standard")
    
    def test_run_batch_performance_test_task_structure(self, mock_batch_request_data):
        """测试批量性能测试任务结构"""
        # 检查任务是否正确注册
        assert run_batch_performance_test.name == "run_batch_performance_test"
        assert run_batch_performance_test.bind is True
        
        # 检查任务参数
        task_info = run_batch_performance_test.s(mock_batch_request_data)
        assert task_info.args == (mock_batch_request_data,)
    
    def test_scheduled_performance_test_task_structure(self, mock_schedule_config):
        """测试定时性能测试任务结构"""
        # 检查任务是否正确注册
        assert scheduled_performance_test.name == "scheduled_performance_test"
        
        # 检查任务参数
        task_info = scheduled_performance_test.s(mock_schedule_config)
        assert task_info.args == (mock_schedule_config,)
    
    def test_send_test_notification_task_structure(self):
        """测试通知发送任务结构"""
        # 检查任务是否正确注册
        assert send_test_notification.name == "send_test_notification"
        
        # 检查任务参数
        task_info = send_test_notification.s(
            "completion", 
            {"schedule_id": "test"}, 
            {"status": "success"}
        )
        assert len(task_info.args) == 3
    
    @patch('celery_tasks.tasks.performance_tasks.AsyncSessionLocal')
    @patch('celery_tasks.tasks.performance_tasks.ModelPerformanceService')
    @patch('celery_tasks.tasks.performance_tasks.LLMServiceFactory')
    def test_run_performance_test_success_flow(
        self, 
        mock_llm_factory, 
        mock_service_class, 
        mock_session_local,
        mock_test_request_data
    ):
        """测试性能测试任务成功流程"""
        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # 模拟服务实例
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # 模拟测试结果
        mock_result = MagicMock()
        mock_result.dict.return_value = {
            "id": str(uuid.uuid4()),
            "test_type": "standard",
            "success_rate": 100.0
        }
        mock_service.run_standard_test.return_value = mock_result
        
        # 模拟LLM工厂
        mock_factory = MagicMock()
        mock_llm_factory.return_value = mock_factory
        
        # 创建模拟任务实例
        mock_task = MagicMock()
        mock_task.request.id = "test_task_id"
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # 执行任务（模拟）
        with patch('celery_tasks.tasks.performance_tasks.current_task', mock_task):
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_result.dict()
                
                # 调用任务函数
                result = run_performance_test(
                    mock_task, 
                    mock_test_request_data, 
                    "standard"
                )
                
                # 验证结果
                assert result == mock_result.dict()
                mock_task.update_state.assert_called()
    
    @patch('celery_tasks.tasks.performance_tasks.AsyncSessionLocal')
    @patch('celery_tasks.tasks.performance_tasks.ModelPerformanceService')
    @patch('celery_tasks.tasks.performance_tasks.LLMServiceFactory')
    def test_run_batch_performance_test_success_flow(
        self, 
        mock_llm_factory, 
        mock_service_class, 
        mock_session_local,
        mock_batch_request_data
    ):
        """测试批量性能测试任务成功流程"""
        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # 模拟服务实例
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # 模拟批量测试结果
        mock_result = MagicMock()
        mock_result.dict.return_value = {
            "batch_id": str(uuid.uuid4()),
            "total_models": 2,
            "completed_tests": [],
            "failed_tests": [],
            "status": "completed"
        }
        mock_service.run_batch_test.return_value = mock_result
        
        # 模拟LLM工厂
        mock_factory = MagicMock()
        mock_llm_factory.return_value = mock_factory
        
        # 创建模拟任务实例
        mock_task = MagicMock()
        mock_task.request.id = "test_batch_task_id"
        
        # 执行任务（模拟）
        with patch('celery_tasks.tasks.performance_tasks.current_task', mock_task):
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_result.dict()
                
                # 调用任务函数
                result = run_batch_performance_test(
                    mock_task, 
                    mock_batch_request_data
                )
                
                # 验证结果
                assert result == mock_result.dict()
                mock_task.update_state.assert_called()
    
    @patch('celery_tasks.tasks.performance_tasks.AsyncSessionLocal')
    @patch('celery_tasks.tasks.performance_tasks.ModelPerformanceService')
    @patch('celery_tasks.tasks.performance_tasks.LLMServiceFactory')
    @patch('celery_tasks.tasks.performance_tasks.send_test_notification')
    def test_scheduled_performance_test_success_flow(
        self, 
        mock_send_notification,
        mock_llm_factory, 
        mock_service_class, 
        mock_session_local,
        mock_schedule_config
    ):
        """测试定时性能测试任务成功流程"""
        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # 模拟服务实例
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # 模拟测试结果
        mock_test_result = MagicMock()
        mock_test_result.dict.return_value = {
            "id": str(uuid.uuid4()),
            "success_rate": 100.0
        }
        mock_service.run_standard_test.return_value = mock_test_result
        
        # 模拟LLM工厂
        mock_factory = MagicMock()
        mock_llm_factory.return_value = mock_factory
        
        # 模拟通知任务
        mock_send_notification.delay.return_value = MagicMock()
        
        # 执行任务（模拟）
        with patch('asyncio.run') as mock_asyncio_run:
            # 模拟异步函数返回值
            expected_result = {
                "schedule_id": mock_schedule_config["schedule_id"],
                "execution_time": datetime.now(timezone.utc).isoformat(),
                "total_models": 1,
                "successful_tests": 1,
                "failed_tests": 0,
                "results": [{
                    "model_id": mock_schedule_config["model_ids"][0],
                    "status": "success",
                    "result": mock_test_result.dict()
                }]
            }
            mock_asyncio_run.return_value = expected_result
            
            # 调用任务函数
            result = scheduled_performance_test(mock_schedule_config)
            
            # 验证结果
            assert result["schedule_id"] == mock_schedule_config["schedule_id"]
            assert result["total_models"] == 1
            assert result["successful_tests"] == 1
            assert result["failed_tests"] == 0
            
            # 验证通知发送
            mock_send_notification.delay.assert_called_once()
    
    def test_send_test_notification_completion(self):
        """测试完成通知发送"""
        schedule_config = {
            "schedule_id": "test_schedule",
            "notification_emails": ["test@example.com"]
        }
        
        test_results = {
            "execution_time": datetime.now(timezone.utc).isoformat(),
            "total_models": 2,
            "successful_tests": 2,
            "failed_tests": 0
        }
        
        # 调用通知函数
        result = send_test_notification(
            "completion", 
            schedule_config, 
            test_results
        )
        
        # 验证结果
        assert result["status"] == "success"
        assert "通知发送成功" in result["message"]
    
    def test_send_test_notification_failure(self):
        """测试失败通知发送"""
        schedule_config = {
            "schedule_id": "test_schedule",
            "notification_emails": ["test@example.com"]
        }
        
        error_message = "测试执行失败"
        
        # 调用通知函数
        result = send_test_notification(
            "failure", 
            schedule_config, 
            error_message=error_message
        )
        
        # 验证结果
        assert result["status"] == "success"
        assert "通知发送成功" in result["message"]
    
    def test_task_retry_mechanism(self, mock_test_request_data):
        """测试任务重试机制"""
        # 创建模拟任务实例
        mock_task = MagicMock()
        mock_task.request.id = "test_task_id"
        mock_task.request.retries = 1
        mock_task.max_retries = 3
        mock_task.retry.side_effect = Exception("Retry triggered")
        
        # 模拟异常
        with patch('celery_tasks.tasks.performance_tasks.current_task', mock_task):
            with patch('asyncio.run', side_effect=Exception("Test error")):
                
                # 调用任务函数，期望重试
                try:
                    run_performance_test(
                        mock_task, 
                        mock_test_request_data, 
                        "standard"
                    )
                except Exception as e:
                    assert "Retry triggered" in str(e)
                
                # 验证重试被调用
                mock_task.retry.assert_called_once()
    
    def test_task_max_retries_exceeded(self, mock_test_request_data):
        """测试超过最大重试次数"""
        # 创建模拟任务实例
        mock_task = MagicMock()
        mock_task.request.id = "test_task_id"
        mock_task.request.retries = 3  # 已达到最大重试次数
        mock_task.max_retries = 3
        
        # 模拟异常
        with patch('celery_tasks.tasks.performance_tasks.current_task', mock_task):
            with patch('asyncio.run', side_effect=Exception("Test error")):
                
                # 调用任务函数
                result = run_performance_test(
                    mock_task, 
                    mock_test_request_data, 
                    "standard"
                )
                
                # 验证返回错误结果
                assert result["status"] == "error"
                assert "Test error" in result["message"]
                
                # 验证状态更新为失败
                mock_task.update_state.assert_called_with(
                    state='FAILURE',
                    meta={
                        'status': 'failed',
                        'error': 'Test error',
                        'progress': 0
                    }
                )
