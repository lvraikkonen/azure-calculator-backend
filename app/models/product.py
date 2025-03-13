import uuid
from sqlalchemy import Column, String, Float, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class Product(Base):
    """Azure产品模型"""
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_code = Column(String(50), nullable=False, unique=True, index=True)  # 如 'vm-basic'
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    price_unit = Column(String(20), nullable=False)  # 如 'USD/小时', 'USD/GB/月'
    category = Column(String(50), nullable=False, index=True)