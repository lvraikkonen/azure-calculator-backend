"""
清理相关的Celery任务
"""

import uuid
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from celery import current_task
from sqlalchemy import select, delete, func

from celery_tasks.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.model_management.factory import create_service
from app.models.model_configuration import ModelConfiguration
from app.models.model_price_history import ModelPriceHistory
from app.models.model_audit_log import ModelAuditLog

logger = get_logger(__name__)


@celery_app.task(bind=True)
def cleanup_model_data(self, model_id: str) -> Dict[str, Any]:
    """
    清理已删除模型的相关数据
    
    Args:
        model_id: 模型ID字符串
        
    Returns:
        清理结果字典
    """
    logger.info(f"开始清理模型数据: {model_id}")
    
    # 更新任务状态
    self.update_state(
        state='PROGRESS',
        meta={
            'status': 'initializing',
            'progress': 10,
            'model_id': model_id
        }
    )
    
    async def _cleanup_data():
        """异步清理数据的内部函数"""
        try:
            # 获取数据库会话
            async with AsyncSessionLocal() as db:
                model_uuid = uuid.UUID(model_id)
                cleanup_results = {}
                
                # 更新进度
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'cleaning_price_history',
                        'progress': 30,
                        'model_id': model_id
                    }
                )
                
                # 清理价格历史记录
                price_history_result = await db.execute(
                    delete(ModelPriceHistory).where(ModelPriceHistory.model_id == model_uuid)
                )
                cleanup_results['price_history_deleted'] = price_history_result.rowcount
                
                # 更新进度
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'cleaning_audit_logs',
                        'progress': 60,
                        'model_id': model_id
                    }
                )
                
                # 清理审计日志（保留最近30天的记录）
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
                audit_log_result = await db.execute(
                    delete(ModelAuditLog).where(
                        ModelAuditLog.model_id == model_uuid,
                        ModelAuditLog.action_date < cutoff_date
                    )
                )
                cleanup_results['audit_logs_deleted'] = audit_log_result.rowcount
                
                # 更新进度
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'cleaning_performance_data',
                        'progress': 80,
                        'model_id': model_id
                    }
                )
                
                # 清理性能测试数据（如果存在相关表）
                # 这里可以添加清理性能测试记录的逻辑
                # 例如：清理 model_performance_tests 表中的相关记录
                cleanup_results['performance_tests_deleted'] = 0  # 占位符
                
                # 提交事务
                await db.commit()
                
                return {
                    'model_id': model_id,
                    'cleanup_results': cleanup_results,
                    'total_records_deleted': sum(cleanup_results.values()),
                    'cleaned_at': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"清理模型数据失败: {str(e)}", exc_info=True)
            raise
    
    try:
        # 执行异步清理
        result = asyncio.run(_cleanup_data())
        
        # 更新任务状态为完成
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'completed',
                'progress': 100,
                'result': result
            }
        )
        
        logger.info(f"模型数据清理完成: {model_id}, 删除记录数: {result['total_records_deleted']}")
        return result
        
    except Exception as e:
        logger.error(f"清理模型数据任务失败: {str(e)}", exc_info=True)
        
        # 更新任务状态为失败
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e),
                'progress': 0,
                'model_id': model_id
            }
        )
        
        return {"status": "error", "message": str(e), "model_id": model_id}


@celery_app.task(bind=True)
def cleanup_expired_cache(self) -> Dict[str, Any]:
    """
    清理过期的缓存数据
    
    Returns:
        清理结果字典
    """
    logger.info("开始清理过期缓存")
    
    try:
        # 获取全局工厂实例并清理缓存
        from app.services.model_management.factory import get_factory
        
        factory = get_factory()
        cache_manager = factory.get_cache_manager()
        
        # 获取清理前的统计
        before_stats = cache_manager.get_stats()
        
        # 清理过期缓存（通过重新创建缓存管理器实现）
        factory.reset()
        
        # 获取清理后的统计
        new_cache_manager = factory.get_cache_manager()
        after_stats = new_cache_manager.get_stats()
        
        result = {
            'before_cache_size': before_stats['size'],
            'after_cache_size': after_stats['size'],
            'cleared_entries': before_stats['size'] - after_stats['size'],
            'cleaned_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"缓存清理完成: 清理了 {result['cleared_entries']} 个条目")
        return result
        
    except Exception as e:
        logger.error(f"清理缓存任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def cleanup_old_audit_logs(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """
    清理旧的审计日志
    
    Args:
        days_to_keep: 保留的天数，默认90天
        
    Returns:
        清理结果字典
    """
    logger.info(f"开始清理 {days_to_keep} 天前的审计日志")
    
    async def _cleanup_logs():
        """异步清理日志的内部函数"""
        try:
            # 获取数据库会话
            async with AsyncSessionLocal() as db:
                # 计算截止日期
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
                
                # 统计要删除的记录数
                count_result = await db.execute(
                    select(func.count()).select_from(ModelAuditLog)
                    .where(ModelAuditLog.action_date < cutoff_date)
                )
                records_to_delete = count_result.scalar_one()
                
                # 删除旧记录
                delete_result = await db.execute(
                    delete(ModelAuditLog).where(ModelAuditLog.action_date < cutoff_date)
                )
                
                # 提交事务
                await db.commit()
                
                return {
                    'cutoff_date': cutoff_date.isoformat(),
                    'records_deleted': delete_result.rowcount,
                    'days_kept': days_to_keep,
                    'cleaned_at': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"清理审计日志失败: {str(e)}", exc_info=True)
            raise
    
    try:
        # 执行异步清理
        result = asyncio.run(_cleanup_logs())
        
        logger.info(f"审计日志清理完成: 删除了 {result['records_deleted']} 条记录")
        return result
        
    except Exception as e:
        logger.error(f"清理审计日志任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def cleanup_orphaned_price_history(self) -> Dict[str, Any]:
    """
    清理孤立的价格历史记录（对应的模型已被删除）
    
    Returns:
        清理结果字典
    """
    logger.info("开始清理孤立的价格历史记录")
    
    async def _cleanup_orphaned():
        """异步清理孤立记录的内部函数"""
        try:
            # 获取数据库会话
            async with AsyncSessionLocal() as db:
                # 查找孤立的价格历史记录
                orphaned_query = select(ModelPriceHistory.model_id).distinct().where(
                    ~ModelPriceHistory.model_id.in_(
                        select(ModelConfiguration.id)
                    )
                )
                
                orphaned_result = await db.execute(orphaned_query)
                orphaned_model_ids = [row[0] for row in orphaned_result.fetchall()]
                
                if not orphaned_model_ids:
                    return {
                        'orphaned_models_found': 0,
                        'records_deleted': 0,
                        'cleaned_at': datetime.now(timezone.utc).isoformat()
                    }
                
                # 删除孤立的价格历史记录
                delete_result = await db.execute(
                    delete(ModelPriceHistory).where(
                        ModelPriceHistory.model_id.in_(orphaned_model_ids)
                    )
                )
                
                # 提交事务
                await db.commit()
                
                return {
                    'orphaned_models_found': len(orphaned_model_ids),
                    'orphaned_model_ids': [str(mid) for mid in orphaned_model_ids],
                    'records_deleted': delete_result.rowcount,
                    'cleaned_at': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"清理孤立价格历史记录失败: {str(e)}", exc_info=True)
            raise
    
    try:
        # 执行异步清理
        result = asyncio.run(_cleanup_orphaned())
        
        logger.info(f"孤立价格历史记录清理完成: 删除了 {result['records_deleted']} 条记录")
        return result
        
    except Exception as e:
        logger.error(f"清理孤立价格历史记录任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True)
def daily_maintenance_cleanup(self) -> Dict[str, Any]:
    """
    每日维护清理任务
    
    Returns:
        清理结果字典
    """
    logger.info("开始每日维护清理")
    
    try:
        results = {}
        
        # 清理过期缓存
        cache_result = cleanup_expired_cache.delay()
        results['cache_cleanup'] = cache_result.get(timeout=300)
        
        # 清理旧审计日志（保留90天）
        audit_result = cleanup_old_audit_logs.delay(90)
        results['audit_cleanup'] = audit_result.get(timeout=300)
        
        # 清理孤立的价格历史记录
        orphaned_result = cleanup_orphaned_price_history.delay()
        results['orphaned_cleanup'] = orphaned_result.get(timeout=300)
        
        # 汇总结果
        total_deleted = 0
        for cleanup_type, cleanup_result in results.items():
            if isinstance(cleanup_result, dict):
                total_deleted += cleanup_result.get('records_deleted', 0)
                total_deleted += cleanup_result.get('cleared_entries', 0)
        
        summary = {
            'maintenance_type': 'daily',
            'cleanup_results': results,
            'total_records_processed': total_deleted,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"每日维护清理完成: 处理了 {total_deleted} 条记录")
        return summary
        
    except Exception as e:
        logger.error(f"每日维护清理任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
