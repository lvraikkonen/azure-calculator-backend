"""
性能测试调度管理 API 端点
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.model_management.performance_scheduler_service import PerformanceSchedulerService
from app.schemas.model_management.performance import (
    TestScheduleRequest, TestScheduleResponse
)

router = APIRouter()


def get_scheduler_service(db: AsyncSession = Depends(get_db)) -> PerformanceSchedulerService:
    """获取调度服务实例"""
    return PerformanceSchedulerService(db)


@router.post("/performance/schedules", response_model=TestScheduleResponse)
async def create_schedule(
    request: TestScheduleRequest,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    创建性能测试调度
    
    Args:
        request: 调度请求参数
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        TestScheduleResponse: 调度响应
    """
    try:
        schedule = await scheduler_service.create_schedule(
            request=request,
            created_by=current_user.id
        )
        
        return schedule
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建调度失败: {str(e)}"
        )


@router.get("/performance/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    获取调度详情
    
    Args:
        schedule_id: 调度ID
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        Dict: 调度详情
    """
    try:
        schedule = await scheduler_service.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="调度不存在"
            )
        
        return schedule
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度失败: {str(e)}"
        )


@router.get("/performance/schedules")
async def list_schedules(
    status_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    获取调度列表
    
    Args:
        status_filter: 状态筛选
        limit: 分页限制
        offset: 分页偏移
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        List: 调度列表
    """
    try:
        schedules = await scheduler_service.list_schedules(
            status=status_filter,
            limit=limit,
            offset=offset
        )
        
        return {
            "schedules": schedules,
            "total": len(schedules),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取调度列表失败: {str(e)}"
        )


@router.put("/performance/schedules/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    暂停调度
    
    Args:
        schedule_id: 调度ID
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        Dict: 操作结果
    """
    try:
        success = await scheduler_service.pause_schedule(schedule_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="调度不存在或无法暂停"
            )
        
        return {
            "schedule_id": str(schedule_id),
            "status": "paused",
            "message": "调度已暂停"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"暂停调度失败: {str(e)}"
        )


@router.put("/performance/schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    恢复调度
    
    Args:
        schedule_id: 调度ID
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        Dict: 操作结果
    """
    try:
        success = await scheduler_service.resume_schedule(schedule_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="调度不存在或无法恢复"
            )
        
        return {
            "schedule_id": str(schedule_id),
            "status": "active",
            "message": "调度已恢复"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复调度失败: {str(e)}"
        )


@router.delete("/performance/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    删除调度
    
    Args:
        schedule_id: 调度ID
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        Dict: 操作结果
    """
    try:
        success = await scheduler_service.delete_schedule(schedule_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="调度不存在"
            )
        
        return {
            "schedule_id": str(schedule_id),
            "status": "deleted",
            "message": "调度已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除调度失败: {str(e)}"
        )


@router.get("/performance/schedules/{schedule_id}/tasks/{task_id}/status")
async def get_schedule_task_status(
    schedule_id: UUID,
    task_id: str,
    current_user: User = Depends(get_current_user),
    scheduler_service: PerformanceSchedulerService = Depends(get_scheduler_service)
):
    """
    获取调度任务状态
    
    Args:
        schedule_id: 调度ID
        task_id: 任务ID
        current_user: 当前用户
        scheduler_service: 调度服务
    
    Returns:
        Dict: 任务状态信息
    """
    try:
        # 验证调度存在
        schedule = await scheduler_service.get_schedule(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="调度不存在"
            )
        
        # 获取任务状态
        task_status = await scheduler_service.get_task_status(task_id)
        
        return {
            "schedule_id": str(schedule_id),
            "task_status": task_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.post("/performance/schedules/test")
async def test_schedule_execution(
    request: TestScheduleRequest,
    current_user: User = Depends(get_current_user)
):
    """
    测试调度执行（不实际创建调度）
    
    Args:
        request: 调度请求参数
        current_user: 当前用户
    
    Returns:
        Dict: 测试结果
    """
    try:
        from celery_tasks.tasks.performance_tasks import scheduled_performance_test
        
        # 创建测试配置
        test_config = {
            "schedule_id": "test_" + str(UUID()),
            "model_ids": [str(mid) for mid in request.model_ids],
            "test_type": request.test_type,
            "rounds": request.rounds,
            "prompt": request.prompt,
            "notify_on_completion": False,
            "notify_on_failure": False
        }
        
        # 立即执行测试
        task_result = scheduled_performance_test.delay(test_config)
        
        return {
            "test_task_id": task_result.id,
            "status": "submitted",
            "message": "调度测试已提交，请使用task_id查询结果"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"调度测试失败: {str(e)}"
        )
