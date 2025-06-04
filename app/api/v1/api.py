from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, admin, roles
from app.api.v1.endpoints import chat, products
from app.api.v1.endpoints import rag, model_performance, model_management, performance_scheduler
from app.api.v1.endpoints import token_billing
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(model_management.router, prefix="/models-management", tags=["模型管理"])
api_router.include_router(model_performance.router, prefix="/models-management", tags=["模型性能测试"])
# api_router.include_router(performance_scheduler.router, prefix="/models", tags=["性能测试调度"])
api_router.include_router(token_billing.router, prefix="/token-billing", tags=["Token计费"])

# 健康检查端点
@api_router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint
    """
    return {"status": "healthy"}