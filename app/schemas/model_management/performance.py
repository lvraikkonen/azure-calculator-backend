from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# 测试配置基础Schema
class TestConfigBase(BaseModel):
    """性能测试配置基础Schema"""
    test_name: str = Field(..., min_length=1, max_length=100, description="测试名称")
    test_type: str = Field(..., description="测试类型: standard, long_context, etc.")
    rounds: int = Field(1, ge=1, description="测试轮数")


# 创建测试请求
class TestCreate(TestConfigBase):
    """创建测试请求Schema"""
    model_id: UUID = Field(..., description="要测试的模型ID")
    test_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="测试参数")


# 更新测试请求
class TestUpdate(BaseModel):
    """更新测试请求Schema"""
    test_name: Optional[str] = Field(None, min_length=1, max_length=100)
    rounds: Optional[int] = Field(None, ge=1)
    test_params: Optional[Dict[str, Any]] = None


# 测试响应
class TestResponse(TestConfigBase):
    """测试响应Schema"""
    id: UUID = Field(..., description="测试ID")
    model_id: UUID = Field(..., description="模型ID")
    model_name: str = Field(..., description="模型名称")

    # 测试结果
    avg_response_time: Optional[float] = Field(None, description="平均响应时间(ms)")
    avg_first_token_time: Optional[float] = Field(None, description="平均首个token响应时间(ms)")
    avg_throughput: Optional[float] = Field(None, description="平均吞吐量(tokens/sec)")
    success_rate: Optional[float] = Field(None, description="成功率(%)")
    error_rate: Optional[float] = Field(None, description="错误率(%)")

    # 测试参数
    test_params: Dict[str, Any] = Field(default_factory=dict, description="测试参数")

    # 元数据
    test_date: datetime = Field(..., description="测试日期")
    tested_by: Optional[UUID] = Field(None, description="测试执行人ID")

    class Config:
        from_attributes = True


# 简化的测试结果摘要
class TestResultSummary(BaseModel):
    """用于列表展示的简化测试结果Schema"""
    id: UUID
    test_name: str
    test_type: str
    model_id: UUID
    model_name: str
    avg_response_time: Optional[float]
    success_rate: Optional[float]
    test_date: datetime

    class Config:
        from_attributes = True


# 测试列表响应
class TestListResponse(BaseModel):
    """测试列表响应Schema"""
    total: int = Field(..., description="总测试数")
    tests: List[TestResultSummary] = Field(..., description="测试列表")


# 测试详情响应
class TestDetailResponse(TestResponse):
    """测试详情响应Schema"""
    input_tokens: Optional[int] = Field(None, description="平均输入token数")
    output_tokens: Optional[int] = Field(None, description="平均输出token数")
    tokens_per_second: Optional[float] = Field(None, description="平均token生成速度(tokens/sec)")
    input_cost: Optional[float] = Field(None, description="输入token成本")
    output_cost: Optional[float] = Field(None, description="输出token成本")
    total_cost: Optional[float] = Field(None, description="总成本")
    detailed_results: Optional[Dict[str, Any]] = Field(None, description="详细测试结果")

    class Config:
        from_attributes = True

    @property
    def total_tokens(self) -> Optional[int]:
        """总token数"""
        if self.input_tokens is not None and self.output_tokens is not None:
            return self.input_tokens + self.output_tokens
        return None


# 速度测试请求
class SpeedTestRequest(BaseModel):
    """速度测试请求Schema"""
    model_id: UUID = Field(..., description="要测试的模型ID")
    rounds: int = Field(3, ge=1, le=10, description="测试轮数")
    test_type: str = Field("standard", description="测试类型")
    prompt: Optional[str] = Field(None, description="测试使用的提示词")

    @classmethod
    @field_validator("test_type")
    def validate_test_type(cls, v):
        allowed_types = ['standard', 'long_context', 'complex_reasoning']
        if v not in allowed_types:
            raise ValueError(f"test_type必须是以下之一: {', '.join(allowed_types)}")
        return v


# 延迟测试请求
class LatencyTestRequest(BaseModel):
    """延迟测试请求Schema"""
    model_id: UUID = Field(..., description="要测试的模型ID")
    rounds: int = Field(5, ge=1, le=20, description="测试轮数")
    measure_first_token: bool = Field(True, description="是否测量首个token延迟")


# 批量测试请求
class BatchTestRequest(BaseModel):
    """批量测试请求Schema"""
    model_ids: List[UUID] = Field(..., min_items=1, max_items=10, description="要测试的模型ID列表")
    test_type: str = Field("standard", description="测试类型")
    rounds: int = Field(3, ge=1, le=10, description="测试轮数")
    prompt: Optional[str] = Field(None, description="测试使用的提示词")

    @classmethod
    @field_validator("test_type")
    def validate_test_type(cls, v):
        allowed_types = ['standard', 'long_context', 'complex_reasoning']
        if v not in allowed_types:
            raise ValueError(f"test_type必须是以下之一: {', '.join(allowed_types)}")
        return v


# 批量测试响应
class BatchTestResponse(BaseModel):
    """批量测试响应Schema"""
    batch_id: UUID = Field(..., description="批量测试ID")
    total_models: int = Field(..., description="总模型数")
    completed_tests: List[TestResponse] = Field(..., description="已完成的测试")
    failed_tests: List[Dict[str, Any]] = Field(..., description="失败的测试")
    status: str = Field(..., description="批量测试状态: running, completed, failed")


# 测试比较请求
class TestComparisonRequest(BaseModel):
    """测试比较请求Schema"""
    test_ids: List[UUID] = Field(..., min_items=2, max_items=10, description="要比较的测试ID列表")
    metrics: List[str] = Field(
        default=["avg_response_time", "avg_first_token_time", "success_rate"],
        description="要比较的指标"
    )


# 测试比较响应
class TestComparisonResponse(BaseModel):
    """测试比较响应Schema"""
    comparison_id: UUID = Field(..., description="比较ID")
    tests: List[TestDetailResponse] = Field(..., description="参与比较的测试")
    metrics_comparison: Dict[str, Any] = Field(..., description="指标比较结果")
    summary: Dict[str, Any] = Field(..., description="比较摘要")
    created_at: datetime = Field(..., description="比较创建时间")


# 测试调度请求
class TestScheduleRequest(BaseModel):
    """测试调度请求Schema"""
    model_ids: List[UUID] = Field(..., min_items=1, max_items=20, description="要测试的模型ID列表")
    test_type: str = Field("standard", description="测试类型")
    rounds: int = Field(3, ge=1, le=10, description="测试轮数")
    prompt: Optional[str] = Field(None, description="测试使用的提示词")

    # 调度配置
    schedule_type: str = Field("once", description="调度类型: once, daily, weekly, monthly")
    schedule_time: Optional[datetime] = Field(None, description="调度时间")
    cron_expression: Optional[str] = Field(None, description="Cron表达式（高级调度）")
    timezone: str = Field("UTC", description="时区")

    # 通知配置
    notify_on_completion: bool = Field(True, description="完成时是否通知")
    notify_on_failure: bool = Field(True, description="失败时是否通知")
    notification_emails: List[str] = Field(default_factory=list, description="通知邮箱列表")

    @classmethod
    @field_validator("test_type")
    def validate_test_type(cls, v):
        allowed_types = ['standard', 'long_context', 'complex_reasoning', 'latency']
        if v not in allowed_types:
            raise ValueError(f"test_type必须是以下之一: {', '.join(allowed_types)}")
        return v

    @classmethod
    @field_validator("schedule_type")
    def validate_schedule_type(cls, v):
        allowed_types = ['once', 'daily', 'weekly', 'monthly', 'cron']
        if v not in allowed_types:
            raise ValueError(f"schedule_type必须是以下之一: {', '.join(allowed_types)}")
        return v


# 测试调度响应
class TestScheduleResponse(BaseModel):
    """测试调度响应Schema"""
    schedule_id: UUID = Field(..., description="调度ID")
    model_ids: List[UUID] = Field(..., description="模型ID列表")
    test_type: str = Field(..., description="测试类型")
    schedule_type: str = Field(..., description="调度类型")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    status: str = Field(..., description="调度状态: active, paused, completed, failed")
    created_at: datetime = Field(..., description="创建时间")
    created_by: Optional[UUID] = Field(None, description="创建人ID")


# 测试结果导出请求
class TestExportRequest(BaseModel):
    """测试结果导出请求Schema"""
    test_ids: Optional[List[UUID]] = Field(None, description="要导出的测试ID列表")
    model_ids: Optional[List[UUID]] = Field(None, description="按模型ID筛选")
    test_type: Optional[str] = Field(None, description="按测试类型筛选")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")

    # 导出配置
    export_format: str = Field("csv", description="导出格式: csv, excel, json")
    include_detailed_results: bool = Field(False, description="是否包含详细结果")
    include_raw_data: bool = Field(False, description="是否包含原始数据")

    @classmethod
    @field_validator("export_format")
    def validate_export_format(cls, v):
        allowed_formats = ['csv', 'excel', 'json', 'pdf']
        if v not in allowed_formats:
            raise ValueError(f"export_format必须是以下之一: {', '.join(allowed_formats)}")
        return v


# 测试结果导出响应
class TestExportResponse(BaseModel):
    """测试结果导出响应Schema"""
    export_id: UUID = Field(..., description="导出ID")
    file_url: str = Field(..., description="文件下载URL")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    export_format: str = Field(..., description="导出格式")
    record_count: int = Field(..., description="导出记录数")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: datetime = Field(..., description="过期时间")


# 趋势分析请求
class TrendAnalysisRequest(BaseModel):
    """趋势分析请求Schema"""
    model_ids: List[UUID] = Field(..., min_items=1, description="要分析的模型ID列表")
    metrics: List[str] = Field(
        default=["avg_response_time", "success_rate", "avg_throughput"],
        description="要分析的指标"
    )
    time_range: str = Field("30d", description="时间范围: 7d, 30d, 90d, 1y")
    granularity: str = Field("daily", description="粒度: hourly, daily, weekly, monthly")

    @classmethod
    @field_validator("time_range")
    def validate_time_range(cls, v):
        allowed_ranges = ['7d', '30d', '90d', '1y']
        if v not in allowed_ranges:
            raise ValueError(f"time_range必须是以下之一: {', '.join(allowed_ranges)}")
        return v

    @classmethod
    @field_validator("granularity")
    def validate_granularity(cls, v):
        allowed_granularities = ['hourly', 'daily', 'weekly', 'monthly']
        if v not in allowed_granularities:
            raise ValueError(f"granularity必须是以下之一: {', '.join(allowed_granularities)}")
        return v


# 趋势分析响应
class TrendAnalysisResponse(BaseModel):
    """趋势分析响应Schema"""
    analysis_id: UUID = Field(..., description="分析ID")
    model_trends: Dict[str, Any] = Field(..., description="模型趋势数据")
    metric_trends: Dict[str, Any] = Field(..., description="指标趋势数据")
    insights: List[Dict[str, Any]] = Field(..., description="分析洞察")
    recommendations: List[str] = Field(..., description="改进建议")
    created_at: datetime = Field(..., description="创建时间")