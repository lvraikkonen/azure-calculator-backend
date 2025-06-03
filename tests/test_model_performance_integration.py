"""
ModelPerformanceService 集成测试
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.model_management.model_performance_service import ModelPerformanceService
from app.schemas.model_management.performance import (
    SpeedTestRequest, LatencyTestRequest, BatchTestRequest, TestComparisonRequest
)


class TestPerformanceAPIIntegration:
    """性能测试API集成测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
        
    @pytest.fixture
    async def async_client(self):
        """创建异步测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
            
    @pytest.fixture
    def mock_user_token(self):
        """模拟用户认证令牌"""
        # 这里应该返回有效的JWT令牌
        return "Bearer mock_token"
        
    @pytest.fixture
    def test_model_id(self):
        """测试模型ID"""
        return uuid.uuid4()
        
    @pytest.mark.asyncio
    async def test_create_performance_test_endpoint(self, async_client, mock_user_token, test_model_id):
        """测试创建性能测试端点"""
        request_data = {
            "model_id": str(test_model_id),
            "test_type": "standard",
            "rounds": 3,
            "prompt": "测试提示词"
        }
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_llm_factory') as mock_get_factory, \
             patch('app.services.model_management.model_performance_service.ModelPerformanceService.run_standard_test') as mock_run_test:
            
            # 模拟用户认证
            mock_get_user.return_value = MagicMock(id=uuid.uuid4())
            
            # 模拟LLM工厂
            mock_get_factory.return_value = MagicMock()
            
            # 模拟测试执行结果
            mock_run_test.return_value = {
                "id": uuid.uuid4(),
                "model_id": test_model_id,
                "test_name": "标准测试",
                "test_type": "standard",
                "rounds": 3,
                "avg_response_time": 1500.0,
                "success_rate": 100.0,
                "test_date": datetime.now(timezone.utc)
            }
            
            response = await async_client.post(
                f"/api/v1/models/{test_model_id}/performance/tests",
                json=request_data,
                headers={"Authorization": mock_user_token}
            )
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["test_type"] == "standard"
            assert data["rounds"] == 3
            
    @pytest.mark.asyncio
    async def test_get_test_progress_endpoint(self, async_client, mock_user_token):
        """测试获取测试进度端点"""
        test_id = uuid.uuid4()
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.services.model_management.model_performance_service.ModelPerformanceService.get_test_progress') as mock_get_progress:
            
            mock_get_user.return_value = MagicMock(id=uuid.uuid4())
            
            # 模拟进度数据
            mock_get_progress.return_value = {
                "test_id": str(test_id),
                "status": "running",
                "total_rounds": 5,
                "completed_rounds": 2,
                "failed_rounds": 0,
                "progress_percentage": 40.0
            }
            
            response = await async_client.get(
                f"/api/v1/performance/tests/{test_id}/progress",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["test_id"] == str(test_id)
            assert data["status"] == "running"
            assert data["progress_percentage"] == 40.0
            
    @pytest.mark.asyncio
    async def test_cancel_test_endpoint(self, async_client, mock_user_token):
        """测试取消测试端点"""
        test_id = uuid.uuid4()
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.services.model_management.model_performance_service.ModelPerformanceService.cancel_test') as mock_cancel:
            
            mock_get_user.return_value = MagicMock(id=uuid.uuid4())
            mock_cancel.return_value = True
            
            response = await async_client.delete(
                f"/api/v1/performance/tests/{test_id}",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已取消" in data["message"]
            
    @pytest.mark.asyncio
    async def test_get_performance_metrics_endpoint(self, async_client, mock_user_token):
        """测试获取性能指标端点"""
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.services.model_management.model_performance_service.ModelPerformanceService.get_performance_metrics') as mock_get_metrics:
            
            mock_get_user.return_value = MagicMock(id=uuid.uuid4())
            
            # 模拟指标数据
            mock_get_metrics.return_value = {
                "test_duration": {
                    "count": 10,
                    "avg": 2.5,
                    "min": 1.0,
                    "max": 5.0
                },
                "counters": {
                    "total_tests": 10,
                    "successful_tests": 8,
                    "failed_tests": 2
                },
                "test_success_rate": 80.0
            }
            
            response = await async_client.get(
                "/api/v1/performance/metrics",
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "test_duration" in data
            assert "counters" in data
            assert data["test_success_rate"] == 80.0
            
    @pytest.mark.asyncio
    async def test_batch_test_endpoint(self, async_client, mock_user_token):
        """测试批量测试端点"""
        model_ids = [uuid.uuid4(), uuid.uuid4()]
        
        request_data = {
            "model_ids": [str(mid) for mid in model_ids],
            "test_type": "standard",
            "rounds": 3,
            "prompt": "批量测试提示词"
        }
        
        with patch('app.api.deps.get_current_user') as mock_get_user, \
             patch('app.api.deps.get_llm_factory') as mock_get_factory, \
             patch('app.services.model_management.model_performance_service.ModelPerformanceService.run_batch_test') as mock_batch_test:
            
            mock_get_user.return_value = MagicMock(id=uuid.uuid4())
            mock_get_factory.return_value = MagicMock()
            
            # 模拟批量测试结果
            mock_batch_test.return_value = {
                "batch_id": uuid.uuid4(),
                "total_models": 2,
                "completed_tests": [
                    {
                        "id": uuid.uuid4(),
                        "model_id": model_ids[0],
                        "test_type": "standard",
                        "success_rate": 100.0
                    }
                ],
                "failed_tests": [
                    {
                        "model_id": str(model_ids[1]),
                        "error": "模型不可用"
                    }
                ],
                "status": "partial"
            }
            
            response = await async_client.post(
                "/api/v1/performance/tests/batch",
                json=request_data,
                headers={"Authorization": mock_user_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "batch_id" in data
            assert data["total_models"] == 2
            assert data["status"] == "partial"
            assert len(data["completed_tests"]) == 1
            assert len(data["failed_tests"]) == 1


class TestPerformanceServiceIntegration:
    """性能服务集成测试"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        
        # 模拟查询结果
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
    def mock_llm_service(self):
        """模拟LLM服务"""
        llm_service = AsyncMock()
        
        # 模拟流式响应
        async def mock_chat_stream(*args, **kwargs):
            chunks = [
                {"content": "Hello"},
                {"content": " world"},
                {"content": "!"}
            ]
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.01)  # 模拟网络延迟
                
        llm_service.chat_stream = mock_chat_stream
        return llm_service
        
    @pytest.mark.asyncio
    async def test_service_with_real_workflow(self, service, mock_llm_service):
        """测试服务的真实工作流程"""
        # 创建测试记录
        test_data = {
            "model_id": uuid.uuid4(),
            "test_name": "集成测试",
            "test_type": "standard",
            "rounds": 2,
            "test_params": {"prompt": "测试提示词"}
        }
        
        # 模拟模型配置
        mock_config = MagicMock()
        mock_config.id = test_data["model_id"]
        mock_config.model_type = "openai"
        mock_config.model_name = "gpt-4"
        mock_config.input_price = 0.03
        mock_config.output_price = 0.06
        
        # 将配置放入缓存
        service._model_config_cache[str(test_data["model_id"])] = mock_config
        
        # 模拟测试记录
        mock_test_record = MagicMock()
        mock_test_record.id = uuid.uuid4()
        mock_test_record.model_id = test_data["model_id"]
        
        with patch('app.utils.token_counter.count_tokens') as mock_count_tokens:
            # 模拟token计数
            mock_count_tokens.side_effect = lambda text, *args: len(text.split())
            
            # 执行测试
            result = await service._execute_standard_test(
                llm_service=mock_llm_service,
                test_record=mock_test_record,
                prompt="测试提示词",
                rounds=2
            )
            
            # 验证结果
            assert "avg_response_time" in result
            assert "success_rate" in result
            assert "detailed_results" in result
            assert result["success_rate"] == 100.0  # 所有轮次都应该成功
            
            # 验证进度跟踪
            progress = service.get_test_progress(mock_test_record.id)
            assert progress is not None
            assert progress["status"] == "completed"
            assert progress["completed_rounds"] == 2
            assert progress["failed_rounds"] == 0
            
            # 验证性能指标
            metrics = service.get_performance_metrics()
            assert metrics["counters"]["total_tests"] == 1
            assert metrics["counters"]["successful_tests"] == 1
            assert metrics["counters"]["total_rounds"] == 2
            assert metrics["counters"]["successful_rounds"] == 2
