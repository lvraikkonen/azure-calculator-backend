# app/api/v1/endpoints/token_billing.py

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.services.token_billing.analytics_service import TokenUsageAnalytics
from app.services.token_billing.report_generator import (
    CustomReportGenerator, ReportConfig, ReportType, ReportFormat
)
from app.services.token_billing.monitoring import TokenUsageMonitor, LogAlertHandler
from app.services.token_billing.scheduler_service import TokenBillingScheduler
from app.services.token_billing.plugin_system import get_plugin_manager
from app.schemas.token_billing import *
from celery_tasks.tasks.token_billing_tasks import (
    aggregate_token_usage_stats,
    generate_usage_report,
    monitor_usage_anomalies,
    calculate_cost_projections
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/analytics/trends", response_model=TrendAnalysisResponse)
async def get_usage_trends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_id: Optional[UUID] = Query(None, description="模型ID，为空则分析所有模型"),
    days: int = Query(30, ge=7, le=365, description="分析天数")
):
    """获取使用趋势分析"""
    try:
        analytics = TokenUsageAnalytics(db)
        trends = await analytics.analyze_usage_trends(model_id, days)
        
        return TrendAnalysisResponse(
            model_id=str(model_id) if model_id else None,
            analysis_period=days,
            trends=trends,
            generated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"获取使用趋势失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取使用趋势失败")


@router.get("/analytics/patterns", response_model=UsagePatternResponse)
async def get_usage_patterns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_id: Optional[UUID] = Query(None, description="模型ID"),
    days: int = Query(30, ge=7, le=365, description="分析天数")
):
    """获取使用模式分析"""
    try:
        analytics = TokenUsageAnalytics(db)
        pattern = await analytics.analyze_usage_patterns(model_id, days)
        
        return UsagePatternResponse(
            model_id=str(model_id) if model_id else None,
            analysis_period=days,
            pattern=pattern,
            generated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"获取使用模式失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取使用模式失败")


@router.get("/analytics/forecast", response_model=CostForecastResponse)
async def get_cost_forecast(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    model_id: Optional[UUID] = Query(None, description="模型ID"),
    forecast_days: int = Query(30, ge=1, le=365, description="预测天数")
):
    """获取成本预测"""
    try:
        analytics = TokenUsageAnalytics(db)
        forecast = await analytics.forecast_costs(model_id, forecast_days)
        
        return CostForecastResponse(
            model_id=str(model_id) if model_id else None,
            forecast=forecast,
            generated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"获取成本预测失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取成本预测失败")


@router.post("/reports/generate", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成自定义报告"""
    try:
        generator = CustomReportGenerator(db)
        
        # 创建报告配置
        config = ReportConfig(
            report_type=ReportType(request.report_type),
            format=ReportFormat(request.format),
            start_date=request.start_date,
            end_date=request.end_date,
            model_ids=request.model_ids,
            include_trends=request.include_trends,
            include_predictions=request.include_predictions,
            include_recommendations=request.include_recommendations,
            group_by=request.group_by,
            filters=request.filters,
            custom_fields=request.custom_fields
        )
        
        # 生成报告
        report = await generator.generate_report(config)
        
        return ReportGenerationResponse(
            report_id=report['metadata']['report_id'],
            status="completed",
            download_url=f"/api/v1/token-billing/reports/{report['metadata']['report_id']}/download",
            metadata=report['metadata'],
            generated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="生成报告失败")


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载报告"""
    try:
        # 这里应该从存储中获取报告
        # 简化实现，直接返回错误
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
        
    except Exception as e:
        logger.error(f"下载报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="下载报告失败")


@router.post("/monitoring/check", response_model=MonitoringCheckResponse)
async def run_monitoring_check(
    request: MonitoringCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行监控检查"""
    try:
        monitor = TokenUsageMonitor(db)
        
        # 添加日志处理器
        log_handler = LogAlertHandler()
        monitor.add_alert_handler(log_handler)
        
        # 运行检查
        alerts = await monitor.run_all_checks(request.target_date)
        
        return MonitoringCheckResponse(
            target_date=request.target_date,
            alerts_found=sum(len(alert_list) for alert_list in alerts.values()),
            alerts_by_type=alerts,
            checked_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"运行监控检查失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="运行监控检查失败")


@router.post("/tasks/aggregate", response_model=TaskResponse)
async def schedule_aggregation_task(
    request: AggregationTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """调度统计聚合任务"""
    try:
        task = aggregate_token_usage_stats.delay(request.target_date)
        
        return TaskResponse(
            task_id=task.id,
            task_type="aggregate_token_usage_stats",
            status="pending",
            scheduled_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"调度聚合任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="调度聚合任务失败")


@router.post("/tasks/monitor", response_model=TaskResponse)
async def schedule_monitoring_task(
    request: MonitoringTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """调度监控任务"""
    try:
        task = monitor_usage_anomalies.delay(request.threshold_multiplier)
        
        return TaskResponse(
            task_id=task.id,
            task_type="monitor_usage_anomalies",
            status="pending",
            scheduled_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"调度监控任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="调度监控任务失败")


@router.post("/tasks/forecast", response_model=TaskResponse)
async def schedule_forecast_task(
    request: ForecastTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """调度成本预测任务"""
    try:
        task = calculate_cost_projections.delay(request.projection_days)
        
        return TaskResponse(
            task_id=task.id,
            task_type="calculate_cost_projections",
            status="pending",
            scheduled_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"调度预测任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="调度预测任务失败")


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取任务状态"""
    try:
        scheduler = TokenBillingScheduler()
        status_info = await scheduler.get_task_status(task_id)
        
        return TaskStatusResponse(
            task_id=task_id,
            status=status_info['status'],
            result=status_info.get('result'),
            error=status_info.get('error'),
            checked_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取任务状态失败")


@router.delete("/tasks/{task_id}", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """取消任务"""
    try:
        scheduler = TokenBillingScheduler()
        success = await scheduler.cancel_task(task_id)
        
        return TaskCancelResponse(
            task_id=task_id,
            cancelled=success,
            cancelled_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins(
    current_user: User = Depends(get_current_user)
):
    """列出所有插件"""
    try:
        plugin_manager = get_plugin_manager()
        plugins = plugin_manager.list_plugins()
        
        plugin_list = []
        for name, info in plugins.items():
            plugin_list.append({
                'name': name,
                'version': info.metadata.version,
                'description': info.metadata.description,
                'type': info.metadata.plugin_type.value,
                'status': info.status.value,
                'loaded_at': info.loaded_at.isoformat() if info.loaded_at else None
            })
        
        return PluginListResponse(
            plugins=plugin_list,
            total_count=len(plugin_list)
        )
        
    except Exception as e:
        logger.error(f"列出插件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="列出插件失败")


@router.post("/export", response_model=DataExportResponse)
async def export_data(
    request: DataExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出数据"""
    try:
        # 根据导出类型获取数据
        if request.export_type == "usage_summary":
            generator = CustomReportGenerator(db)
            config = ReportConfig(
                report_type=ReportType.USAGE_SUMMARY,
                format=ReportFormat(request.format),
                start_date=request.start_date,
                end_date=request.end_date,
                model_ids=request.model_ids
            )
            report = await generator.generate_report(config)
            data = report['data']
        else:
            raise HTTPException(status_code=400, detail="不支持的导出类型")
        
        # 使用插件导出
        plugin_manager = get_plugin_manager()
        export_results = await plugin_manager.export_data_with_plugins(data, request.format)
        
        return DataExportResponse(
            export_id=f"export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            format=request.format,
            data_size=len(str(data)),
            export_results=export_results,
            exported_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="导出数据失败")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """健康检查"""
    try:
        # 检查数据库连接
        await db.execute("SELECT 1")
        
        # 检查插件状态
        plugin_manager = get_plugin_manager()
        plugins = plugin_manager.list_plugins()
        active_plugins = sum(1 for p in plugins.values() if p.status.value == "active")
        
        return HealthCheckResponse(
            status="healthy",
            database_connected=True,
            active_plugins=active_plugins,
            total_plugins=len(plugins),
            checked_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return HealthCheckResponse(
            status="unhealthy",
            database_connected=False,
            active_plugins=0,
            total_plugins=0,
            checked_at=datetime.now(timezone.utc),
            error=str(e)
        )
