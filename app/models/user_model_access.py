# app/models/user_model_access.py
import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Integer, Index, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class UserModelAccess(Base):
    """用户模型访问权限表"""
    __tablename__ = "user_model_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False)

    # 权限设置
    access_level = Column(String(20), default="read", comment="访问级别: read, write, admin")
    has_access = Column(Boolean, default=True, comment="是否有访问权限")
    daily_quota = Column(Integer, nullable=True, comment="每日请求限制")
    token_quota = Column(Integer, nullable=True, comment="每日token限制")

    # 额外配置
    custom_settings = Column(JSONB, nullable=True, comment="用户自定义模型设置")

    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 优化索引设计
    __table_args__ = (
        Index('idx_model_access_user', user_id),
        Index('idx_model_access_model', model_id),
        Index('idx_model_access_user_model', user_id, model_id, unique=True),
    )