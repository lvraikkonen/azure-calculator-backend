from typing import List, Dict, Any, Optional
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field


# 使用量查询参数
class UsageQueryParams(BaseModel):
    """使用量查询参数Schema"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    model_id: Optional[UUID] = Field(None, description="模型ID(可选)")
    user_id: Optional[UUID] = Field(None, description="用户ID(可选)")
    group_by: Optional[str] = Field("day", description="分组方式: day, hour, model, user")


# Token使用数据
class TokenUsageData(BaseModel):
    """Token使用数据Schema"""
    input_tokens: int = Field(0, description="输入token数")
    output_tokens: int = Field(0, description="输出token数")
    total_tokens: int = Field(0, description="总token数")
    input_cost: float = Field(0.0, description="输入token成本")
    output_cost: float = Field(0.0, description="输出token成本")
    total_cost: float = Field(0.0, description="总成本")


# 日使用量响应
class DailyUsageResponse(BaseModel):
    """日使用量响应Schema"""
    date: date = Field(..., description="统计日期")
    model_id: Optional[UUID] = Field(None, description="模型ID")
    model_name: Optional[str] = Field(None, description="模型名称")

    # 使用计数
    request_count: int = Field(0, description="请求总数")
    success_count: int = Field(0, description="成功请求数")
    error_count: int = Field(0, description="错误请求数")

    # Token统计
    tokens: TokenUsageData = Field(..., description="Token使用数据")

    # 性能统计
    avg_response_time: Optional[float] = Field(None, description="平均响应时间(ms)")
    avg_first_token_time: Optional[float] = Field(None, description="平均首个token响应时间(ms)")

    # 用户统计
    unique_users: int = Field(0, description="唯一用户数")

    class Config:
        orm_mode = True


# 小时使用量响应
class HourlyUsageResponse(BaseModel):
    """小时使用量响应Schema"""
    hour_timestamp: datetime = Field(..., description="小时时间戳")
    model_id: Optional[UUID] = Field(None, description="模型ID")
    model_name: Optional[str] = Field(None, description="模型名称")

    # 使用计数
    request_count: int = Field(0, description="请求总数")
    success_count: int = Field(0, description="成功请求数")
    error_count: int = Field(0, description="错误请求数")

    # Token统计
    tokens: TokenUsageData = Field(..., description="Token使用数据")

    # 性能统计
    avg_response_time: Optional[float] = Field(None, description="平均响应时间(ms)")

    class Config:
        orm_mode = True


# 使用量摘要响应
class UsageSummaryResponse(BaseModel):
    """使用量摘要响应Schema"""
    period_start: date = Field(..., description="统计周期开始")
    period_end: date = Field(..., description="统计周期结束")

    # 总体统计
    total_requests: int = Field(0, description="总请求数")
    total_success: int = Field(0, description="总成功请求数")
    total_errors: int = Field(0, description="总错误请求数")
    success_rate: float = Field(0.0, description="成功率(%)")

    # Token统计
    tokens: TokenUsageData = Field(..., description="Token使用数据")

    # 模型分布
    model_distribution: Dict[str, int] = Field(default_factory=dict, description="模型使用分布")

    # 性能统计
    avg_response_time: Optional[float] = Field(None, description="平均响应时间(ms)")

    # 用户统计
    unique_users: int = Field(0, description="唯一用户数")


# 用户使用量响应
class UserUsageResponse(BaseModel):
    """用户使用量响应Schema"""
    user_id: UUID = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")

    # 使用统计
    total_requests: int = Field(0, description="总请求数")
    tokens: TokenUsageData = Field(..., description="Token使用数据")

    # 模型使用分布
    model_usage: Dict[str, int] = Field(default_factory=dict, description="模型使用分布")

    class Config:
        orm_mode = True


# 使用量报表请求
class UsageReportRequest(BaseModel):
    """使用量报表请求Schema"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    group_by: str = Field("day", description="分组方式: day, model, user")
    models: Optional[List[UUID]] = Field(None, description="模型ID列表(可选)")
    users: Optional[List[UUID]] = Field(None, description="用户ID列表(可选)")
    include_costs: bool = Field(True, description="是否包含成本信息")
    format: str = Field("json", description="报表格式: json, csv, excel")


# 使用量报表响应
class UsageReportResponse(BaseModel):
    """使用量报表响应Schema"""
    report_id: UUID = Field(..., description="报表ID")
    created_at: datetime = Field(..., description="创建时间")
    parameters: UsageReportRequest = Field(..., description="报表参数")
    summary: UsageSummaryResponse = Field(..., description="使用量摘要")
    report_url: Optional[str] = Field(None, description="报表下载URL(如适用)")