from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class ProductBase(BaseModel):
    """产品基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: float = Field(..., ge=0, description="产品价格")
    price_unit: str = Field(..., min_length=1, max_length=20, description="价格单位")
    category: str = Field(..., min_length=1, max_length=50, description="产品分类")


class ProductCreate(ProductBase):
    """创建产品请求模型"""
    product_code: str = Field(..., min_length=1, max_length=50, description="产品代码")


class ProductUpdate(BaseModel):
    """更新产品请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: Optional[float] = Field(None, ge=0, description="产品价格")
    price_unit: Optional[str] = Field(None, min_length=1, max_length=20, description="价格单位")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="产品分类")


class ProductInDB(ProductBase):
    """数据库中的产品模型"""
    id: UUID
    product_code: str


class Product(ProductInDB):
    """产品响应模型"""
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "product_code": "vm-basic",
                "name": "虚拟机(基础)",
                "description": "基础型虚拟机，适合开发测试和轻量级应用",
                "price": 0.0575,
                "price_unit": "USD/小时",
                "category": "计算"
            }
        }