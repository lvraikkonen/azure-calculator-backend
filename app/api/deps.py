from typing import Annotated, Callable, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.user import UserService
from app.services.role import RoleService
from app.services.product import ProductService
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import ModelType, BaseLLMService, ContextProvider
from app.services.llm.context_providers import ProductContextProvider
from app.services.intent_analysis import IntentAnalysisService
from app.services.conversation import ConversationService
from app.services.model_management.model_configuration_service import ModelConfigurationService
from app.services.model_management.factory import ModelManagementServiceFactory
from app.rag.services.hybrid_rag_service import HybridRAGService
from app.rag.services.rag_factory import create_rag_service

settings = get_settings()
logger = get_logger(__name__)

# 创建模型管理服务工厂（单例）
model_management_factory = ModelManagementServiceFactory()

# 全局LLM工厂实例（将在get_llm_factory中动态注入模型配置服务）
llm_factory = None

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Dependency to validate the token and get the current user
    
    Args:
        db: Database session
        token: JWT token from the request
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Extract username from token
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # Create token data object
        token_data = TokenPayload(sub=username)
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.username == token_data.sub)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User not found: {token_data.sub}")
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

def has_any_role(roles: List[str]) -> Callable:
    """
    创建一个依赖项，检查当前用户是否拥有任一所需角色
    
    Args:
        roles: 所需角色列表，用户拥有其中任一角色即可
        
    Returns:
        返回当前用户（如果用户拥有所需角色之一）的依赖函数
        
    Raises:
        HTTPException: 如果用户没有任何所需角色
    """
    async def check_roles(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        # 超级管理员始终拥有所有权限
        if current_user.is_superuser:
            return current_user
            
        # 检查用户是否拥有角色
        if not current_user.groups:
            logger.warning(f"用户 {current_user.username} 没有分配角色")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户没有所需的权限",
            )
            
        # 解析用户的角色
        user_roles = [r.strip() for r in current_user.groups.split(",")]
        
        # 检查用户是否拥有任一所需角色
        if not any(role in user_roles for role in roles):
            logger.warning(
                f"用户 {current_user.username} 没有所需角色: {roles}. "
                f"用户角色: {user_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户没有所需的权限",
            )
            
        return current_user
        
    return check_roles

async def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    """
    获取用户服务实例
    """
    return UserService(db)

async def get_role_service(
    db: AsyncSession = Depends(get_db)
) -> RoleService:
    """
    获取角色服务实例
    """
    return RoleService(db)

async def get_product_service(
    db: AsyncSession = Depends(get_db)
) -> ProductService:
    """
    获取产品服务实例
    """
    return ProductService(db)

async def get_llm_factory(db: AsyncSession = Depends(get_db)) -> LLMServiceFactory:
    """
    获取LLM服务工厂实例，动态注入模型配置服务
    """
    global llm_factory

    # 如果工厂实例不存在，创建一个新的
    if llm_factory is None:
        logger.info("开始创建LLM服务工厂...")

        try:
            logger.debug(f"数据库会话类型: {type(db)}")
            logger.debug(f"模型管理工厂类型: {type(model_management_factory)}")

            # 创建模型配置服务
            logger.debug("正在创建模型配置服务...")
            model_config_service = model_management_factory.create_service(db)
            logger.info(f"模型配置服务创建成功: {type(model_config_service).__name__}")

            # 创建性能测试服务
            logger.debug("正在创建性能测试服务...")
            from app.services.model_management.model_performance_service import ModelPerformanceService
            performance_service = ModelPerformanceService(db)
            logger.info(f"性能测试服务创建成功: {type(performance_service).__name__}")

            # 创建带有模型配置服务和性能测试服务的LLM工厂
            logger.debug("正在创建带配置服务和性能服务的LLM工厂...")
            llm_factory = LLMServiceFactory(
                model_config_service=model_config_service,
                performance_service=performance_service
            )

            logger.info("✅ LLM服务工厂已创建并注入模型配置服务和性能测试服务")

        except Exception as e:
            logger.error(f"❌ 创建模型配置服务失败: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")

            logger.warning("回退到无配置服务的LLM工厂")
            # 回退到无配置服务的工厂
            llm_factory = LLMServiceFactory()

    return llm_factory

async def get_llm_service(
        product_service: ProductService = Depends(get_product_service),
        llm_factory_instance: LLMServiceFactory = Depends(get_llm_factory)
) -> BaseLLMService:
    """
    获取默认LLM服务实例，使用ProductContextProvider
    """
    # 创建产品上下文提供者
    context_provider = ProductContextProvider(product_service)

    # 获取默认服务
    service = await llm_factory_instance.get_service()

    # 为了保持兼容，设置一个内部属性存储上下文提供者
    setattr(service, "_context_providers", [context_provider])

    return service

async def get_intent_analysis_service(
        llm_factory_instance: LLMServiceFactory = Depends(get_llm_factory)
) -> IntentAnalysisService:
    """
    获取意图分析服务实例

    Args:
        llm_factory_instance: LLM服务工厂实例

    Returns:
        IntentAnalysisService: 意图分析服务实例
    """
    return IntentAnalysisService(llm_factory_instance)

async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
    llm_factory_instance: LLMServiceFactory = Depends(get_llm_factory),
    product_service: ProductService = Depends(get_product_service)
) -> ConversationService:
    """
    获取对话服务实例
    """
    return ConversationService(db, llm_factory_instance, product_service)

async def get_model_service(
        model_type: ModelType,
        model_name: Optional[str] = None,
        context_providers: List[ContextProvider] = None,
        llm_factory_instance: LLMServiceFactory = Depends(get_llm_factory)
) -> BaseLLMService:
    """
    获取指定类型的LLM服务实例，支持提供上下文提供者

    Args:
        model_type: 模型类型枚举
        model_name: 具体模型名称（可选）
        context_providers: 上下文提供者列表
        llm_factory_instance: LLM服务工厂

    Returns:
        BaseLLMService: 指定类型的LLM服务实例
    """
    service = await llm_factory_instance.get_service(model_type, model_name)

    # 如果提供了上下文提供者，保存到服务实例中
    if context_providers:
        setattr(service, "_context_providers", context_providers)

    return service

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    获取当前活跃的超级用户
    """
    if not user_service.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    if not user_service.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def has_required_role(role: str):
    """
    检查用户是否具有指定角色
    
    这是一个依赖工厂函数，返回实际的依赖函数
    """
    async def _has_role(
        current_user: User = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service),
    ) -> User:
        if not user_service.is_active(current_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # 超级用户拥有所有权限
        if user_service.is_superuser(current_user):
            return current_user
            
        # 检查用户是否有指定角色
        if not current_user.groups or role not in current_user.groups.split(','):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
            
        return current_user
    
    return _has_role

async def get_rag_service(
    llm_service: BaseLLMService = Depends(get_llm_service)
) -> HybridRAGService:
    """获取RAG服务实例"""
    return await create_rag_service(llm_service)