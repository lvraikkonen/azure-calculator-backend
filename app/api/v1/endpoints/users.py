from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, has_required_role, get_user_service
from app.core.logging import async_log_user_operation, get_logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import UserService


router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[UserResponse])
async def read_users(
    user_service: UserService = Depends(get_user_service),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(has_required_role("admin")),
) -> Any:
    """
    获取用户列表
    """
    users = await user_service.get_users(skip=skip, limit=limit)
    
    await async_log_user_operation(
        user=current_user.username,
        action="获取用户列表",
        details={"skip": skip, "limit": limit},
    )
    
    return users


@router.post("/", response_model=UserResponse)
async def create_new_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    创建新用户（管理员权限）
    """
    # 检查用户名是否已存在
    user = await user_service.get_user_by_username(user_in.username)
    if user:
        logger.warning(f"尝试创建已存在的用户名: {user_in.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被占用",
        )
        
    # 检查邮箱是否已存在
    user = await user_service.get_user_by_email(user_in.email)
    if user:
        logger.warning(f"尝试创建已存在的邮箱: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被占用",
        )
    
    user = await user_service.create_user(user_in)
    
    await async_log_user_operation(
        user=current_user.username,
        action="创建用户",
        details={"username": user_in.username},
    )
    
    return user


@router.get("/me", response_model=UserResponse)
async def read_user_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取当前用户
    """
    # 从数据库中获取最新的用户信息
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_in: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    更新当前用户
    """
    # 不允许自己修改为管理员
    if user_in.is_superuser:
        user_in.is_superuser = None
    
    # 如果尝试修改邮箱，检查新邮箱是否已存在
    if user_in.email and user_in.email != current_user.email:
        user = await user_service.get_user_by_email(user_in.email)
        if user:
            logger.warning(f"尝试更新为已存在的邮箱: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被占用",
            )
    
    user = await user_service.update_user(current_user.id, user_in)
    
    await async_log_user_operation(
        user=current_user.username,
        action="更新个人信息",
        details={},
    )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_superuser),
) -> None:  # 明确返回None，而不是Any
    """
    删除用户（管理员权限）
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )
    
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败",
        )
    
    await async_log_user_operation(
        user=current_user.username,
        action="删除用户",
        details={"user_id": user_id, "username": user.username},
    )


# 添加获取单个用户功能
@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    通过ID获取用户
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # 非管理员只能查看自己
    if user.id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限",
        )
    
    return user