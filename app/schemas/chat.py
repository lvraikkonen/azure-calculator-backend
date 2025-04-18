from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from app.core.config import get_settings

settings = get_settings()


class MessageBase(BaseModel):
    """消息基础模型"""
    content: str = Field(..., min_length=1, description="消息内容")


class MessageCreate(MessageBase):
    """创建消息请求模型"""
    conversation_id: Optional[UUID] = Field(None, description="会话ID，如果为None则创建新会话")
    context: Optional[Dict[str, Any]] = Field(default={}, description="消息上下文，如产品数据等")
    model_type: Optional[str] = None  # 添加直接的模型类型字段
    model_name: Optional[str] = None  # 添加直接的模型名称字段
    use_reasoning: Optional[bool] = False  # 是否使用推理能力

    def __init__(self, **data):
        super().__init__(**data)
        # 将模型选择参数添加到context中确保兼容性
        if self.model_type and "model_type" not in self.context:
            self.context["model_type"] = self.model_type
        if self.model_name and "model_name" not in self.context:
            self.context["model_name"] = self.model_name
        if self.use_reasoning:
            self.context["reasoning"] = True
            # 如果用户请求推理但没指定模型，使用默认推理模型
            if not self.model_name:
                self.context["model_name"] = settings.DEEPSEEK_R1_MODEL
                self.context["model_type"] = "deepseek"


class Recommendation(BaseModel):
    """产品推荐模型"""
    name: str = Field(..., description="推荐方案名称")
    description: str = Field(..., description="推荐方案描述")
    products: List[Dict[str, Any]] = Field(..., description="推荐产品列表")


class MessageResponse(MessageBase):
    """消息响应模型"""
    id: Optional[UUID] = Field(default_factory=uuid4, description="消息ID")
    conversation_id: Optional[UUID] = Field(None, description="会话ID")
    sender: str = Field(..., description="发送者，'user' 或 'ai'")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="消息时间戳")
    suggestions: Optional[List[str]] = Field(default=[], description="下一步建议列表")
    recommendation: Optional[Recommendation] = Field(None, description="产品推荐")
    thinking: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
                "content": "我推荐以下Azure服务组合...",
                "sender": "ai",
                "timestamp": "2025-03-01T12:00:00",
                "suggestions": [
                    "这些服务的总价格是多少?",
                    "有更便宜的替代方案吗?"
                ],
                "recommendation": {
                    "name": "基础Web应用方案",
                    "description": "适合小型Web应用的基础架构",
                    "products": [
                        {"id": "vm-basic", "name": "虚拟机(基础)", "quantity": 2},
                        {"id": "storage-std", "name": "标准存储", "quantity": 100}
                    ]
                }
            }
        }


class ConversationBase(BaseModel):
    """会话基础模型"""
    title: Optional[str] = Field(None, description="会话标题")


class ConversationCreate(ConversationBase):
    """创建会话请求模型"""
    pass


class ConversationResponse(ConversationBase):
    """会话响应模型"""
    id: UUID = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    messages: List[MessageResponse] = Field(default=[], description="会话消息列表")


class ConversationSummary(ConversationBase):
    """会话摘要模型"""
    id: UUID = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    message_count: int = Field(..., description="消息数量")
    last_message: Optional[str] = Field(None, description="最后一条消息内容")


class FeedbackCreate(BaseModel):
    """反馈请求模型"""
    message_id: UUID = Field(..., description="消息ID")
    feedback_type: str = Field(..., description="反馈类型，例如 'like' 或 'dislike'")
    comment: Optional[str] = Field(None, description="反馈详情")

    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        allowed_types = ['like', 'dislike', 'helpful', 'not_helpful']
        if v not in allowed_types:
            raise ValueError(f"反馈类型必须是以下之一: {', '.join(allowed_types)}")
        return v


class FeedbackResponse(FeedbackCreate):
    """反馈响应模型"""
    id: UUID = Field(..., description="反馈ID")
    created_at: datetime = Field(..., description="创建时间")


class ModelInfo(BaseModel):
    """模型信息模式"""
    model_type: str
    model_name: str
    display_name: str
    description: str
    supports_reasoning: bool
    is_default: bool