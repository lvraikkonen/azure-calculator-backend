# app/schemas/token_billing.py

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# 枚举类型
class TrendDirectionEnum(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class ReportTypeEnum(str, Enum):
    USAGE_SUMMARY = "usage_summary"
    COST_ANALYSIS = "cost_analysis"
    TREND_ANALYSIS = "trend_analysis"
    MODEL_COMPARISON = "model_comparison"
    PERFORMANCE_REPORT = "performance_report"
    CUSTOM = "custom"


class ReportFormatEnum(str, Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"


# 基础数据模型
class TrendAnalysisData(BaseModel):
    """趋势分析数据"""
    direction: TrendDirectionEnum
    slope: float
    correlation: float
    confidence: float
    prediction_7d: float
    prediction_30d: float
    volatility: float
    seasonal_pattern: Optional[Dict[str, float]] = None


class UsagePatternData(BaseModel):
    """使用模式数据"""
    peak_hours: List[int]
    peak_days: List[str]
    usage_distribution: Dict[str, float]
    efficiency_score: float
    cost_optimization_potential: float


class CostForecastData(BaseModel):
    """成本预测数据"""
    period: str
    predicted_cost: float
    confidence_interval: List[float]  # [lower, upper]
    factors: Dict[str, float]
    recommendations: List[str]


# 请求模型
class ReportGenerationRequest(BaseModel):
    """报告生成请求"""
    report_type: ReportTypeEnum
    format: ReportFormatEnum = ReportFormatEnum.JSON
    start_date: date
    end_date: date
    model_ids: Optional[List[UUID]] = None
    include_trends: bool = True
    include_predictions: bool = False
    include_recommendations: bool = True
    group_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    custom_fields: Optional[List[str]] = None


class MonitoringCheckRequest(BaseModel):
    """监控检查请求"""
    target_date: Optional[date] = None
    threshold_multiplier: float = 3.0


class AggregationTaskRequest(BaseModel):
    """聚合任务请求"""
    target_date: Optional[str] = None


class MonitoringTaskRequest(BaseModel):
    """监控任务请求"""
    threshold_multiplier: float = 3.0


class ForecastTaskRequest(BaseModel):
    """预测任务请求"""
    projection_days: int = 30


class DataExportRequest(BaseModel):
    """数据导出请求"""
    export_type: str  # "usage_summary", "cost_analysis", etc.
    format: str = "json"
    start_date: date
    end_date: date
    model_ids: Optional[List[UUID]] = None
    filters: Optional[Dict[str, Any]] = None


# 响应模型
class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    model_id: Optional[str] = None
    analysis_period: int
    trends: Dict[str, TrendAnalysisData]
    generated_at: datetime


class UsagePatternResponse(BaseModel):
    """使用模式响应"""
    model_id: Optional[str] = None
    analysis_period: int
    pattern: UsagePatternData
    generated_at: datetime


class CostForecastResponse(BaseModel):
    """成本预测响应"""
    model_id: Optional[str] = None
    forecast: CostForecastData
    generated_at: datetime


class ReportGenerationResponse(BaseModel):
    """报告生成响应"""
    report_id: str
    status: str
    download_url: Optional[str] = None
    metadata: Dict[str, Any]
    generated_at: datetime


class MonitoringCheckResponse(BaseModel):
    """监控检查响应"""
    target_date: Optional[date]
    alerts_found: int
    alerts_by_type: Dict[str, List[Dict[str, Any]]]
    checked_at: datetime


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    task_type: str
    status: str
    scheduled_at: datetime


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    checked_at: datetime


class TaskCancelResponse(BaseModel):
    """任务取消响应"""
    task_id: str
    cancelled: bool
    cancelled_at: datetime


class PluginInfo(BaseModel):
    """插件信息"""
    name: str
    version: str
    description: str
    type: str
    status: str
    loaded_at: Optional[str] = None


class PluginListResponse(BaseModel):
    """插件列表响应"""
    plugins: List[PluginInfo]
    total_count: int


class DataExportResponse(BaseModel):
    """数据导出响应"""
    export_id: str
    format: str
    data_size: int
    export_results: Dict[str, Any]
    exported_at: datetime


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    database_connected: bool
    active_plugins: int
    total_plugins: int
    checked_at: datetime
    error: Optional[str] = None


# 高级分析模型
class ModelComparisonItem(BaseModel):
    """模型对比项"""
    model_id: str
    model_name: str
    model_type: str
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    error_rate: float
    cost_per_request: float
    tokens_per_request: float


class ModelComparisonResponse(BaseModel):
    """模型对比响应"""
    models: List[ModelComparisonItem]
    comparison_metrics: List[str]
    period: str
    generated_at: datetime


class PerformanceMetric(BaseModel):
    """性能指标"""
    model_id: str
    model_name: str
    date: str
    avg_response_time: Optional[float]
    max_response_time: Optional[float]
    avg_first_token_time: Optional[float]
    request_count: int
    error_count: int
    error_rate: float


class PerformanceReportResponse(BaseModel):
    """性能报告响应"""
    metrics: List[PerformanceMetric]
    summary: Dict[str, Any]
    period: str
    generated_at: datetime


class UsageSummaryItem(BaseModel):
    """使用摘要项"""
    model_id: str
    model_name: str
    model_type: str
    total_requests: int
    success_rate: float
    total_tokens: int
    input_tokens: int
    output_tokens: int
    avg_response_time: float
    max_response_time: float
    active_days: int


class UsageSummaryResponse(BaseModel):
    """使用摘要响应"""
    records: List[UsageSummaryItem]
    summary: Dict[str, Any]
    period: str
    generated_at: datetime


class CostAnalysisItem(BaseModel):
    """成本分析项"""
    model_id: str
    model_name: str
    date: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


class CostAnalysisResponse(BaseModel):
    """成本分析响应"""
    records: List[CostAnalysisItem]
    summary: Dict[str, Any]
    period: str
    generated_at: datetime


# 实时数据流模型
class RealTimeUsageData(BaseModel):
    """实时使用数据"""
    timestamp: datetime
    model_id: str
    model_name: str
    request_count: int
    token_count: int
    cost: float
    response_time: Optional[float]
    success: bool


class RealTimeStreamResponse(BaseModel):
    """实时流响应"""
    event_type: str  # "usage", "alert", "status"
    data: Dict[str, Any]
    timestamp: datetime


# 配置模型
class AlertConfiguration(BaseModel):
    """告警配置"""
    enabled: bool = True
    thresholds: Dict[str, float]
    notification_channels: List[str]
    cooldown_minutes: int = 60


class BudgetConfiguration(BaseModel):
    """预算配置"""
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    alert_percentage: float = 80.0  # 达到预算百分比时告警
    auto_disable: bool = False  # 超预算时自动禁用


class SystemConfiguration(BaseModel):
    """系统配置"""
    cache_enabled: bool = True
    cache_ttl: int = 3600
    monitoring_enabled: bool = True
    alert_config: AlertConfiguration
    budget_config: Optional[BudgetConfiguration] = None
    retention_days: int = 90


class ConfigurationUpdateRequest(BaseModel):
    """配置更新请求"""
    config: SystemConfiguration


class ConfigurationResponse(BaseModel):
    """配置响应"""
    config: SystemConfiguration
    updated_at: datetime
    version: str
