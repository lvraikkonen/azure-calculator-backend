from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


logger = get_logger(__name__)


async def get_role(db: AsyncSession, role_id: int) -> Optional[Role]:
    """
    通过ID获取角色
    
    Args:
        db: 数据库会话
        role_id: 角色ID
        
    Returns:
        Optional[Role]: 角色对象或None
    """
    stmt = select(Role).where(Role.id == role_id).options(joinedload(Role.users))
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    """
    通过名称获取角色
    
    Args:
        db: 数据库会话
        name: 角色名称
        
    Returns:
        Optional[Role]: 角色对象或None
    """
    stmt = select(Role).where(Role.name == name).options(joinedload(Role.users))
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_roles(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100
) -> List[Role]:
    """
    获取角色列表
    
    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数
        
    Returns:
        List[Role]: 角色列表
    """
    stmt = select(Role).options(joinedload(Role.users)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_role(db: AsyncSession, role_in: RoleCreate) -> Role:
    """
    创建新角色
    
    Args:
        db: 数据库会话
        role_in: 角色创建模式
        
    Returns:
        Role: 创建的角色对象
        
    Raises:
        ValueError: 如果角色名称已存在
    """
    # 检查角色名称是否已存在
    existing_role = await get_role_by_name(db, role_in.name)
    if existing_role:
        logger.warning(f"尝试创建已存在的角色: {role_in.name}")
        raise ValueError(f"角色名称已存在: {role_in.name}")
    
    # 创建角色对象
    role = Role(
        name=role_in.name,
        description=role_in.description,
    )
    
    # 保存到数据库
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    logger.info(f"创建新角色: {role.name}")
    return role


async def update_role(
    db: AsyncSession, 
    role: Role,
    role_in: Union[RoleUpdate, dict]
) -> Role:
    """
    更新角色
    
    Args:
        db: 数据库会话
        role: 要更新的角色对象
        role_in: 更新数据
        
    Returns:
        Role: 更新后的角色对象
        
    Raises:
        ValueError: 如果新角色名称已存在
    """
    # 将 role_in 转换为字典
    update_data = role_in if isinstance(role_in, dict) else role_in.model_dump(exclude_unset=True)
    
    # 检查名称是否变更且已存在
    if "name" in update_data and update_data["name"] != role.name:
        existing_role = await get_role_by_name(db, update_data["name"])
        if existing_role:
            logger.warning(f"尝试更新角色名称为已存在的名称: {update_data['name']}")
            raise ValueError(f"角色名称已存在: {update_data['name']}")
    
    # 更新字段
    for field, value in update_data.items():
        if hasattr(role, field) and value is not None:
            setattr(role, field, value)
    
    # 保存到数据库
    await db.commit()
    await db.refresh(role)
    
    logger.info(f"更新角色: {role.name}")
    return role


async def delete_role(db: AsyncSession, role: Role) -> bool:
    """
    删除角色
    
    Args:
        db: 数据库会话
        role: 要删除的角色对象
        
    Returns:
        bool: 是否成功删除
    """
    role_name = role.name
    
    # 从数据库中删除
    await db.delete(role)
    await db.commit()
    
    logger.info(f"删除角色: {role_name}")
    return True