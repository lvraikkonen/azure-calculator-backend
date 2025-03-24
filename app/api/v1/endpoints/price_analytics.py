from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user, get_product_service
from app.services.product import ProductService
from app.models.user import User

router = APIRouter()

@router.get("/trends/{product_code}")
async def get_price_trends(
    product_code: str,
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取产品价格趋势数据
    
    Args:
        product_code: 产品代码
        
    Returns:
        价格趋势数据点列表
    """
    # 验证产品存在
    product = await product_service.get_product_by_id(product_code)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="产品不存在"
        )
        
    # 获取价格趋势
    trends = await product_service.get_price_trends(product_code)
    
    return {
        "product": product,
        "trends": trends
    }

@router.get("/stats")
async def get_product_stats(
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取产品数据统计信息
    
    Returns:
        产品统计信息
    """
    if not product_service.mongodb_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB服务未初始化"
        )
        
    stats = await product_service.mongodb_service.get_stats()
    
    return stats