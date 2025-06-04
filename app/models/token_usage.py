# app/models/token_usage.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TokenUsageStats(BaseModel):
    """Token使用统计数据模型"""
    input_tokens: int = Field(default=0, description="输入的token数量")
    output_tokens: int = Field(default=0, description="输出的token数量")
    input_cost: float = Field(default=0.0, description="输入token的成本")
    output_cost: float = Field(default=0.0, description="输出token的成本")

    @property
    def total_tokens(self) -> int:
        """总token数"""
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        """总成本"""
        return self.input_cost + self.output_cost

    def add_usage(self, other: 'TokenUsageStats') -> 'TokenUsageStats':
        """合并另一个使用统计"""
        return TokenUsageStats(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            input_cost=self.input_cost + other.input_cost,
            output_cost=self.output_cost + other.output_cost
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost
        }


class TokenUsageEvent(BaseModel):
    """Token使用事件模型"""
    model_id: str = Field(..., description="模型ID")
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(..., description="模型类型")
    user_id: Optional[str] = Field(None, description="用户ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    request_id: Optional[str] = Field(None, description="请求ID")
    
    # Token统计
    input_tokens: int = Field(default=0, description="输入token数")
    output_tokens: int = Field(default=0, description="输出token数")
    
    # 成本信息
    input_cost: float = Field(default=0.0, description="输入成本")
    output_cost: float = Field(default=0.0, description="输出成本")
    
    # 性能信息
    response_time: Optional[float] = Field(None, description="响应时间(ms)")
    first_token_time: Optional[float] = Field(None, description="首个token时间(ms)")
    
    # 时间戳
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间")
    
    # 操作信息
    operation_name: str = Field(default="chat", description="操作名称")
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")

    @property
    def total_tokens(self) -> int:
        """总token数"""
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        """总成本"""
        return self.input_cost + self.output_cost

    def to_usage_stats(self) -> TokenUsageStats:
        """转换为使用统计"""
        return TokenUsageStats(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            input_cost=self.input_cost,
            output_cost=self.output_cost
        )


class TokenBudgetInfo(BaseModel):
    """Token预算信息"""
    daily_limit: Optional[int] = Field(None, description="每日token限制")
    monthly_limit: Optional[int] = Field(None, description="每月token限制")
    daily_used: int = Field(default=0, description="今日已使用token")
    monthly_used: int = Field(default=0, description="本月已使用token")
    
    daily_cost_limit: Optional[float] = Field(None, description="每日成本限制")
    monthly_cost_limit: Optional[float] = Field(None, description="每月成本限制")
    daily_cost_used: float = Field(default=0.0, description="今日已使用成本")
    monthly_cost_used: float = Field(default=0.0, description="本月已使用成本")

    @property
    def daily_tokens_remaining(self) -> Optional[int]:
        """剩余每日token"""
        if self.daily_limit is None:
            return None
        return max(0, self.daily_limit - self.daily_used)

    @property
    def monthly_tokens_remaining(self) -> Optional[int]:
        """剩余每月token"""
        if self.monthly_limit is None:
            return None
        return max(0, self.monthly_limit - self.monthly_used)

    @property
    def daily_cost_remaining(self) -> Optional[float]:
        """剩余每日成本"""
        if self.daily_cost_limit is None:
            return None
        return max(0.0, self.daily_cost_limit - self.daily_cost_used)

    @property
    def monthly_cost_remaining(self) -> Optional[float]:
        """剩余每月成本"""
        if self.monthly_cost_limit is None:
            return None
        return max(0.0, self.monthly_cost_limit - self.monthly_cost_used)

    def is_over_daily_limit(self) -> bool:
        """是否超过每日限制"""
        token_over = self.daily_limit is not None and self.daily_used >= self.daily_limit
        cost_over = self.daily_cost_limit is not None and self.daily_cost_used >= self.daily_cost_limit
        return token_over or cost_over

    def is_over_monthly_limit(self) -> bool:
        """是否超过每月限制"""
        token_over = self.monthly_limit is not None and self.monthly_used >= self.monthly_limit
        cost_over = self.monthly_cost_limit is not None and self.monthly_cost_used >= self.monthly_cost_limit
        return token_over or cost_over

    def can_afford(self, estimated_tokens: int, estimated_cost: float) -> tuple[bool, str]:
        """检查是否可以承担预估的使用量"""
        # 检查每日限制
        if self.daily_limit is not None and (self.daily_used + estimated_tokens) > self.daily_limit:
            return False, f"超过每日token限制 ({self.daily_limit})"
        
        if self.daily_cost_limit is not None and (self.daily_cost_used + estimated_cost) > self.daily_cost_limit:
            return False, f"超过每日成本限制 (${self.daily_cost_limit:.2f})"
        
        # 检查每月限制
        if self.monthly_limit is not None and (self.monthly_used + estimated_tokens) > self.monthly_limit:
            return False, f"超过每月token限制 ({self.monthly_limit})"
        
        if self.monthly_cost_limit is not None and (self.monthly_cost_used + estimated_cost) > self.monthly_cost_limit:
            return False, f"超过每月成本限制 (${self.monthly_cost_limit:.2f})"
        
        return True, "预算检查通过"
