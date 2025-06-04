from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_superuser, get_role_service
from app.core.logging import async_log_user_operation, get_logger
from app.models.user import User
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate, Role as RoleSchema
from app.services.role import RoleService

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[RoleSchema])
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    获取所有角色列表（管理员权限）
    """
    roles = await role_service.get_roles(skip=skip, limit=limit)
    
    await async_log_user_operation(
        user=current_user.username,
        action="获取角色列表",
        details={"skip": skip, "limit": limit},
    )
    
    return roles


@router.get("/{role_id}", response_model=RoleSchema)
async def get_role(
    role_id: int,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    获取指定角色（管理员权限）
    """
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    return role


@router.post("/", response_model=RoleSchema, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    创建新角色（管理员权限）
    """
    try:
        role = await role_service.create_role(role_in)
        
        await async_log_user_operation(
            user=current_user.username,
            action="创建角色",
            details={"role_name": role.name},
        )
        
        return role
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{role_id}", response_model=RoleSchema)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    更新角色（管理员权限）
    """
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    try:
        updated_role = await role_service.update_role(role, role_in)
        
        await async_log_user_operation(
            user=current_user.username,
            action="更新角色",
            details={"role_id": role_id, "role_name": role.name},
        )
        
        return updated_role
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> None:  # 明确返回None
    """
    删除角色（管理员权限）
    """
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    # 检查是否有用户关联此角色
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法删除已分配给用户的角色"
        )
    
    await role_service.delete_role(role)
    
    await async_log_user_operation(
        user=current_user.username,
        action="删除角色",
        details={"role_id": role_id, "role_name": role.name},
    )

@router.post("/{role_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    role_id: int,
    user_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> None:  # 明确返回None
    """
    为用户分配角色（管理员权限）
    """
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    success = await role_service.assign_role_to_user(role, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分配角色失败，用户可能不存在"
        )

    await async_log_user_operation(
        user=current_user.username,
        action="分配角色给用户",
        details={"role_id": role_id, "role_name": role.name, "user_id": str(user_id)},
    )


@router.delete("/{role_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    role_id: int,
    user_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    current_user: User = Depends(get_current_active_superuser)
) -> None:  # 明确返回None
    """
    从用户移除角色（管理员权限）
    """
    role = await role_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    success = await role_service.remove_role_from_user(role, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="移除角色失败，用户可能不存在或没有此角色"
        )

    await async_log_user_operation(
        user=current_user.username,
        action="从用户移除角色",
        details={"role_id": role_id, "role_name": role.name, "user_id": str(user_id)},
    )