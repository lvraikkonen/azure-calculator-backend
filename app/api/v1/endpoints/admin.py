from typing import Annotated, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.ldap_utils import search_ldap_user_in_ad, format_ad_guid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from ldap3 import Server, Connection, core
from app.schemas.user import LDAPTestRequest, LDAPTestResponse

from app.api.deps import get_current_active_superuser
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.user import (
    LDAPUserCreate,
    LDAPUserCreateResponse,
    LDAPUserSearchRequest, LDAPUserSearchResponse,
    SimplifiedLDAPUserCreate,
    LDAPTestRequest, LDAPTestResponse
)
from app.services.user import get_user_by_username, get_user_by_ldap_guid

settings = get_settings()
router = APIRouter()
logger = get_logger(__name__)


@router.post("/test-ldap-user", response_model=LDAPTestResponse)
async def test_ldap_user_connection(
    request: LDAPTestRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_superuser)]
):
    """使用普通域账号测试LDAP连通性"""
    try:
        # 构造用户PrincipalName
        user_principal = f"{request.username}@{settings.LDAP_DOMAIN}"
        
        # 直接绑定测试
        with Connection(
            Server(settings.LDAP_SERVER),
            user=user_principal,
            password=request.password,
            auto_bind=True
        ) as conn:
            return {
                "is_success": conn.bound,
                "message": "验证成功" if conn.bound else "验证失败"
            }
            
    except core.exceptions.LDAPBindError:
        return {"is_success": False, "message": "账号或密码错误"}
    except Exception as e:
        logger.error(f"LDAP测试异常: {str(e)}")
        return {"is_success": False, "message": f"连接失败: {str(e)}"}

@router.post("/search-ldap-user", response_model=LDAPUserSearchResponse)
async def search_ldap_user(
    request: LDAPUserSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_active_superuser)]
):
    """通过用户名查询LDAP用户信息"""
    try:
        # 调用工具函数
        ldap_data = search_ldap_user_in_ad(
            username=request.username,
            settings=get_settings()
        )
        
        return {
            "username": ldap_data["username"],
            "full_name": ldap_data["displayname"],  # 字段名修改
            "email": ldap_data["email"],
            "ldap_guid": format_ad_guid(ldap_data["guid"]),  # 使用统一的GUID格式化方法
            "exists_in_local": await get_user_by_username(db, request.username) is not None
        }
    except HTTPException as e:
        raise e  # 直接传递工具函数抛出的HTTP异常

@router.post("/ldap-users", response_model=LDAPUserCreateResponse)
async def create_ldap_user(
    user_in: Union[LDAPUserCreate, SimplifiedLDAPUserCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_active_superuser)],
) -> Any:
    """创建LDAP用户（支持自动获取GUID）"""
    logger.debug(f"开始创建LDAP用户，操作者: {current_user.username}，模式: {'简化' if isinstance(user_in, SimplifiedLDAPUserCreate) else '完整'}")

    try:
        # ================== 简化模式处理 ==================
        if isinstance(user_in, SimplifiedLDAPUserCreate):
            # 调用工具函数验证AD用户存在性
            ldap_data = search_ldap_user_in_ad(
                username=user_in.username,
                settings=get_settings()
            )
                
            # 检查本地用户是否存在
            if await get_user_by_username(db, user_in.username):
                logger.warning(f"用户已存在: {user_in.username}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户已存在"
                )

            # 转换为完整请求
            user_in = LDAPUserCreate(
                username=ldap_data["username"],
                displayname=ldap_data["displayname"],
                email=ldap_data["email"],
                ldap_guid=format_ad_guid(ldap_data["guid"]),
                groups=user_in.groups
            )

        # ================== 通用校验逻辑 ==================
        # 检查用户名冲突
        if await get_user_by_username(db, user_in.username):
            logger.warning(f"用户名冲突: {user_in.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被占用"
            )

        # 检查GUID重复
        if await get_user_by_ldap_guid(db, user_in.ldap_guid):
            logger.warning(f"LDAP GUID重复: {user_in.ldap_guid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该LDAP用户已注册"
            )

        # ================== 创建用户 ==================
        try:
            user = UserModel(
                username=user_in.username,
                full_name=user_in.displayname,
                email=user_in.email,
                ldap_guid=user_in.ldap_guid,
                auth_source="ldap",
                groups=user_in.groups,
                is_active=True
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"LDAP用户创建成功: {user_in.username}")
            return user
            
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"数据库唯一性冲突: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户数据冲突，请检查用户名或GUID"
            )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"创建LDAP用户失败 | 操作者: {current_user.username} | 错误类型: {type(e).__name__} | 详情: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误"
        )