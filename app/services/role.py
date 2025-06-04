from typing import List, Optional, Union
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

logger = logging.getLogger(__name__)

class RoleService:
    """角色服务，提供角色相关的数据访问和业务逻辑"""
    
    def __init__(self, db: AsyncSession):
        """初始化角色服务"""
        self.db = db
    
    async def get_role(self, role_id: int) -> Optional[Role]:
        """
        通过ID获取角色
        
        Args:
            role_id: 角色ID
            
        Returns:
            Optional[Role]: 角色对象或None
        """
        stmt = select(Role).where(Role.id == role_id).options(joinedload(Role.users))
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """
        通过名称获取角色
        
        Args:
            name: 角色名称
            
        Returns:
            Optional[Role]: 角色对象或None
        """
        stmt = select(Role).where(Role.name == name).options(joinedload(Role.users))
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def get_roles(self, skip: int = 0, limit: int = 100) -> List[Role]:
        """
        获取角色列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Role]: 角色列表
        """
        stmt = select(Role).options(joinedload(Role.users)).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create_role(self, role_in: RoleCreate) -> Role:
        """
        创建新角色
        
        Args:
            role_in: 角色创建模式
            
        Returns:
            Role: 创建的角色对象
            
        Raises:
            ValueError: 如果角色名称已存在
        """
        # 检查角色名称是否已存在
        existing_role = await self.get_role_by_name(role_in.name)
        if existing_role:
            logger.warning(f"尝试创建已存在的角色: {role_in.name}")
            raise ValueError(f"角色名称已存在: {role_in.name}")
        
        # 创建角色对象
        role = Role(
            name=role_in.name,
            description=role_in.description,
        )
        
        # 保存到数据库
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        
        logger.info(f"创建新角色: {role.name}")
        return role
    
    async def update_role(self, role: Role, role_in: Union[RoleUpdate, dict]) -> Role:
        """
        更新角色
        
        Args:
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
            existing_role = await self.get_role_by_name(update_data["name"])
            if existing_role:
                logger.warning(f"尝试更新角色名称为已存在的名称: {update_data['name']}")
                raise ValueError(f"角色名称已存在: {update_data['name']}")
        
        # 更新字段
        for field, value in update_data.items():
            if hasattr(role, field) and value is not None:
                setattr(role, field, value)
        
        # 保存到数据库
        await self.db.commit()
        await self.db.refresh(role)
        
        logger.info(f"更新角色: {role.name}")
        return role
    
    async def delete_role(self, role: Role) -> bool:
        """
        删除角色
        
        Args:
            role: 要删除的角色对象
            
        Returns:
            bool: 是否成功删除
        """
        role_name = role.name
        
        # 从数据库中删除
        await self.db.delete(role)
        await self.db.commit()
        
        logger.info(f"删除角色: {role_name}")
        return True
    
    async def assign_role_to_user(self, role: Role, user_id: UUID) -> bool:
        """
        为用户分配角色

        Args:
            role: 角色对象
            user_id: 用户ID

        Returns:
            bool: 是否成功分配
        """
        from app.models.user import User

        # 获取用户
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"尝试为不存在的用户分配角色: user_id={user_id}")
            return False

        # 分配角色
        role.users.append(user)
        await self.db.commit()

        logger.info(f"为用户({user.username})分配角色: {role.name}")
        return True
    
    async def remove_role_from_user(self, role: Role, user_id: UUID) -> bool:
        """
        从用户移除角色

        Args:
            role: 角色对象
            user_id: 用户ID

        Returns:
            bool: 是否成功移除
        """
        from app.models.user import User

        # 获取用户
        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"尝试从不存在的用户移除角色: user_id={user_id}")
            return False

        # 检查用户是否有此角色
        if user not in role.users:
            logger.warning(f"用户({user.username})没有角色: {role.name}")
            return False

        # 移除角色
        role.users.remove(user)
        await self.db.commit()

        logger.info(f"从用户({user.username})移除角色: {role.name}")
        return True