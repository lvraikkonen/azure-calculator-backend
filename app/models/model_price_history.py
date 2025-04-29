# app/models/model_price_history.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelPriceHistory(Base):
    """模型价格历史记录表，仅在价格变更时记录"""
    __tablename__ = "model_price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False,
                      index=True)

    # 价格信息
    input_price = Column(Float, nullable=False, comment="输入token价格")
    output_price = Column(Float, nullable=False, comment="输出token价格")
    currency = Column(String(10), default="USD", comment="货币单位")

    # 变更信息
    effective_date = Column(DateTime, nullable=False, comment="生效日期")
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 索引优化
    __table_args__ = (
        Index('idx_model_id_date', model_id, effective_date),
    )