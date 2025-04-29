# app/models/model_usage_daily.py
import uuid
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelUsageDaily(Base):
    """模型使用统计表，按日聚合"""
    __tablename__ = "model_usage_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usage_date = Column(Date, primary_key=True, nullable=False, comment="统计日期")
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False)

    # 使用计数
    request_count = Column(Integer, default=0, comment="请求总数")
    success_count = Column(Integer, default=0, comment="成功请求数")
    error_count = Column(Integer, default=0, comment="错误请求数")

    # Token统计
    input_tokens = Column(Integer, default=0, comment="输入token总数")
    output_tokens = Column(Integer, default=0, comment="输出token总数")

    # 性能统计
    avg_response_time = Column(Float, nullable=True, comment="平均响应时间(ms)")
    avg_first_token_time = Column(Float, nullable=True, comment="平均首个token响应时间(ms)")
    max_response_time = Column(Float, nullable=True, comment="最大响应时间(ms)")
    p95_response_time = Column(Float, nullable=True, comment="P95响应时间(ms)")

    # 用户统计
    unique_users = Column(Integer, default=0, comment="唯一用户数")
    user_distribution = Column(JSONB, nullable=True, comment="用户分布统计")

    # 成本统计
    estimated_cost = Column(Float, default=0.0, comment="估计成本")

    # 元数据
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 优化索引
    __table_args__ = (
        Index('idx_usage_model_date', model_id, usage_date),
        {'postgresql_partition_by': 'RANGE (usage_date)'}
    )