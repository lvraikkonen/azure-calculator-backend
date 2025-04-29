# app/models/user_usage_stats.py
import uuid
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class UserUsageStats(Base):
    """用户使用统计表，按日聚合"""
    __tablename__ = "user_usage_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usage_date = Column(Date, primary_key=True, nullable=False, comment="统计日期")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 汇总统计
    total_requests = Column(Integer, default=0, comment="总请求数")
    total_input_tokens = Column(Integer, default=0, comment="总输入token数")
    total_output_tokens = Column(Integer, default=0, comment="总输出token数")

    # 模型使用分布
    model_distribution = Column(UUID(as_uuid=True), nullable=True, comment="最常用模型ID")

    # 成本统计
    total_cost = Column(Float, default=0.0, comment="总成本")

    # 元数据
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 优化索引
    __table_args__ = (
        Index('idx_user_usage_date', user_id, usage_date),
        {'postgresql_partition_by': 'RANGE (usage_date)'}
    )