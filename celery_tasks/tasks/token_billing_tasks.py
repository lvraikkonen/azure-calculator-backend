# celery_tasks/tasks/token_billing_tasks.py

import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from celery import Task
from celery.exceptions import Retry
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.model_usage_daily import ModelUsageDaily
from app.models.model_usage_hourly import ModelUsageHourly
from app.models.model_usage_log import ModelUsageLog
from app.models.model_configuration import ModelConfiguration
from app.services.model_management.model_usage_service import ModelUsageService
from app.services.token_billing.token_cost_calculator import TokenCostCalculator
from celery_tasks.celery_app import celery_app

logger = get_logger(__name__)


class TokenBillingTask(Task):
    """Token计费任务基类，提供通用的错误处理和重试机制"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(bind=True, base=TokenBillingTask, name="aggregate_token_usage_stats")
def aggregate_token_usage_stats(self, target_date: str = None) -> Dict[str, Any]:
    """
    聚合Token使用统计数据
    
    Args:
        target_date: 目标日期（YYYY-MM-DD格式），默认为昨天
        
    Returns:
        聚合结果字典
    """
    logger.info(f"开始聚合Token使用统计数据，任务ID: {self.request.id}")
    
    async def _aggregate_stats():
        async with AsyncSessionLocal() as db:
            try:
                # 解析目标日期
                if target_date:
                    target = datetime.strptime(target_date, "%Y-%m-%d").date()
                else:
                    target = date.today() - timedelta(days=1)
                
                logger.info(f"聚合日期: {target}")
                
                # 查询该日期的小时统计数据
                stmt = select(ModelUsageHourly).where(
                    and_(
                        func.date(ModelUsageHourly.hour_timestamp) == target,
                        ModelUsageHourly.request_count > 0
                    )
                )
                
                result = await db.execute(stmt)
                hourly_stats = result.scalars().all()
                
                if not hourly_stats:
                    logger.warning(f"没有找到 {target} 的小时统计数据")
                    return {"status": "no_data", "date": str(target)}
                
                # 按模型聚合数据
                model_aggregates = {}
                for hourly in hourly_stats:
                    model_id = hourly.model_id
                    if model_id not in model_aggregates:
                        model_aggregates[model_id] = {
                            'request_count': 0,
                            'success_count': 0,
                            'error_count': 0,
                            'input_tokens': 0,
                            'output_tokens': 0,
                            'total_response_time': 0,
                            'max_response_time': 0,
                            'response_time_count': 0,
                            'total_first_token_time': 0,
                            'first_token_time_count': 0,
                            'unique_users': set()
                        }
                    
                    agg = model_aggregates[model_id]
                    agg['request_count'] += hourly.request_count
                    agg['success_count'] += hourly.success_count
                    agg['error_count'] += hourly.error_count
                    agg['input_tokens'] += hourly.input_tokens
                    agg['output_tokens'] += hourly.output_tokens
                    
                    if hourly.avg_response_time:
                        agg['total_response_time'] += hourly.avg_response_time * hourly.request_count
                        agg['response_time_count'] += hourly.request_count
                        agg['max_response_time'] = max(agg['max_response_time'], 
                                                     hourly.max_response_time or 0)
                    
                    if hourly.avg_first_token_time:
                        agg['total_first_token_time'] += hourly.avg_first_token_time * hourly.request_count
                        agg['first_token_time_count'] += hourly.request_count
                
                # 更新或创建日统计记录
                updated_models = []
                for model_id, agg in model_aggregates.items():
                    # 查找现有的日统计记录
                    daily_stmt = select(ModelUsageDaily).where(
                        and_(
                            ModelUsageDaily.model_id == model_id,
                            ModelUsageDaily.usage_date == target
                        )
                    )
                    daily_result = await db.execute(daily_stmt)
                    daily_stats = daily_result.scalar_one_or_none()
                    
                    if not daily_stats:
                        daily_stats = ModelUsageDaily(
                            model_id=model_id,
                            usage_date=target
                        )
                        db.add(daily_stats)
                    
                    # 更新统计数据
                    daily_stats.request_count = agg['request_count']
                    daily_stats.success_count = agg['success_count']
                    daily_stats.error_count = agg['error_count']
                    daily_stats.input_tokens = agg['input_tokens']
                    daily_stats.output_tokens = agg['output_tokens']
                    
                    if agg['response_time_count'] > 0:
                        daily_stats.avg_response_time = agg['total_response_time'] / agg['response_time_count']
                        daily_stats.max_response_time = agg['max_response_time']
                    
                    if agg['first_token_time_count'] > 0:
                        daily_stats.avg_first_token_time = agg['total_first_token_time'] / agg['first_token_time_count']
                    
                    daily_stats.updated_at = datetime.now(timezone.utc)
                    updated_models.append(str(model_id))
                
                await db.commit()
                
                result = {
                    "status": "success",
                    "date": str(target),
                    "models_processed": len(updated_models),
                    "model_ids": updated_models,
                    "total_requests": sum(agg['request_count'] for agg in model_aggregates.values()),
                    "total_tokens": sum(agg['input_tokens'] + agg['output_tokens'] 
                                      for agg in model_aggregates.values()),
                    "aggregated_at": datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"Token使用统计聚合完成: {result}")
                return result
                
            except Exception as e:
                await db.rollback()
                logger.error(f"聚合Token使用统计失败: {str(e)}", exc_info=True)
                raise
    
    try:
        return asyncio.run(_aggregate_stats())
    except Exception as e:
        logger.error(f"聚合Token使用统计任务失败: {str(e)}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=TokenBillingTask, name="generate_usage_report")
def generate_usage_report(self, start_date: str, end_date: str, 
                         model_ids: List[str] = None) -> Dict[str, Any]:
    """
    生成使用报告
    
    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）
        model_ids: 模型ID列表，为空则包含所有模型
        
    Returns:
        报告数据字典
    """
    logger.info(f"开始生成使用报告，任务ID: {self.request.id}")
    
    async def _generate_report():
        async with AsyncSessionLocal() as db:
            try:
                usage_service = ModelUsageService(db)
                
                # 解析日期
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                
                logger.info(f"生成报告时间范围: {start} 到 {end}")
                
                # 构建查询
                stmt = select(
                    ModelUsageDaily.model_id,
                    ModelConfiguration.name.label('model_name'),
                    func.sum(ModelUsageDaily.request_count).label('total_requests'),
                    func.sum(ModelUsageDaily.success_count).label('total_success'),
                    func.sum(ModelUsageDaily.error_count).label('total_errors'),
                    func.sum(ModelUsageDaily.input_tokens).label('total_input_tokens'),
                    func.sum(ModelUsageDaily.output_tokens).label('total_output_tokens'),
                    func.avg(ModelUsageDaily.avg_response_time).label('avg_response_time'),
                    func.max(ModelUsageDaily.max_response_time).label('max_response_time')
                ).select_from(
                    ModelUsageDaily.join(ModelConfiguration)
                ).where(
                    and_(
                        ModelUsageDaily.usage_date >= start,
                        ModelUsageDaily.usage_date <= end
                    )
                ).group_by(
                    ModelUsageDaily.model_id, ModelConfiguration.name
                )
                
                # 添加模型过滤
                if model_ids:
                    model_uuids = [UUID(mid) for mid in model_ids]
                    stmt = stmt.where(ModelUsageDaily.model_id.in_(model_uuids))
                
                result = await db.execute(stmt)
                report_data = result.all()
                
                # 格式化报告数据
                models_report = []
                total_cost = 0.0
                
                for row in report_data:
                    # 获取模型价格信息
                    model_stmt = select(ModelConfiguration).where(
                        ModelConfiguration.id == row.model_id
                    )
                    model_result = await db.execute(model_stmt)
                    model = model_result.scalar_one_or_none()
                    
                    input_cost = 0.0
                    output_cost = 0.0
                    if model:
                        input_price = model.input_price or 0.0
                        output_price = model.output_price or 0.0
                        input_cost = (row.total_input_tokens * input_price) / 1_000_000
                        output_cost = (row.total_output_tokens * output_price) / 1_000_000
                    
                    model_total_cost = input_cost + output_cost
                    total_cost += model_total_cost
                    
                    success_rate = 0.0
                    if row.total_requests > 0:
                        success_rate = (row.total_success / row.total_requests) * 100
                    
                    models_report.append({
                        'model_id': str(row.model_id),
                        'model_name': row.model_name,
                        'total_requests': row.total_requests,
                        'success_rate': round(success_rate, 2),
                        'total_tokens': row.total_input_tokens + row.total_output_tokens,
                        'input_tokens': row.total_input_tokens,
                        'output_tokens': row.total_output_tokens,
                        'input_cost': round(input_cost, 6),
                        'output_cost': round(output_cost, 6),
                        'total_cost': round(model_total_cost, 6),
                        'avg_response_time': round(row.avg_response_time or 0, 2),
                        'max_response_time': round(row.max_response_time or 0, 2)
                    })
                
                # 生成汇总信息
                summary = {
                    'period': f"{start} 到 {end}",
                    'total_models': len(models_report),
                    'total_requests': sum(m['total_requests'] for m in models_report),
                    'total_tokens': sum(m['total_tokens'] for m in models_report),
                    'total_cost': round(total_cost, 6),
                    'avg_cost_per_request': round(total_cost / max(sum(m['total_requests'] for m in models_report), 1), 6)
                }
                
                report = {
                    'status': 'success',
                    'summary': summary,
                    'models': models_report,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"使用报告生成完成: {summary}")
                return report
                
            except Exception as e:
                logger.error(f"生成使用报告失败: {str(e)}", exc_info=True)
                raise
    
    try:
        return asyncio.run(_generate_report())
    except Exception as e:
        logger.error(f"生成使用报告任务失败: {str(e)}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=TokenBillingTask, name="cleanup_old_usage_logs")
def cleanup_old_usage_logs(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    清理旧的使用日志

    Args:
        days_to_keep: 保留天数，默认30天

    Returns:
        清理结果字典
    """
    logger.info(f"开始清理旧的使用日志，保留{days_to_keep}天，任务ID: {self.request.id}")

    async def _cleanup_logs():
        async with AsyncSessionLocal() as db:
            try:
                usage_service = ModelUsageService(db)

                # 执行清理
                deleted_count = await usage_service.cleanup_old_logs(days_to_keep)

                result = {
                    'status': 'success',
                    'days_kept': days_to_keep,
                    'records_deleted': deleted_count,
                    'cleaned_at': datetime.now(timezone.utc).isoformat()
                }

                logger.info(f"使用日志清理完成: 删除了 {deleted_count} 条记录")
                return result

            except Exception as e:
                logger.error(f"清理使用日志失败: {str(e)}", exc_info=True)
                raise

    try:
        return asyncio.run(_cleanup_logs())
    except Exception as e:
        logger.error(f"清理使用日志任务失败: {str(e)}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=TokenBillingTask, name="monitor_usage_anomalies")
def monitor_usage_anomalies(self, threshold_multiplier: float = 3.0) -> Dict[str, Any]:
    """
    监控使用异常

    Args:
        threshold_multiplier: 异常阈值倍数，默认3.0（超过平均值3倍视为异常）

    Returns:
        监控结果字典
    """
    logger.info(f"开始监控使用异常，阈值倍数: {threshold_multiplier}，任务ID: {self.request.id}")

    async def _monitor_anomalies():
        async with AsyncSessionLocal() as db:
            try:
                # 获取最近7天的平均使用量
                end_date = date.today()
                start_date = end_date - timedelta(days=7)

                # 计算每个模型的平均日使用量
                avg_stmt = select(
                    ModelUsageDaily.model_id,
                    ModelConfiguration.name.label('model_name'),
                    func.avg(ModelUsageDaily.request_count).label('avg_requests'),
                    func.avg(ModelUsageDaily.input_tokens + ModelUsageDaily.output_tokens).label('avg_tokens')
                ).select_from(
                    ModelUsageDaily.join(ModelConfiguration)
                ).where(
                    and_(
                        ModelUsageDaily.usage_date >= start_date,
                        ModelUsageDaily.usage_date < end_date
                    )
                ).group_by(
                    ModelUsageDaily.model_id, ModelConfiguration.name
                )

                avg_result = await db.execute(avg_stmt)
                avg_usage = {row.model_id: {
                    'model_name': row.model_name,
                    'avg_requests': row.avg_requests or 0,
                    'avg_tokens': row.avg_tokens or 0
                } for row in avg_result}

                # 检查今天的使用量
                today_stmt = select(
                    ModelUsageDaily.model_id,
                    ModelConfiguration.name.label('model_name'),
                    ModelUsageDaily.request_count,
                    (ModelUsageDaily.input_tokens + ModelUsageDaily.output_tokens).label('total_tokens')
                ).select_from(
                    ModelUsageDaily.join(ModelConfiguration)
                ).where(
                    ModelUsageDaily.usage_date == end_date
                )

                today_result = await db.execute(today_stmt)
                today_usage = today_result.all()

                # 检测异常
                anomalies = []
                for row in today_usage:
                    model_id = row.model_id
                    if model_id not in avg_usage:
                        continue

                    avg_data = avg_usage[model_id]

                    # 检查请求数异常
                    if (row.request_count > avg_data['avg_requests'] * threshold_multiplier and
                        avg_data['avg_requests'] > 0):
                        anomalies.append({
                            'type': 'high_request_count',
                            'model_id': str(model_id),
                            'model_name': row.model_name,
                            'current_value': row.request_count,
                            'average_value': round(avg_data['avg_requests'], 2),
                            'threshold': round(avg_data['avg_requests'] * threshold_multiplier, 2),
                            'severity': 'high' if row.request_count > avg_data['avg_requests'] * threshold_multiplier * 2 else 'medium'
                        })

                    # 检查Token数异常
                    if (row.total_tokens > avg_data['avg_tokens'] * threshold_multiplier and
                        avg_data['avg_tokens'] > 0):
                        anomalies.append({
                            'type': 'high_token_usage',
                            'model_id': str(model_id),
                            'model_name': row.model_name,
                            'current_value': row.total_tokens,
                            'average_value': round(avg_data['avg_tokens'], 2),
                            'threshold': round(avg_data['avg_tokens'] * threshold_multiplier, 2),
                            'severity': 'high' if row.total_tokens > avg_data['avg_tokens'] * threshold_multiplier * 2 else 'medium'
                        })

                result = {
                    'status': 'success',
                    'monitoring_date': str(end_date),
                    'threshold_multiplier': threshold_multiplier,
                    'anomalies_detected': len(anomalies),
                    'anomalies': anomalies,
                    'monitored_at': datetime.now(timezone.utc).isoformat()
                }

                if anomalies:
                    logger.warning(f"检测到 {len(anomalies)} 个使用异常")
                    for anomaly in anomalies:
                        logger.warning(f"异常: {anomaly}")
                else:
                    logger.info("未检测到使用异常")

                return result

            except Exception as e:
                logger.error(f"监控使用异常失败: {str(e)}", exc_info=True)
                raise

    try:
        return asyncio.run(_monitor_anomalies())
    except Exception as e:
        logger.error(f"监控使用异常任务失败: {str(e)}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=TokenBillingTask, name="calculate_cost_projections")
def calculate_cost_projections(self, projection_days: int = 30) -> Dict[str, Any]:
    """
    计算成本预测

    Args:
        projection_days: 预测天数，默认30天

    Returns:
        预测结果字典
    """
    logger.info(f"开始计算成本预测，预测{projection_days}天，任务ID: {self.request.id}")

    async def _calculate_projections():
        async with AsyncSessionLocal() as db:
            try:
                # 获取最近30天的使用数据用于预测
                end_date = date.today()
                start_date = end_date - timedelta(days=30)

                # 查询历史数据
                stmt = select(
                    ModelUsageDaily.model_id,
                    ModelConfiguration.name.label('model_name'),
                    ModelConfiguration.input_price,
                    ModelConfiguration.output_price,
                    func.avg(ModelUsageDaily.input_tokens).label('avg_input_tokens'),
                    func.avg(ModelUsageDaily.output_tokens).label('avg_output_tokens'),
                    func.count(ModelUsageDaily.id).label('active_days')
                ).select_from(
                    ModelUsageDaily.join(ModelConfiguration)
                ).where(
                    and_(
                        ModelUsageDaily.usage_date >= start_date,
                        ModelUsageDaily.usage_date < end_date,
                        ModelUsageDaily.request_count > 0
                    )
                ).group_by(
                    ModelUsageDaily.model_id,
                    ModelConfiguration.name,
                    ModelConfiguration.input_price,
                    ModelConfiguration.output_price
                )

                result = await db.execute(stmt)
                historical_data = result.all()

                projections = []
                total_projected_cost = 0.0

                for row in historical_data:
                    # 计算日均成本
                    input_price = row.input_price or 0.0
                    output_price = row.output_price or 0.0

                    daily_input_cost = (row.avg_input_tokens * input_price) / 1_000_000
                    daily_output_cost = (row.avg_output_tokens * output_price) / 1_000_000
                    daily_total_cost = daily_input_cost + daily_output_cost

                    # 预测总成本
                    projected_cost = daily_total_cost * projection_days
                    total_projected_cost += projected_cost

                    # 计算使用频率（活跃天数比例）
                    usage_frequency = row.active_days / 30.0

                    projections.append({
                        'model_id': str(row.model_id),
                        'model_name': row.model_name,
                        'avg_daily_input_tokens': round(row.avg_input_tokens, 2),
                        'avg_daily_output_tokens': round(row.avg_output_tokens, 2),
                        'daily_input_cost': round(daily_input_cost, 6),
                        'daily_output_cost': round(daily_output_cost, 6),
                        'daily_total_cost': round(daily_total_cost, 6),
                        'projected_cost': round(projected_cost, 6),
                        'usage_frequency': round(usage_frequency, 2),
                        'active_days_in_period': row.active_days
                    })

                # 按预测成本排序
                projections.sort(key=lambda x: x['projected_cost'], reverse=True)

                result = {
                    'status': 'success',
                    'projection_period_days': projection_days,
                    'historical_period_days': 30,
                    'total_projected_cost': round(total_projected_cost, 6),
                    'models_analyzed': len(projections),
                    'projections': projections,
                    'calculated_at': datetime.now(timezone.utc).isoformat()
                }

                logger.info(f"成本预测计算完成: 预测{projection_days}天总成本 ${total_projected_cost:.6f}")
                return result

            except Exception as e:
                logger.error(f"计算成本预测失败: {str(e)}", exc_info=True)
                raise

    try:
        return asyncio.run(_calculate_projections())
    except Exception as e:
        logger.error(f"计算成本预测任务失败: {str(e)}", exc_info=True)
        raise self.retry(exc=e)
