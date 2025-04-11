import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Feedback(Base):
    """消息反馈模型"""
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    feedback_type = Column(String(20), nullable=False)  # 'like', 'dislike', 'helpful', 'not_helpful'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(tz=timezone.utc))
    
    # 关系
    message = relationship("Message", back_populates="feedback")