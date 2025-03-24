from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, admin, roles
from app.api.v1.endpoints import chat, products, price_analytics
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(price_analytics.router, prefix="/price-analytics", tags=["price-analytics"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])

# 健康检查端点
@api_router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint
    """
    return {"status": "healthy"}