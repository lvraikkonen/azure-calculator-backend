"""
性能测试相关的 Celery 任务
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from celery import current_task
from celery.exceptions import Retry

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.model_performance_test import ModelPerformanceTest
from app.models.model_configuration import ModelConfiguration
from app.services.model_management.model_performance_service import ModelPerformanceService
from app.services.llm.factory import LLMServiceFactory
from app.schemas.model_management.performance import (
    SpeedTestRequest, LatencyTestRequest, BatchTestRequest
)
from celery_tasks.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(name="run_performance_test", bind=True, max_retries=3)
def run_performance_test(self, test_request_data: Dict[str, Any], test_type: str = "standard"):
    """
    执行单个性能测试任务
    
    Args:
        test_request_data: 测试请求数据
        test_type: 测试类型 (standard, latency)
    
    Returns:
        Dict: 测试结果
    """
    try:
        logger.info(f"开始执行性能测试任务: {current_task.request.id}")
        
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': 'initializing', 'progress': 0}
        )
        
        async def _execute_test():
            async with AsyncSessionLocal() as session:
                # 创建服务实例
                performance_service = ModelPerformanceService(session)
                llm_factory = LLMServiceFactory()
                
                try:
                    if test_type == "standard":
                        # 创建标准测试请求
                        request = SpeedTestRequest(**test_request_data)
                        result = await performance_service.run_standard_test(request, llm_factory)
                    elif test_type == "latency":
                        # 创建延迟测试请求
                        request = LatencyTestRequest(**test_request_data)
                        result = await performance_service.run_latency_test(request, llm_factory)
                    else:
                        raise ValueError(f"不支持的测试类型: {test_type}")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"性能测试执行失败: {str(e)}", exc_info=True)
                    raise
        
        # 执行异步测试
        result = asyncio.run(_execute_test())
        
        # 更新任务状态为完成
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'completed',
                'progress': 100,
                'result': result.dict() if hasattr(result, 'dict') else result
            }
        )
        
        logger.info(f"性能测试任务完成: {current_task.request.id}")
        return result.dict() if hasattr(result, 'dict') else result
        
    except Exception as e:
        logger.error(f"性能测试任务失败: {str(e)}", exc_info=True)
        
        # 重试逻辑
        if self.request.retries < self.max_retries:
            logger.info(f"重试性能测试任务 (第 {self.request.retries + 1} 次)")
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # 指数退避
        
        # 更新任务状态为失败
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e),
                'progress': 0
            }
        )
        
        return {"status": "error", "message": str(e)}


@celery_app.task(name="run_batch_performance_test", bind=True)
def run_batch_performance_test(self, batch_request_data: Dict[str, Any]):
    """
    执行批量性能测试任务
    
    Args:
        batch_request_data: 批量测试请求数据
    
    Returns:
        Dict: 批量测试结果
    """
    try:
        logger.info(f"开始执行批量性能测试任务: {current_task.request.id}")
        
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': 'initializing', 'progress': 0}
        )
        
        async def _execute_batch_test():
            async with AsyncSessionLocal() as session:
                # 创建服务实例
                performance_service = ModelPerformanceService(session)
                llm_factory = LLMServiceFactory()
                
                # 创建批量测试请求
                request = BatchTestRequest(**batch_request_data)
                
                # 执行批量测试
                result = await performance_service.run_batch_test(request, llm_factory)
                return result
        
        # 执行异步批量测试
        result = asyncio.run(_execute_batch_test())
        
        # 更新任务状态为完成
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'completed',
                'progress': 100,
                'result': result.dict() if hasattr(result, 'dict') else result
            }
        )
        
        logger.info(f"批量性能测试任务完成: {current_task.request.id}")
        return result.dict() if hasattr(result, 'dict') else result
        
    except Exception as e:
        logger.error(f"批量性能测试任务失败: {str(e)}", exc_info=True)
        
        # 更新任务状态为失败
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e),
                'progress': 0
            }
        )
        
        return {"status": "error", "message": str(e)}


@celery_app.task(name="scheduled_performance_test")
def scheduled_performance_test(schedule_config: Dict[str, Any]):
    """
    定时性能测试任务
    
    Args:
        schedule_config: 调度配置
    
    Returns:
        Dict: 调度执行结果
    """
    try:
        logger.info(f"开始执行定时性能测试: {schedule_config.get('schedule_id')}")
        
        async def _execute_scheduled_test():
            async with AsyncSessionLocal() as session:
                # 创建服务实例
                performance_service = ModelPerformanceService(session)
                llm_factory = LLMServiceFactory()
                
                # 提取测试配置
                model_ids = schedule_config.get('model_ids', [])
                test_type = schedule_config.get('test_type', 'standard')
                rounds = schedule_config.get('rounds', 3)
                prompt = schedule_config.get('prompt')
                
                results = []
                
                # 为每个模型执行测试
                for model_id in model_ids:
                    try:
                        if test_type == "standard":
                            request_data = {
                                "model_id": model_id,
                                "test_type": test_type,
                                "rounds": rounds,
                                "prompt": prompt
                            }
                            request = SpeedTestRequest(**request_data)
                            result = await performance_service.run_standard_test(request, llm_factory)
                        elif test_type == "latency":
                            request_data = {
                                "model_id": model_id,
                                "rounds": rounds,
                                "measure_first_token": True
                            }
                            request = LatencyTestRequest(**request_data)
                            result = await performance_service.run_latency_test(request, llm_factory)
                        
                        results.append({
                            "model_id": str(model_id),
                            "status": "success",
                            "result": result.dict() if hasattr(result, 'dict') else result
                        })
                        
                    except Exception as e:
                        logger.error(f"模型 {model_id} 的定时测试失败: {str(e)}")
                        results.append({
                            "model_id": str(model_id),
                            "status": "error",
                            "error": str(e)
                        })
                
                return {
                    "schedule_id": schedule_config.get('schedule_id'),
                    "execution_time": datetime.now(timezone.utc).isoformat(),
                    "total_models": len(model_ids),
                    "successful_tests": len([r for r in results if r["status"] == "success"]),
                    "failed_tests": len([r for r in results if r["status"] == "error"]),
                    "results": results
                }
        
        # 执行定时测试
        result = asyncio.run(_execute_scheduled_test())
        
        # 发送通知（如果配置了）
        if schedule_config.get('notify_on_completion', False):
            send_test_notification.delay(
                notification_type="completion",
                schedule_config=schedule_config,
                test_results=result
            )
        
        logger.info(f"定时性能测试完成: {schedule_config.get('schedule_id')}")
        return result
        
    except Exception as e:
        logger.error(f"定时性能测试失败: {str(e)}", exc_info=True)
        
        # 发送失败通知
        if schedule_config.get('notify_on_failure', False):
            send_test_notification.delay(
                notification_type="failure",
                schedule_config=schedule_config,
                error_message=str(e)
            )
        
        return {"status": "error", "message": str(e)}


@celery_app.task(name="send_test_notification")
def send_test_notification(notification_type: str, schedule_config: Dict[str, Any], 
                          test_results: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None):
    """
    发送测试通知
    
    Args:
        notification_type: 通知类型 (completion, failure)
        schedule_config: 调度配置
        test_results: 测试结果（成功时）
        error_message: 错误信息（失败时）
    
    Returns:
        Dict: 通知发送结果
    """
    try:
        logger.info(f"发送测试通知: {notification_type}")
        
        # 这里可以集成邮件服务、Slack、钉钉等通知方式
        # 目前先记录日志
        
        if notification_type == "completion":
            message = f"""
            性能测试完成通知
            
            调度ID: {schedule_config.get('schedule_id')}
            执行时间: {test_results.get('execution_time') if test_results else 'N/A'}
            总模型数: {test_results.get('total_models', 0) if test_results else 0}
            成功测试: {test_results.get('successful_tests', 0) if test_results else 0}
            失败测试: {test_results.get('failed_tests', 0) if test_results else 0}
            """
        elif notification_type == "failure":
            message = f"""
            性能测试失败通知
            
            调度ID: {schedule_config.get('schedule_id')}
            失败时间: {datetime.now(timezone.utc).isoformat()}
            错误信息: {error_message}
            """
        else:
            message = f"未知通知类型: {notification_type}"
        
        logger.info(f"通知内容: {message}")
        
        # TODO: 实际的通知发送逻辑
        # 可以集成邮件服务、消息队列等
        
        return {"status": "success", "message": "通知发送成功"}
        
    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
