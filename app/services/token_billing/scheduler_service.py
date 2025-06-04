# app/services/token_billing/scheduler_service.py

import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.token_billing.monitoring import TokenUsageMonitor, LogAlertHandler
from celery_tasks.celery_app import get_celery_app
from celery_tasks.tasks.token_billing_tasks import (
    aggregate_token_usage_stats,
    generate_usage_report,
    cleanup_old_usage_logs,
    monitor_usage_anomalies,
    calculate_cost_projections
)

logger = get_logger(__name__)


class ScheduleType(Enum):
    """调度类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    HOURLY = "hourly"
    CUSTOM = "custom"


class TokenBillingScheduler:
    """Token计费调度服务"""
    
    def __init__(self, db: AsyncSession = None):
        """
        初始化调度服务
        
        Args:
            db: 数据库会话（可选）
        """
        self.db = db
        self.logger = logger
        self.celery_app = get_celery_app()
        
        # 调度任务配置
        self.scheduled_tasks = {
            'daily_aggregation': {
                'task': 'aggregate_token_usage_stats',
                'schedule': 'daily',
                'time': '01:00',  # 每天凌晨1点
                'enabled': True
            },
            'daily_monitoring': {
                'task': 'monitor_usage_anomalies',
                'schedule': 'daily',
                'time': '09:00',  # 每天上午9点
                'enabled': True
            },
            'weekly_cleanup': {
                'task': 'cleanup_old_usage_logs',
                'schedule': 'weekly',
                'day': 'sunday',
                'time': '02:00',  # 每周日凌晨2点
                'enabled': True
            },
            'monthly_report': {
                'task': 'generate_usage_report',
                'schedule': 'monthly',
                'day': 1,
                'time': '08:00',  # 每月1号上午8点
                'enabled': True
            },
            'daily_projections': {
                'task': 'calculate_cost_projections',
                'schedule': 'daily',
                'time': '10:00',  # 每天上午10点
                'enabled': True
            }
        }
    
    async def schedule_daily_aggregation(self, target_date: str = None) -> str:
        """
        调度日统计聚合任务
        
        Args:
            target_date: 目标日期（YYYY-MM-DD格式），默认为昨天
            
        Returns:
            str: 任务ID
        """
        try:
            task = aggregate_token_usage_stats.delay(target_date)
            self.logger.info(f"已调度日统计聚合任务: {task.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"调度日统计聚合任务失败: {str(e)}", exc_info=True)
            raise
    
    async def schedule_usage_monitoring(self, threshold_multiplier: float = 3.0) -> str:
        """
        调度使用量监控任务
        
        Args:
            threshold_multiplier: 异常阈值倍数
            
        Returns:
            str: 任务ID
        """
        try:
            task = monitor_usage_anomalies.delay(threshold_multiplier)
            self.logger.info(f"已调度使用量监控任务: {task.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"调度使用量监控任务失败: {str(e)}", exc_info=True)
            raise
    
    async def schedule_usage_report(self, start_date: str, end_date: str, 
                                  model_ids: List[str] = None) -> str:
        """
        调度使用报告生成任务
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            model_ids: 模型ID列表
            
        Returns:
            str: 任务ID
        """
        try:
            task = generate_usage_report.delay(start_date, end_date, model_ids)
            self.logger.info(f"已调度使用报告生成任务: {task.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"调度使用报告生成任务失败: {str(e)}", exc_info=True)
            raise
    
    async def schedule_cleanup(self, days_to_keep: int = 30) -> str:
        """
        调度清理任务
        
        Args:
            days_to_keep: 保留天数
            
        Returns:
            str: 任务ID
        """
        try:
            task = cleanup_old_usage_logs.delay(days_to_keep)
            self.logger.info(f"已调度清理任务: {task.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"调度清理任务失败: {str(e)}", exc_info=True)
            raise
    
    async def schedule_cost_projections(self, projection_days: int = 30) -> str:
        """
        调度成本预测任务
        
        Args:
            projection_days: 预测天数
            
        Returns:
            str: 任务ID
        """
        try:
            task = calculate_cost_projections.delay(projection_days)
            self.logger.info(f"已调度成本预测任务: {task.id}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"调度成本预测任务失败: {str(e)}", exc_info=True)
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            status_info = {
                'task_id': task_id,
                'status': result.status,
                'ready': result.ready(),
                'successful': result.successful() if result.ready() else None,
                'failed': result.failed() if result.ready() else None,
                'result': None,
                'error': None
            }
            
            if result.ready():
                if result.successful():
                    status_info['result'] = result.result
                elif result.failed():
                    status_info['error'] = str(result.info)
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
            return {
                'task_id': task_id,
                'status': 'UNKNOWN',
                'error': str(e)
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否取消成功
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            result.revoke(terminate=True)
            self.logger.info(f"已取消任务: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"取消任务失败: {str(e)}", exc_info=True)
            return False
    
    async def run_daily_maintenance(self) -> Dict[str, Any]:
        """
        运行日常维护任务
        
        Returns:
            Dict[str, Any]: 维护结果
        """
        maintenance_results = {}
        
        try:
            # 1. 聚合昨天的统计数据
            yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            aggregation_task_id = await self.schedule_daily_aggregation(yesterday)
            maintenance_results['aggregation_task'] = aggregation_task_id
            
            # 2. 监控使用异常
            monitoring_task_id = await self.schedule_usage_monitoring()
            maintenance_results['monitoring_task'] = monitoring_task_id
            
            # 3. 计算成本预测
            projection_task_id = await self.schedule_cost_projections()
            maintenance_results['projection_task'] = projection_task_id
            
            # 4. 如果是周日，执行清理任务
            if date.today().weekday() == 6:  # 周日
                cleanup_task_id = await self.schedule_cleanup()
                maintenance_results['cleanup_task'] = cleanup_task_id
            
            # 5. 如果是月初，生成月度报告
            if date.today().day == 1:
                last_month_end = date.today() - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                
                report_task_id = await self.schedule_usage_report(
                    start_date=last_month_start.strftime("%Y-%m-%d"),
                    end_date=last_month_end.strftime("%Y-%m-%d")
                )
                maintenance_results['monthly_report_task'] = report_task_id
            
            maintenance_results['status'] = 'success'
            maintenance_results['scheduled_at'] = datetime.now(timezone.utc).isoformat()
            
            self.logger.info(f"日常维护任务调度完成: {maintenance_results}")
            return maintenance_results
            
        except Exception as e:
            self.logger.error(f"日常维护任务调度失败: {str(e)}", exc_info=True)
            maintenance_results['status'] = 'error'
            maintenance_results['error'] = str(e)
            return maintenance_results
    
    async def setup_monitoring_alerts(self) -> TokenUsageMonitor:
        """
        设置监控告警
        
        Returns:
            TokenUsageMonitor: 配置好的监控器
        """
        if not self.db:
            raise ValueError("需要数据库会话才能设置监控")
        
        # 创建监控器
        monitor = TokenUsageMonitor(self.db)
        
        # 添加日志告警处理器
        log_handler = LogAlertHandler()
        monitor.add_alert_handler(log_handler)
        
        # 可以根据需要添加其他告警处理器
        # email_handler = EmailAlertHandler(email_config)
        # monitor.add_alert_handler(email_handler)
        
        self.logger.info("监控告警系统已设置")
        return monitor
    
    def get_scheduled_tasks_info(self) -> Dict[str, Any]:
        """
        获取调度任务信息
        
        Returns:
            Dict[str, Any]: 调度任务配置信息
        """
        return {
            'scheduled_tasks': self.scheduled_tasks,
            'celery_app_name': self.celery_app.main,
            'total_tasks': len(self.scheduled_tasks),
            'enabled_tasks': len([t for t in self.scheduled_tasks.values() if t.get('enabled', False)])
        }


# 全局调度器实例
_global_scheduler: Optional[TokenBillingScheduler] = None


def get_global_scheduler() -> TokenBillingScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TokenBillingScheduler()
    return _global_scheduler


def set_global_scheduler(scheduler: TokenBillingScheduler):
    """设置全局调度器实例"""
    global _global_scheduler
    _global_scheduler = scheduler
