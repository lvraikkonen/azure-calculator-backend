from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_product_service, get_db
from app.models.user import User
from app.schemas.product import Product, ProductCreate, ProductUpdate
from app.services.product import ProductService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/", response_model=List[Product])
async def list_products(
    category: Optional[str] = None,
    product_service: ProductService = Depends(get_product_service)
):
    """
    获取产品列表，可选按分类过滤
    """
    if category:
        return await product_service.get_products_by_category(category)
    else:
        return await product_service.get_all_products()

@router.get("/{product_code}", response_model=Product)
async def get_product(
    product_code: str,
    product_service: ProductService = Depends(get_product_service)
):
    """
    根据产品代码获取产品详情
    """
    product = await product_service.get_product_by_id(product_code)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="产品不存在"
        )
    return product

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    """
    创建新产品（仅管理员）
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    try:
        return await product_service.create_product(db, product)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建产品失败: {str(e)}"
        )

@router.put("/{product_code}", response_model=Product)
async def update_product(
    product_code: str,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    """
    更新产品信息（仅管理员）
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    product = await product_service.update_product(db, product_code, product_update)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="产品不存在"
        )
    return product