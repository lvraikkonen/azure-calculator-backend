from typing import List, Optional
import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

class UserService:
    """用户服务，提供用户相关的数据访问和业务逻辑"""
    
    def __init__(self, db: AsyncSession):
        """初始化用户服务"""
        self.db = db
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        通过ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 如果找到用户则返回，否则返回None
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 如果找到用户则返回，否则返回None
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_user_by_ldap_guid(self, ldap_guid: str) -> Optional[User]:
        """
        通过LDAP GUID获取用户
        
        Args:
            ldap_guid: LDAP GUID
            
        Returns:
            Optional[User]: 如果找到用户则返回，否则返回None
        """
        result = await self.db.execute(select(User).where(User.ldap_guid == ldap_guid))
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        通过电子邮件获取用户
        
        Args:
            email: 电子邮件地址
            
        Returns:
            Optional[User]: 如果找到用户则返回，否则返回None
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        获取多个用户（分页）
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[User]: 用户列表
        """
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def create_user(self, user_in: UserCreate) -> User:
        """
        创建新用户
        
        Args:
            user_in: 用户创建数据
            
        Returns:
            User: 创建的用户
        """
        # 创建带有哈希密码的新用户
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=get_password_hash(user_in.password),
            is_active=user_in.is_active if user_in.is_active is not None else True,
            is_superuser=user_in.is_superuser if user_in.is_superuser is not None else False,
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        logger.info(f"创建新用户: {db_user.username}")
        return db_user
    
    async def update_user(self, user_id: UUID, user_in: UserUpdate) -> Optional[User]:
        """
        更新用户

        Args:
            user_id: 用户ID
            user_in: 用户更新数据

        Returns:
            Optional[User]: 如果找到并更新用户则返回，否则返回None
        """
        # 获取当前用户
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"尝试更新不存在的用户: ID={user_id}")
            return None

        # 准备更新数据
        update_data = user_in.model_dump(exclude_unset=True)

        # 如果提供了密码，则对其进行哈希处理
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        # 更新用户
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await self.db.commit()

        logger.info(f"更新用户: ID={user_id}, 用户名={user.username}")

        # 刷新用户
        return await self.get_user_by_id(user_id)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        验证用户
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            Optional[User]: 如果验证成功则返回用户，否则返回None
        """
        user = await self.get_user_by_username(username)
        if not user:
            logger.warning(f"尝试验证不存在的用户: {username}")
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.warning(f"密码验证失败: 用户名={username}")
            return None
        
        logger.info(f"用户验证成功: {username}")
        return user
    
    def is_active(self, user: User) -> bool:
        """
        检查用户是否活跃
        
        Args:
            user: 要检查的用户
            
        Returns:
            bool: 如果用户是活跃的，则为True，否则为False
        """
        return user.is_active
    
    def is_superuser(self, user: User) -> bool:
        """
        检查用户是否是超级用户
        
        Args:
            user: 要检查的用户
            
        Returns:
            bool: 如果用户是超级用户，则为True，否则为False
        """
        return user.is_superuser
    
    async def delete_user(self, user_id: UUID) -> bool:
        """
        删除用户

        Args:
            user_id: 要删除的用户ID

        Returns:
            bool: 如果成功删除，则为True，否则为False
        """
        # 获取当前用户
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"尝试删除不存在的用户: ID={user_id}")
            return False

        username = user.username

        # 从数据库中删除
        await self.db.delete(user)
        await self.db.commit()

        logger.info(f"删除用户: ID={user_id}, 用户名={username}")
        return True