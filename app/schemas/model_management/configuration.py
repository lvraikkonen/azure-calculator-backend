from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator


# 基础模型配置Schema
class ModelConfigBase(BaseModel):
    """模型配置基础Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="模型唯一名称")
    display_name: str = Field(..., min_length=1, max_length=100, description="模型显示名称")
    description: Optional[str] = Field(None, max_length=500, description="模型描述")
    model_type: str = Field(..., description="模型类型: openai, deepseek等")
    model_name: str = Field(..., description="具体模型名称")

    # 可选通用配置
    is_custom: Optional[bool] = Field(False, description="是否自定义模型")
    is_active: Optional[bool] = Field(True, description="模型是否激活")
    is_visible: Optional[bool] = Field(True, description="是否在用户界面可见")

    # 验证方法
    @validator('model_type')
    def validate_model_type(cls, v):
        allowed_types = ['openai', 'deepseek', 'anthropic', 'azure_openai']
        if v.lower() not in allowed_types:
            raise ValueError(f"model_type必须是以下之一: {', '.join(allowed_types)}")
        return v.lower()


# 创建模型请求
class ModelCreate(ModelConfigBase):
    """创建模型请求Schema"""
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="附加参数")
    input_price: float = Field(0.0, ge=0, description="输入token价格(单位:百万tokens)")
    output_price: float = Field(0.0, ge=0, description="输出token价格(单位:百万tokens)")
    capabilities: Optional[List[str]] = Field(default_factory=list, description="模型能力列表")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大token限制")
    rate_limit: Optional[int] = Field(None, gt=0, description="每分钟最大请求次数")
    user_rate_limit: Optional[int] = Field(None, gt=0, description="每用户每分钟最大请求次数")


# 更新模型请求
class ModelUpdate(BaseModel):
    """更新模型请求Schema"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    input_price: Optional[float] = Field(None, ge=0)
    output_price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_visible: Optional[bool] = None
    capabilities: Optional[List[str]] = None
    max_tokens: Optional[int] = Field(None, gt=0)
    rate_limit: Optional[int] = Field(None, gt=0)
    user_rate_limit: Optional[int] = Field(None, gt=0)


# 模型测试请求
class ModelTestRequest(BaseModel):
    """模型连接测试请求Schema"""
    model_id: UUID = Field(..., description="要测试的模型ID")
    test_message: Optional[str] = Field("This is a test message", description="测试消息")


# 模型测试响应
class ModelTestResponse(BaseModel):
    """模型连接测试响应Schema"""
    success: bool = Field(..., description="测试是否成功")
    response_time: Optional[float] = Field(None, description="响应时间(毫秒)")
    message: str = Field(..., description="测试结果消息")
    response: Optional[str] = Field(None, description="模型响应内容")
    error: Optional[str] = Field(None, description="错误详情(如有)")


# 基础模型响应
class ModelResponse(ModelConfigBase):
    """模型响应Schema"""
    id: UUID = Field(..., description="模型ID")
    api_key_masked: Optional[str] = Field(None, description="掩码处理后的API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    input_price: float = Field(..., description="输入token价格")
    output_price: float = Field(..., description="输出token价格")
    currency: str = Field(..., description="货币单位")
    capabilities: List[str] = Field(default_factory=list, description="模型能力列表")
    max_tokens: Optional[int] = Field(None, description="最大token限制")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 额外统计信息
    total_requests: Optional[int] = Field(0, description="总请求数")
    avg_response_time: Optional[float] = Field(None, description="平均响应时间(ms)")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")

    class Config:
        orm_mode = True

    @validator('api_key_masked')
    def mask_api_key(cls, v, values):
        """掩码处理API密钥，只显示前4位和后4位"""
        if not v:
            return None
        if len(v) <= 8:
            return "****"
        return v[:4] + "****" + v[-4:]


# 简化的模型列表响应
class ModelSummary(BaseModel):
    """用于列表展示的简化模型响应Schema"""
    id: UUID
    name: str
    display_name: str
    model_type: str
    model_name: str
    is_active: bool
    is_custom: bool
    total_requests: int = 0
    input_price: float
    output_price: float

    class Config:
        orm_mode = True


# 模型列表响应
class ModelListResponse(BaseModel):
    """模型列表响应Schema"""
    total: int = Field(..., description="总模型数")
    models: List[ModelSummary] = Field(..., description="模型列表")