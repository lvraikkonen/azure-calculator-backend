from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_llm_factory
from app.models.user import User
from app.services.model_management.model_performance_service import ModelPerformanceService
from app.services.llm.factory import LLMServiceFactory
from app.schemas.model_management.performance import (
    TestResponse, TestDetailResponse, TestListResponse,
    SpeedTestRequest, LatencyTestRequest, TestResultSummary,
    BatchTestRequest, BatchTestResponse, TestComparisonRequest, TestComparisonResponse,
    TestScheduleRequest, TestScheduleResponse
)

router = APIRouter()


def get_performance_service(db: AsyncSession = Depends(get_db)) -> ModelPerformanceService:
    """获取性能测试服务实例"""
    return ModelPerformanceService(db)


@router.post("/models/{model_id}/performance/tests", response_model=TestResponse)
async def create_performance_test(
    model_id: UUID,
    request: SpeedTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service),
    llm_factory: LLMServiceFactory = Depends(get_llm_factory)
):
    """
    创建并执行性能测试
    
    Args:
        model_id: 模型ID
        request: 测试请求参数
        background_tasks: 后台任务
        current_user: 当前用户
        performance_service: 性能测试服务
        llm_factory: LLM服务工厂
    
    Returns:
        TestResponse: 测试结果
    """
    try:
        # 验证模型ID与请求中的模型ID一致
        if model_id != request.model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径中的模型ID与请求体中的模型ID不一致"
            )
        
        # 执行性能测试
        result = await performance_service.run_standard_test(request, llm_factory)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行性能测试失败: {str(e)}"
        )


@router.post("/models/{model_id}/performance/latency-tests", response_model=TestResponse)
async def create_latency_test(
    model_id: UUID,
    request: LatencyTestRequest,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service),
    llm_factory: LLMServiceFactory = Depends(get_llm_factory)
):
    """
    创建并执行延迟测试
    
    Args:
        model_id: 模型ID
        request: 延迟测试请求参数
        current_user: 当前用户
        performance_service: 性能测试服务
        llm_factory: LLM服务工厂
    
    Returns:
        TestResponse: 测试结果
    """
    try:
        # 验证模型ID与请求中的模型ID一致
        if model_id != request.model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径中的模型ID与请求体中的模型ID不一致"
            )
        
        # 执行延迟测试
        result = await performance_service.run_latency_test(request, llm_factory)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行延迟测试失败: {str(e)}"
        )


@router.get("/models/{model_id}/performance/tests", response_model=TestListResponse)
async def list_model_performance_tests(
    model_id: UUID,
    test_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    获取指定模型的性能测试列表
    
    Args:
        model_id: 模型ID
        test_type: 测试类型筛选
        limit: 分页限制
        offset: 分页偏移
        current_user: 当前用户
        performance_service: 性能测试服务
    
    Returns:
        TestListResponse: 测试列表响应
    """
    try:
        tests, total = await performance_service.list_tests(
            model_id=model_id,
            test_type=test_type,
            limit=limit,
            offset=offset
        )
        
        # 转换为摘要格式
        test_summaries = [
            TestResultSummary(
                id=test.id,
                test_name=test.test_name,
                test_type=test.test_type,
                model_id=test.model_id,
                model_name="模型名称",  # TODO: 从模型配置获取
                avg_response_time=test.avg_response_time,
                success_rate=test.success_rate,
                test_date=test.test_date
            )
            for test in tests
        ]
        
        return TestListResponse(
            total=total,
            tests=test_summaries
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取测试列表失败: {str(e)}"
        )


@router.get("/performance/tests/{test_id}", response_model=TestDetailResponse)
async def get_performance_test_detail(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    获取性能测试详情
    
    Args:
        test_id: 测试ID
        current_user: 当前用户
        performance_service: 性能测试服务
    
    Returns:
        TestDetailResponse: 测试详情
    """
    try:
        test = await performance_service.get_test_by_id(test_id)
        
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="测试记录不存在"
            )
        
        # 获取模型配置以获取模型名称
        model_config = await performance_service._get_model_config(test.model_id)
        model_name = model_config.display_name if model_config else "未知模型"
        
        # 构建详细响应
        return TestDetailResponse(
            id=test.id,
            model_id=test.model_id,
            model_name=model_name,
            test_name=test.test_name,
            test_type=test.test_type,
            rounds=test.rounds,
            avg_response_time=test.avg_response_time,
            avg_first_token_time=test.avg_first_token_time,
            avg_throughput=test.avg_throughput,
            success_rate=test.success_rate,
            error_rate=test.error_rate,
            test_params=test.test_params or {},
            test_date=test.test_date,
            tested_by=test.tested_by,
            # 详细信息
            detailed_results=test.detailed_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取测试详情失败: {str(e)}"
        )


@router.get("/performance/tests", response_model=TestListResponse)
async def list_all_performance_tests(
    model_id: Optional[UUID] = None,
    test_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    获取所有性能测试列表（支持筛选）
    
    Args:
        model_id: 模型ID筛选
        test_type: 测试类型筛选
        limit: 分页限制
        offset: 分页偏移
        current_user: 当前用户
        performance_service: 性能测试服务
    
    Returns:
        TestListResponse: 测试列表响应
    """
    try:
        tests, total = await performance_service.list_tests(
            model_id=model_id,
            test_type=test_type,
            limit=limit,
            offset=offset
        )
        
        # 转换为摘要格式
        test_summaries = [
            TestResultSummary(
                id=test.id,
                test_name=test.test_name,
                test_type=test.test_type,
                model_id=test.model_id,
                model_name="模型名称",  # TODO: 从模型配置获取
                avg_response_time=test.avg_response_time,
                success_rate=test.success_rate,
                test_date=test.test_date
            )
            for test in tests
        ]
        
        return TestListResponse(
            total=total,
            tests=test_summaries
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取测试列表失败: {str(e)}"
        )


@router.get("/performance/tests/{test_id}/progress")
async def get_test_progress(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    获取测试进度

    Args:
        test_id: 测试ID
        current_user: 当前用户
        performance_service: 性能测试服务

    Returns:
        Dict: 测试进度信息
    """
    try:
        progress = performance_service.get_test_progress(test_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="测试进度不存在或测试已完成"
            )

        return progress

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取测试进度失败: {str(e)}"
        )


@router.delete("/performance/tests/{test_id}")
async def cancel_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    取消正在运行的测试

    Args:
        test_id: 测试ID
        current_user: 当前用户
        performance_service: 性能测试服务

    Returns:
        Dict: 取消结果
    """
    try:
        success = await performance_service.cancel_test(test_id)

        return {
            "success": success,
            "message": "测试已取消" if success else "取消失败"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消测试失败: {str(e)}"
        )


@router.get("/performance/metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    获取性能指标统计

    Args:
        current_user: 当前用户
        performance_service: 性能测试服务

    Returns:
        Dict: 性能指标统计信息
    """
    try:
        metrics = performance_service.get_performance_metrics()
        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}"
        )


@router.post("/performance/tests/batch", response_model=BatchTestResponse)
async def create_batch_test(
    request: BatchTestRequest,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service),
    llm_factory: LLMServiceFactory = Depends(get_llm_factory)
):
    """
    创建并执行批量性能测试

    Args:
        request: 批量测试请求参数
        current_user: 当前用户
        performance_service: 性能测试服务
        llm_factory: LLM服务工厂

    Returns:
        BatchTestResponse: 批量测试结果
    """
    try:
        # 执行批量测试
        result = await performance_service.run_batch_test(request, llm_factory)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行批量测试失败: {str(e)}"
        )


@router.post("/performance/tests/compare", response_model=TestComparisonResponse)
async def compare_performance_tests(
    request: TestComparisonRequest,
    current_user: User = Depends(get_current_user),
    performance_service: ModelPerformanceService = Depends(get_performance_service)
):
    """
    比较多个性能测试结果

    Args:
        request: 测试比较请求参数
        current_user: 当前用户
        performance_service: 性能测试服务

    Returns:
        TestComparisonResponse: 比较结果
    """
    try:
        # 执行测试比较
        result = await performance_service.compare_tests(request)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"比较测试失败: {str(e)}"
        )


# ==================== Celery 任务相关端点 ====================

@router.post("/performance/tests/async", response_model=dict)
async def create_async_performance_test(
    model_id: UUID,
    request: SpeedTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    创建异步性能测试任务

    Args:
        model_id: 模型ID
        request: 测试请求参数
        current_user: 当前用户

    Returns:
        Dict: 任务信息
    """
    try:
        from celery_tasks.tasks.performance_tasks import run_performance_test

        # 验证模型ID与请求中的模型ID一致
        if model_id != request.model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径中的模型ID与请求体中的模型ID不一致"
            )

        # 提交异步任务
        task_result = run_performance_test.delay(
            test_request_data=request.dict(),
            test_type="standard"
        )

        return {
            "task_id": task_result.id,
            "status": "submitted",
            "message": "性能测试任务已提交，请使用task_id查询进度"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交异步测试任务失败: {str(e)}"
        )


@router.post("/performance/tests/async/batch", response_model=dict)
async def create_async_batch_test(
    request: BatchTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    创建异步批量测试任务

    Args:
        request: 批量测试请求参数
        current_user: 当前用户

    Returns:
        Dict: 任务信息
    """
    try:
        from celery_tasks.tasks.performance_tasks import run_batch_performance_test

        # 提交异步批量测试任务
        task_result = run_batch_performance_test.delay(
            batch_request_data=request.dict()
        )

        return {
            "task_id": task_result.id,
            "status": "submitted",
            "message": "批量测试任务已提交，请使用task_id查询进度"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交异步批量测试任务失败: {str(e)}"
        )


@router.get("/performance/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取异步任务状态

    Args:
        task_id: 任务ID
        current_user: 当前用户

    Returns:
        Dict: 任务状态信息
    """
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.status,
            "current": 0,
            "total": 100
        }

        if result.state == 'PENDING':
            response.update({
                "status": "pending",
                "message": "任务等待执行"
            })
        elif result.state == 'PROGRESS':
            response.update({
                "status": "running",
                "current": result.info.get('progress', 0),
                "message": result.info.get('status', '执行中')
            })
        elif result.state == 'SUCCESS':
            response.update({
                "status": "completed",
                "current": 100,
                "result": result.result,
                "message": "任务执行成功"
            })
        elif result.state == 'FAILURE':
            response.update({
                "status": "failed",
                "error": str(result.info),
                "message": "任务执行失败"
            })

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.delete("/performance/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消异步任务

    Args:
        task_id: 任务ID
        current_user: 当前用户

    Returns:
        Dict: 取消结果
    """
    try:
        from celery import current_app

        # 撤销任务
        current_app.control.revoke(task_id, terminate=True)

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "任务已取消"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )
