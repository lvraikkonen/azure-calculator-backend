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