"""
性能测试调度管理服务
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
# from croniter import croniter

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from celery import current_app
from celery.result import AsyncResult

from app.core.logging import get_logger
from app.schemas.model_management.performance import (
    TestScheduleRequest, TestScheduleResponse
)
from celery_tasks.tasks.performance_tasks import (
    run_performance_test, run_batch_performance_test, scheduled_performance_test
)

logger = get_logger(__name__)


class PerformanceSchedulerService:
    """性能测试调度服务"""
    
    def __init__(self, db: AsyncSession):
        """初始化调度服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self._active_schedules: Dict[str, Dict[str, Any]] = {}
    
    async def create_schedule(
        self, 
        request: TestScheduleRequest,
        created_by: Optional[uuid.UUID] = None
    ) -> TestScheduleResponse:
        """创建测试调度
        
        Args:
            request: 调度请求
            created_by: 创建人ID
            
        Returns:
            TestScheduleResponse: 调度响应
        """
        schedule_id = uuid.uuid4()
        
        try:
            # 计算下次运行时间
            next_run_time = self._calculate_next_run_time(
                request.schedule_type,
                request.schedule_time,
                request.cron_expression
            )
            
            # 创建调度配置
            schedule_config = {
                "schedule_id": str(schedule_id),
                "model_ids": [str(mid) for mid in request.model_ids],
                "test_type": request.test_type,
                "rounds": request.rounds,
                "prompt": request.prompt,
                "schedule_type": request.schedule_type,
                "schedule_time": request.schedule_time.isoformat() if request.schedule_time else None,
                "cron_expression": request.cron_expression,
                "timezone": request.timezone,
                "notify_on_completion": request.notify_on_completion,
                "notify_on_failure": request.notify_on_failure,
                "notification_emails": request.notification_emails,
                "created_by": str(created_by) if created_by else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            }
            
            # 根据调度类型安排任务
            if request.schedule_type == "once":
                # 一次性任务
                task_result = scheduled_performance_test.apply_async(
                    args=[schedule_config],
                    eta=next_run_time
                )
                schedule_config["celery_task_id"] = task_result.id
                
            elif request.schedule_type in ["daily", "weekly", "monthly"]:
                # 周期性任务
                task_result = self._schedule_periodic_task(schedule_config, next_run_time)
                schedule_config["celery_task_id"] = task_result.id if task_result else None
                
            elif request.schedule_type == "cron":
                # Cron表达式任务
                if not request.cron_expression:
                    raise ValueError("Cron调度类型需要提供cron_expression")
                task_result = self._schedule_cron_task(schedule_config, next_run_time)
                schedule_config["celery_task_id"] = task_result.id if task_result else None
            
            # 保存调度配置到内存（实际项目中应该保存到数据库）
            self._active_schedules[str(schedule_id)] = schedule_config
            
            logger.info(f"创建性能测试调度成功: {schedule_id}")
            
            return TestScheduleResponse(
                schedule_id=schedule_id,
                model_ids=request.model_ids,
                test_type=request.test_type,
                schedule_type=request.schedule_type,
                next_run_time=next_run_time,
                status="active",
                created_at=datetime.now(timezone.utc),
                created_by=created_by
            )
            
        except Exception as e:
            logger.error(f"创建调度失败: {str(e)}", exc_info=True)
            raise
    
    def _calculate_next_run_time(
        self,
        schedule_type: str,
        schedule_time: Optional[datetime],
        cron_expression: Optional[str]
    ) -> datetime:
        """计算下次运行时间
        
        Args:
            schedule_type: 调度类型
            schedule_time: 调度时间
            cron_expression: Cron表达式
            
        Returns:
            datetime: 下次运行时间
        """
        now = datetime.now(timezone.utc)
        
        if schedule_type == "once":
            return schedule_time or now + timedelta(minutes=1)
            
        elif schedule_type == "daily":
            if schedule_time:
                # 使用指定时间
                next_run = schedule_time.replace(tzinfo=timezone.utc)
                if next_run <= now:
                    next_run += timedelta(days=1)
            else:
                # 默认1小时后开始，然后每天执行
                next_run = now + timedelta(hours=1)
            return next_run
            
        elif schedule_type == "weekly":
            if schedule_time:
                next_run = schedule_time.replace(tzinfo=timezone.utc)
                if next_run <= now:
                    next_run += timedelta(weeks=1)
            else:
                next_run = now + timedelta(hours=1)
            return next_run
            
        elif schedule_type == "monthly":
            if schedule_time:
                next_run = schedule_time.replace(tzinfo=timezone.utc)
                if next_run <= now:
                    # 简单的月份增加逻辑
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)
            else:
                next_run = now + timedelta(hours=1)
            return next_run
            
        # elif schedule_type == "cron":
        #     if not cron_expression:
        #         raise ValueError("Cron调度需要提供cron_expression")
            
        #     try:
        #         cron = croniter(cron_expression, now)
        #         return cron.get_next(datetime)
        #     except Exception as e:
        #         raise ValueError(f"无效的Cron表达式: {cron_expression}, 错误: {str(e)}")
        
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")
    
    def _schedule_periodic_task(
        self, 
        schedule_config: Dict[str, Any], 
        next_run_time: datetime
    ) -> Optional[AsyncResult]:
        """安排周期性任务
        
        Args:
            schedule_config: 调度配置
            next_run_time: 下次运行时间
            
        Returns:
            Optional[AsyncResult]: Celery任务结果
        """
        try:
            # 对于周期性任务，我们先安排第一次执行
            # 实际的周期性逻辑需要在任务完成后重新安排下一次执行
            task_result = scheduled_performance_test.apply_async(
                args=[schedule_config],
                eta=next_run_time
            )
            
            logger.info(f"安排周期性任务: {task_result.id}, 下次执行: {next_run_time}")
            return task_result
            
        except Exception as e:
            logger.error(f"安排周期性任务失败: {str(e)}", exc_info=True)
            return None
    
    def _schedule_cron_task(
        self, 
        schedule_config: Dict[str, Any], 
        next_run_time: datetime
    ) -> Optional[AsyncResult]:
        """安排Cron任务
        
        Args:
            schedule_config: 调度配置
            next_run_time: 下次运行时间
            
        Returns:
            Optional[AsyncResult]: Celery任务结果
        """
        try:
            task_result = scheduled_performance_test.apply_async(
                args=[schedule_config],
                eta=next_run_time
            )
            
            logger.info(f"安排Cron任务: {task_result.id}, 下次执行: {next_run_time}")
            return task_result
            
        except Exception as e:
            logger.error(f"安排Cron任务失败: {str(e)}", exc_info=True)
            return None
    
    async def get_schedule(self, schedule_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """获取调度信息
        
        Args:
            schedule_id: 调度ID
            
        Returns:
            Optional[Dict[str, Any]]: 调度信息
        """
        return self._active_schedules.get(str(schedule_id))
    
    async def list_schedules(
        self, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取调度列表
        
        Args:
            status: 状态筛选
            limit: 分页限制
            offset: 分页偏移
            
        Returns:
            List[Dict[str, Any]]: 调度列表
        """
        schedules = list(self._active_schedules.values())
        
        # 状态筛选
        if status:
            schedules = [s for s in schedules if s.get("status") == status]
        
        # 分页
        return schedules[offset:offset + limit]
    
    async def pause_schedule(self, schedule_id: uuid.UUID) -> bool:
        """暂停调度
        
        Args:
            schedule_id: 调度ID
            
        Returns:
            bool: 是否成功
        """
        schedule_key = str(schedule_id)
        if schedule_key not in self._active_schedules:
            return False
        
        schedule = self._active_schedules[schedule_key]
        
        # 取消Celery任务
        celery_task_id = schedule.get("celery_task_id")
        if celery_task_id:
            current_app.control.revoke(celery_task_id, terminate=True)
        
        # 更新状态
        schedule["status"] = "paused"
        schedule["paused_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"暂停调度: {schedule_id}")
        return True
    
    async def resume_schedule(self, schedule_id: uuid.UUID) -> bool:
        """恢复调度
        
        Args:
            schedule_id: 调度ID
            
        Returns:
            bool: 是否成功
        """
        schedule_key = str(schedule_id)
        if schedule_key not in self._active_schedules:
            return False
        
        schedule = self._active_schedules[schedule_key]
        
        if schedule.get("status") != "paused":
            return False
        
        try:
            # 重新计算下次运行时间
            next_run_time = self._calculate_next_run_time(
                schedule["schedule_type"],
                datetime.fromisoformat(schedule["schedule_time"]) if schedule.get("schedule_time") else None,
                schedule.get("cron_expression")
            )
            
            # 重新安排任务
            task_result = scheduled_performance_test.apply_async(
                args=[schedule],
                eta=next_run_time
            )
            
            # 更新调度信息
            schedule["celery_task_id"] = task_result.id
            schedule["status"] = "active"
            schedule["resumed_at"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"恢复调度: {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复调度失败: {str(e)}", exc_info=True)
            return False
    
    async def delete_schedule(self, schedule_id: uuid.UUID) -> bool:
        """删除调度
        
        Args:
            schedule_id: 调度ID
            
        Returns:
            bool: 是否成功
        """
        schedule_key = str(schedule_id)
        if schedule_key not in self._active_schedules:
            return False
        
        schedule = self._active_schedules[schedule_key]
        
        # 取消Celery任务
        celery_task_id = schedule.get("celery_task_id")
        if celery_task_id:
            current_app.control.revoke(celery_task_id, terminate=True)
        
        # 删除调度
        del self._active_schedules[schedule_key]
        
        logger.info(f"删除调度: {schedule_id}")
        return True
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        try:
            result = AsyncResult(task_id)
            
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result,
                "traceback": result.traceback,
                "date_done": result.date_done.isoformat() if result.date_done else None
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "error": str(e)
            }
