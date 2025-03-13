from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.user import user_role


class Role(Base):
    """角色数据库模型"""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关系
    users = relationship("User", secondary=user_role, back_populates="roles")
    
    def __repr__(self):
        return f"<Role {self.name}>"
