# app/models/model_performance_test.py
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base_class import Base


class ModelPerformanceTest(Base):
    """模型性能测试表"""
    __tablename__ = "model_performance_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_configurations.id", ondelete="CASCADE"), nullable=False)

    # 测试配置
    test_name = Column(String(100), nullable=False, comment="测试名称")
    test_type = Column(String(50), nullable=False, comment="测试类型: standard, long_context, etc.")
    rounds = Column(Integer, nullable=False, default=1, comment="测试轮数")

    # 测试状态
    status = Column(String(20), nullable=False, default="pending", comment="测试状态: pending, running, completed, failed, timeout, cancelled")

    # 测试结果摘要
    avg_response_time = Column(Float, nullable=True, comment="平均响应时间(ms)")
    avg_first_token_time = Column(Float, nullable=True, comment="平均首个token响应时间(ms)")
    avg_throughput = Column(Float, nullable=True, comment="平均吞吐量(tokens/sec)")
    success_rate = Column(Float, nullable=True, comment="成功率(%)")
    error_rate = Column(Float, nullable=True, comment="错误率(%)")

    # 额外的性能指标
    min_response_time = Column(Float, nullable=True, comment="最小响应时间(ms)")
    max_response_time = Column(Float, nullable=True, comment="最大响应时间(ms)")
    total_tokens = Column(Integer, nullable=True, comment="总token数")
    input_tokens = Column(Integer, nullable=True, comment="输入token数")
    output_tokens = Column(Integer, nullable=True, comment="输出token数")
    total_cost = Column(Float, nullable=True, comment="总成本")

    # 测试参数和详细结果
    test_params = Column(JSONB, nullable=True, comment="测试参数")
    detailed_results = Column(JSONB, nullable=True, comment="详细测试结果")

    # 元数据
    test_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    tested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 优化索引
    __table_args__ = (
        Index('idx_perf_test_model_date', model_id, test_date),
        Index('idx_perf_test_type', test_type),
    )