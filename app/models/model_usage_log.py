# app/models/model_usage_log.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelUsageLog(Base):
    """模型使用日志表，采样记录详细调用"""
    __tablename__ = "model_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, primary_key=True, nullable=False, default=datetime.utcnow, comment="请求时间")
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)

    # 请求信息 - 注意不再添加唯一约束
    request_id = Column(String(64), nullable=True, comment="请求ID")

    # 用量统计
    input_tokens = Column(Integer, default=0, comment="输入token数")
    output_tokens = Column(Integer, default=0, comment="输出token数")

    # 性能统计
    response_time = Column(Float, nullable=True, comment="响应时间(ms)")
    first_token_time = Column(Float, nullable=True, comment="首个token响应时间(ms)")

    # 状态信息
    status = Column(String(20), nullable=False, comment="请求状态: success, failed")
    error_type = Column(String(50), nullable=True, comment="错误类型")
    error_message = Column(String(500), nullable=True, comment="错误消息")

    # 标记字段
    is_sampled = Column(Boolean, default=False, comment="是否为采样记录")
    is_error = Column(Boolean, default=False, comment="是否为错误记录")

    # 可选的请求上下文 (只在debug模式或特定记录保存)
    request_context = Column(JSONB, nullable=True, comment="请求上下文(仅保存部分)")

    # 优化索引并使用表分区
    __table_args__ = (
        Index('idx_usage_log_timestamp', timestamp),
        Index('idx_usage_log_model_status', model_id, status),
        Index('idx_usage_log_user', user_id),
        {'postgresql_partition_by': 'RANGE (timestamp)'}
    )