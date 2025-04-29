# app/models/model_configuration.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelConfiguration(Base):
    """模型配置表，存储所有LLM模型的基本配置"""
    __tablename__ = "model_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="模型唯一名称")
    display_name = Column(String(100), nullable=False, comment="模型显示名称")
    description = Column(String(500), nullable=True, comment="模型描述")

    # 模型类型和基础配置
    model_type = Column(String(50), nullable=False, index=True, comment="模型类型: openai, deepseek, anthropic等")
    model_name = Column(String(100), nullable=False, comment="具体模型名称: gpt-4, claude-3等")
    api_key = Column(String(500), nullable=True, comment="API密钥(加密存储)")
    base_url = Column(String(255), nullable=True, comment="API基础URL")
    parameters = Column(JSONB, nullable=True, comment="附加参数JSON")

    # 价格信息 (合并自模型价格表，简化设计)
    input_price = Column(Float, default=0.0, comment="输入token价格(单位:百万tokens)")
    output_price = Column(Float, default=0.0, comment="输出token价格(单位:百万tokens)")
    currency = Column(String(10), default="USD", comment="货币单位")

    # 状态和能力
    is_active = Column(Boolean, default=True, comment="模型是否激活")
    is_custom = Column(Boolean, default=False, comment="是否自定义模型")
    is_visible = Column(Boolean, default=True, comment="是否在用户界面可见")
    capabilities = Column(JSONB, nullable=True, comment="模型能力列表")
    max_tokens = Column(Integer, nullable=True, comment="最大token限制")

    # 系统限制
    rate_limit = Column(Integer, nullable=True, comment="每分钟最大请求次数")
    user_rate_limit = Column(Integer, nullable=True, comment="每用户每分钟最大请求次数")
    concurrency_limit = Column(Integer, nullable=True, comment="并发请求限制")

    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 相关统计 (冗余字段, 定期更新，提高查询效率)
    total_requests = Column(Integer, default=0, comment="总请求数")
    total_tokens = Column(Integer, default=0, comment="总tokens数")
    avg_response_time = Column(Float, default=0.0, comment="平均响应时间(ms)")
    last_used_at = Column(DateTime, nullable=True, comment="最后使用时间")

    # 索引优化
    __table_args__ = (
        Index('idx_model_type_active', model_type, is_active),
    )