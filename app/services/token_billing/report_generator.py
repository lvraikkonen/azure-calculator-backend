# app/services/token_billing/report_generator.py

import asyncio
import json
import csv
import io
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, BinaryIO
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import UUID
import base64

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_usage_daily import ModelUsageDaily
from app.models.model_usage_hourly import ModelUsageHourly
from app.models.model_configuration import ModelConfiguration
from app.services.token_billing.analytics_service import TokenUsageAnalytics

logger = get_logger(__name__)


class ReportFormat(Enum):
    """报告格式"""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"


class ReportType(Enum):
    """报告类型"""
    USAGE_SUMMARY = "usage_summary"
    COST_ANALYSIS = "cost_analysis"
    TREND_ANALYSIS = "trend_analysis"
    MODEL_COMPARISON = "model_comparison"
    PERFORMANCE_REPORT = "performance_report"
    CUSTOM = "custom"


@dataclass
class ReportConfig:
    """报告配置"""
    report_type: ReportType
    format: ReportFormat
    start_date: date
    end_date: date
    model_ids: Optional[List[UUID]] = None
    include_trends: bool = True
    include_predictions: bool = False
    include_recommendations: bool = True
    group_by: Optional[str] = None  # 'model', 'date', 'hour'
    filters: Optional[Dict[str, Any]] = None
    custom_fields: Optional[List[str]] = None


@dataclass
class ReportMetadata:
    """报告元数据"""
    report_id: str
    title: str
    description: str
    generated_at: datetime
    generated_by: Optional[str] = None
    config: Optional[ReportConfig] = None
    data_range: Optional[Dict[str, Any]] = None
    total_records: int = 0


class CustomReportGenerator:
    """自定义报告生成器"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化报告生成器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger
        self.analytics = TokenUsageAnalytics(db)
    
    async def generate_report(self, config: ReportConfig, 
                            report_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成报告
        
        Args:
            config: 报告配置
            report_id: 报告ID
            
        Returns:
            Dict[str, Any]: 报告数据
        """
        try:
            # 生成报告ID
            if not report_id:
                report_id = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            # 根据报告类型生成数据
            if config.report_type == ReportType.USAGE_SUMMARY:
                data = await self._generate_usage_summary(config)
            elif config.report_type == ReportType.COST_ANALYSIS:
                data = await self._generate_cost_analysis(config)
            elif config.report_type == ReportType.TREND_ANALYSIS:
                data = await self._generate_trend_analysis(config)
            elif config.report_type == ReportType.MODEL_COMPARISON:
                data = await self._generate_model_comparison(config)
            elif config.report_type == ReportType.PERFORMANCE_REPORT:
                data = await self._generate_performance_report(config)
            else:
                data = await self._generate_custom_report(config)
            
            # 创建报告元数据
            metadata = ReportMetadata(
                report_id=report_id,
                title=self._get_report_title(config),
                description=self._get_report_description(config),
                generated_at=datetime.now(timezone.utc),
                config=config,
                data_range={
                    'start_date': config.start_date.isoformat(),
                    'end_date': config.end_date.isoformat(),
                    'days': (config.end_date - config.start_date).days + 1
                },
                total_records=len(data.get('records', []))
            )
            
            # 构建完整报告
            report = {
                'metadata': asdict(metadata),
                'data': data,
                'format': config.format.value
            }
            
            # 根据格式转换数据
            if config.format != ReportFormat.JSON:
                report['content'] = await self._format_report(report, config.format)
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}", exc_info=True)
            raise
    
    async def _generate_usage_summary(self, config: ReportConfig) -> Dict[str, Any]:
        """生成使用摘要报告"""
        # 查询基础数据
        stmt = select(
            ModelUsageDaily.model_id,
            ModelConfiguration.name.label('model_name'),
            ModelConfiguration.model_type,
            func.sum(ModelUsageDaily.request_count).label('total_requests'),
            func.sum(ModelUsageDaily.success_count).label('total_success'),
            func.sum(ModelUsageDaily.error_count).label('total_errors'),
            func.sum(ModelUsageDaily.input_tokens).label('total_input_tokens'),
            func.sum(ModelUsageDaily.output_tokens).label('total_output_tokens'),
            func.avg(ModelUsageDaily.avg_response_time).label('avg_response_time'),
            func.max(ModelUsageDaily.max_response_time).label('max_response_time'),
            func.count(ModelUsageDaily.id).label('active_days')
        ).select_from(
            ModelUsageDaily.join(ModelConfiguration)
        ).where(
            and_(
                ModelUsageDaily.usage_date >= config.start_date,
                ModelUsageDaily.usage_date <= config.end_date
            )
        ).group_by(
            ModelUsageDaily.model_id,
            ModelConfiguration.name,
            ModelConfiguration.model_type
        )
        
        if config.model_ids:
            stmt = stmt.where(ModelUsageDaily.model_id.in_(config.model_ids))
        
        result = await self.db.execute(stmt)
        records = result.all()
        
        # 处理数据
        summary_data = []
        total_requests = 0
        total_tokens = 0
        
        for row in records:
            success_rate = (row.total_success / row.total_requests * 100) if row.total_requests > 0 else 0
            total_tokens_row = row.total_input_tokens + row.total_output_tokens
            
            record = {
                'model_id': str(row.model_id),
                'model_name': row.model_name,
                'model_type': row.model_type,
                'total_requests': row.total_requests,
                'success_rate': round(success_rate, 2),
                'total_tokens': total_tokens_row,
                'input_tokens': row.total_input_tokens,
                'output_tokens': row.total_output_tokens,
                'avg_response_time': round(row.avg_response_time or 0, 2),
                'max_response_time': round(row.max_response_time or 0, 2),
                'active_days': row.active_days
            }
            
            summary_data.append(record)
            total_requests += row.total_requests
            total_tokens += total_tokens_row
        
        return {
            'records': summary_data,
            'summary': {
                'total_models': len(summary_data),
                'total_requests': total_requests,
                'total_tokens': total_tokens,
                'period_days': (config.end_date - config.start_date).days + 1
            }
        }
    
    async def _generate_cost_analysis(self, config: ReportConfig) -> Dict[str, Any]:
        """生成成本分析报告"""
        # 查询成本数据
        stmt = select(
            ModelUsageDaily.model_id,
            ModelConfiguration.name.label('model_name'),
            ModelConfiguration.input_price,
            ModelConfiguration.output_price,
            ModelUsageDaily.usage_date,
            ModelUsageDaily.input_tokens,
            ModelUsageDaily.output_tokens
        ).select_from(
            ModelUsageDaily.join(ModelConfiguration)
        ).where(
            and_(
                ModelUsageDaily.usage_date >= config.start_date,
                ModelUsageDaily.usage_date <= config.end_date
            )
        ).order_by(ModelUsageDaily.usage_date)
        
        if config.model_ids:
            stmt = stmt.where(ModelUsageDaily.model_id.in_(config.model_ids))
        
        result = await self.db.execute(stmt)
        records = result.all()
        
        # 计算成本
        cost_data = []
        total_cost = 0.0
        model_costs = {}
        
        for row in records:
            input_price = row.input_price or 0.0
            output_price = row.output_price or 0.0
            
            input_cost = (row.input_tokens * input_price) / 1_000_000
            output_cost = (row.output_tokens * output_price) / 1_000_000
            daily_cost = input_cost + output_cost
            
            record = {
                'model_id': str(row.model_id),
                'model_name': row.model_name,
                'date': row.usage_date.isoformat(),
                'input_tokens': row.input_tokens,
                'output_tokens': row.output_tokens,
                'input_cost': round(input_cost, 6),
                'output_cost': round(output_cost, 6),
                'total_cost': round(daily_cost, 6)
            }
            
            cost_data.append(record)
            total_cost += daily_cost
            
            # 按模型汇总
            model_key = str(row.model_id)
            if model_key not in model_costs:
                model_costs[model_key] = {
                    'model_name': row.model_name,
                    'total_cost': 0.0,
                    'input_cost': 0.0,
                    'output_cost': 0.0
                }
            
            model_costs[model_key]['total_cost'] += daily_cost
            model_costs[model_key]['input_cost'] += input_cost
            model_costs[model_key]['output_cost'] += output_cost
        
        # 排序模型成本
        sorted_models = sorted(
            model_costs.items(),
            key=lambda x: x[1]['total_cost'],
            reverse=True
        )
        
        return {
            'records': cost_data,
            'summary': {
                'total_cost': round(total_cost, 6),
                'avg_daily_cost': round(total_cost / max(1, (config.end_date - config.start_date).days + 1), 6),
                'model_breakdown': [
                    {
                        'model_id': model_id,
                        'model_name': data['model_name'],
                        'total_cost': round(data['total_cost'], 6),
                        'cost_percentage': round(data['total_cost'] / total_cost * 100, 2) if total_cost > 0 else 0
                    }
                    for model_id, data in sorted_models
                ]
            }
        }
    
    async def _generate_trend_analysis(self, config: ReportConfig) -> Dict[str, Any]:
        """生成趋势分析报告"""
        trend_data = {}
        
        # 分析所有模型或指定模型的趋势
        if config.model_ids:
            for model_id in config.model_ids:
                trends = await self.analytics.analyze_usage_trends(model_id, days=30)
                if trends:
                    trend_data[str(model_id)] = trends
        else:
            # 分析整体趋势
            trends = await self.analytics.analyze_usage_trends(days=30)
            if trends:
                trend_data['overall'] = trends
        
        # 转换为可序列化格式
        serializable_trends = {}
        for key, trends in trend_data.items():
            serializable_trends[key] = {}
            for metric, trend in trends.items():
                serializable_trends[key][metric] = {
                    'direction': trend.direction.value,
                    'slope': trend.slope,
                    'correlation': trend.correlation,
                    'confidence': trend.confidence,
                    'prediction_7d': trend.prediction_7d,
                    'prediction_30d': trend.prediction_30d,
                    'volatility': trend.volatility
                }
        
        return {
            'trends': serializable_trends,
            'analysis_period': 30,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def _generate_model_comparison(self, config: ReportConfig) -> Dict[str, Any]:
        """生成模型对比报告"""
        if not config.model_ids or len(config.model_ids) < 2:
            return {'error': '模型对比需要至少2个模型'}
        
        comparison_data = []
        
        for model_id in config.model_ids:
            # 获取模型基础数据
            stmt = select(
                ModelConfiguration.name,
                ModelConfiguration.model_type,
                ModelConfiguration.input_price,
                ModelConfiguration.output_price
            ).where(ModelConfiguration.id == model_id)
            
            result = await self.db.execute(stmt)
            model_info = result.first()
            
            if not model_info:
                continue
            
            # 获取使用统计
            usage_stmt = select(
                func.sum(ModelUsageDaily.request_count).label('total_requests'),
                func.sum(ModelUsageDaily.input_tokens).label('total_input_tokens'),
                func.sum(ModelUsageDaily.output_tokens).label('total_output_tokens'),
                func.avg(ModelUsageDaily.avg_response_time).label('avg_response_time'),
                func.sum(ModelUsageDaily.error_count).label('total_errors')
            ).where(
                and_(
                    ModelUsageDaily.model_id == model_id,
                    ModelUsageDaily.usage_date >= config.start_date,
                    ModelUsageDaily.usage_date <= config.end_date
                )
            )
            
            usage_result = await self.db.execute(usage_stmt)
            usage_data = usage_result.first()
            
            if usage_data:
                total_tokens = usage_data.total_input_tokens + usage_data.total_output_tokens
                input_cost = (usage_data.total_input_tokens * (model_info.input_price or 0)) / 1_000_000
                output_cost = (usage_data.total_output_tokens * (model_info.output_price or 0)) / 1_000_000
                
                comparison_data.append({
                    'model_id': str(model_id),
                    'model_name': model_info.name,
                    'model_type': model_info.model_type,
                    'total_requests': usage_data.total_requests or 0,
                    'total_tokens': total_tokens,
                    'total_cost': round(input_cost + output_cost, 6),
                    'avg_response_time': round(usage_data.avg_response_time or 0, 2),
                    'error_rate': round((usage_data.total_errors or 0) / max(1, usage_data.total_requests or 1) * 100, 2),
                    'cost_per_request': round((input_cost + output_cost) / max(1, usage_data.total_requests or 1), 6),
                    'tokens_per_request': round(total_tokens / max(1, usage_data.total_requests or 1), 2)
                })
        
        return {
            'models': comparison_data,
            'comparison_metrics': [
                'total_requests', 'total_tokens', 'total_cost',
                'avg_response_time', 'error_rate', 'cost_per_request', 'tokens_per_request'
            ]
        }
    
    async def _generate_performance_report(self, config: ReportConfig) -> Dict[str, Any]:
        """生成性能报告"""
        # 查询性能数据
        stmt = select(
            ModelUsageDaily.model_id,
            ModelConfiguration.name.label('model_name'),
            ModelUsageDaily.usage_date,
            ModelUsageDaily.avg_response_time,
            ModelUsageDaily.max_response_time,
            ModelUsageDaily.avg_first_token_time,
            ModelUsageDaily.request_count,
            ModelUsageDaily.error_count
        ).select_from(
            ModelUsageDaily.join(ModelConfiguration)
        ).where(
            and_(
                ModelUsageDaily.usage_date >= config.start_date,
                ModelUsageDaily.usage_date <= config.end_date
            )
        ).order_by(ModelUsageDaily.usage_date)
        
        if config.model_ids:
            stmt = stmt.where(ModelUsageDaily.model_id.in_(config.model_ids))
        
        result = await self.db.execute(stmt)
        records = result.all()
        
        performance_data = []
        for row in records:
            performance_data.append({
                'model_id': str(row.model_id),
                'model_name': row.model_name,
                'date': row.usage_date.isoformat(),
                'avg_response_time': row.avg_response_time,
                'max_response_time': row.max_response_time,
                'avg_first_token_time': row.avg_first_token_time,
                'request_count': row.request_count,
                'error_count': row.error_count,
                'error_rate': round((row.error_count or 0) / max(1, row.request_count or 1) * 100, 2)
            })
        
        return {
            'records': performance_data,
            'metrics': ['avg_response_time', 'max_response_time', 'avg_first_token_time', 'error_rate']
        }
    
    async def _generate_custom_report(self, config: ReportConfig) -> Dict[str, Any]:
        """生成自定义报告"""
        # 基础查询
        stmt = select(ModelUsageDaily).where(
            and_(
                ModelUsageDaily.usage_date >= config.start_date,
                ModelUsageDaily.usage_date <= config.end_date
            )
        )
        
        if config.model_ids:
            stmt = stmt.where(ModelUsageDaily.model_id.in_(config.model_ids))
        
        result = await self.db.execute(stmt)
        records = result.scalars().all()
        
        # 转换为字典格式
        data = []
        for record in records:
            data.append({
                'model_id': str(record.model_id),
                'usage_date': record.usage_date.isoformat(),
                'request_count': record.request_count,
                'success_count': record.success_count,
                'error_count': record.error_count,
                'input_tokens': record.input_tokens,
                'output_tokens': record.output_tokens,
                'avg_response_time': record.avg_response_time,
                'max_response_time': record.max_response_time
            })
        
        return {'records': data}
    
    async def _format_report(self, report: Dict[str, Any], format: ReportFormat) -> str:
        """格式化报告"""
        if format == ReportFormat.CSV:
            return self._to_csv(report['data'])
        elif format == ReportFormat.HTML:
            return self._to_html(report)
        else:
            return json.dumps(report, indent=2, default=str)
    
    def _to_csv(self, data: Dict[str, Any]) -> str:
        """转换为CSV格式"""
        output = io.StringIO()
        
        if 'records' in data and data['records']:
            writer = csv.DictWriter(output, fieldnames=data['records'][0].keys())
            writer.writeheader()
            writer.writerows(data['records'])
        
        return output.getvalue()
    
    def _to_html(self, report: Dict[str, Any]) -> str:
        """转换为HTML格式"""
        html = f"""
        <html>
        <head>
            <title>{report['metadata']['title']}</title>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>{report['metadata']['title']}</h1>
            <p>{report['metadata']['description']}</p>
            <p>生成时间: {report['metadata']['generated_at']}</p>
        """
        
        # 添加数据表格
        if 'records' in report['data'] and report['data']['records']:
            html += "<table><thead><tr>"
            for key in report['data']['records'][0].keys():
                html += f"<th>{key}</th>"
            html += "</tr></thead><tbody>"
            
            for record in report['data']['records']:
                html += "<tr>"
                for value in record.values():
                    html += f"<td>{value}</td>"
                html += "</tr>"
            
            html += "</tbody></table>"
        
        html += "</body></html>"
        return html
    
    def _get_report_title(self, config: ReportConfig) -> str:
        """获取报告标题"""
        titles = {
            ReportType.USAGE_SUMMARY: "使用摘要报告",
            ReportType.COST_ANALYSIS: "成本分析报告",
            ReportType.TREND_ANALYSIS: "趋势分析报告",
            ReportType.MODEL_COMPARISON: "模型对比报告",
            ReportType.PERFORMANCE_REPORT: "性能报告"
        }
        return titles.get(config.report_type, "自定义报告")
    
    def _get_report_description(self, config: ReportConfig) -> str:
        """获取报告描述"""
        return f"时间范围: {config.start_date} 至 {config.end_date}"
