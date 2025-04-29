# app/models/model_usage_hourly.py
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Float, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ModelUsageHourly(Base):
    """模型使用统计表，按小时聚合"""
    __tablename__ = "model_usage_hourly"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hour_timestamp = Column(DateTime, primary_key=True, nullable=False,
                            comment="小时时间戳 (YYYY-MM-DD HH:00:00)")
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
    min_response_time = Column(Float, nullable=True, comment="最小响应时间(ms)")
    max_response_time = Column(Float, nullable=True, comment="最大响应时间(ms)")

    # 错误统计
    error_types = Column(String(500), nullable=True, comment="主要错误类型(逗号分隔)")

    # 元数据
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 优化索引
    __table_args__ = (
        Index('idx_hourly_model_hour', model_id, hour_timestamp),
        {'postgresql_partition_by': 'RANGE (hour_timestamp)'}
    )