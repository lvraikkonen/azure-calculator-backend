import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base
from app.models.association import user_role


class User(Base):
    """
    SQLAlchemy User model
    
    Stores user information for authentication and authorization
    """
    __tablename__ = "users"
    
    __table_args__ = (
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('ldap_guid', name='uq_user_ldap_guid'),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    
    # Authentication
    hashed_password = Column(String(200), nullable=True)
    auth_source = Column(String(20), default='local', comment='认证来源: ldap/local')
    ldap_guid = Column(String(100), unique=True, nullable=True, comment='LDAP用户的ObjectGUID')
    
    # Authorization
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    groups = Column(String(255), nullable=True, comment="逗号分隔的用户角色列表，例如: admin,editor,viewer")
    
    # Timestamps
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    roles = relationship("Role", secondary=user_role, back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.username}>"