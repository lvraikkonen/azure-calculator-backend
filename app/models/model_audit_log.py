# app/models/model_audit_log.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelAuditLog(Base):
    """模型审计日志表，记录配置变更"""
    __tablename__ = "model_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False)

    # 操作信息
    action = Column(String(50), nullable=False, comment="执行的操作: create, update, delete, activate, deactivate")
    entity_type = Column(String(50), default="model", comment="实体类型")

    # 变更详情 - 针对不同类型变更存储不同信息
    changes_summary = Column(Text, nullable=True, comment="变更摘要")
    changes_detail = Column(JSONB, nullable=True, comment="变更详情JSON")

    # 操作元数据
    action_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(50), nullable=True, comment="操作来源IP")

    # 优化索引并考虑归档策略
    __table_args__ = (
        Index('idx_audit_model_date', model_id, action_date),
        Index('idx_audit_action_date', action, action_date),
    )