"""
完整的数据库初始化脚本
- 创建表结构
- 添加初始角色
- 添加初始超级用户
"""

import asyncio
import logging
import sys
import subprocess
import uuid
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.database import engine
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role
# 直接定义UserCreate类，避免导入问题
from pydantic import BaseModel, Field
from typing import Optional


# 定义简化版的UserCreate，仅用于本脚本
class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    is_active: bool = True
    is_superuser: bool = False
    groups: Optional[str] = None


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_init")

settings = get_settings()
PROJECT_ROOT = Path(__file__).parent.parent.parent


async def check_table_exists(table_name: str) -> bool:
    """
    检查表是否存在
    
    Args:
        table_name: 表名
        
    Returns:
        bool: 表是否存在
    """
    try:
        # 使用上下文管理器确保连接正确关闭
        async with engine.connect() as conn:
            # 使用text()构造SQL查询
            query = text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables " 
                "WHERE table_name = :table_name)"
            )
            # 执行查询并获取结果
            result = await conn.execute(query, {"table_name": table_name})
            return result.scalar()
    except Exception as e:
        logger.error(f"检查表是否存在时出错: {e}")
        return False


async def create_tables() -> None:
    """
    使用 SQLAlchemy 创建所有表
    """
    try:
        logger.info("开始创建数据库表...")
        
        # 使用 SQLAlchemy 的 metadata 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"创建数据库表时出错: {e}")
        raise


def run_alembic_migration() -> bool:
    """
    运行 Alembic 迁移
    
    Returns:
        bool: 迁移是否成功
    """
    try:
        logger.info("开始运行 Alembic 迁移...")
        
        # 检查 Alembic 目录是否存在
        alembic_dir = PROJECT_ROOT / "alembic"
        if not alembic_dir.exists():
            logger.error("Alembic 目录不存在，无法运行迁移")
            return False
            
        # 运行 Alembic 迁移命令
        result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            cwd=PROJECT_ROOT,
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Alembic 迁移失败: {result.stderr}")
            return False
            
        logger.info(f"Alembic 迁移成功: {result.stdout}")
        return True
        
    except Exception as e:
        logger.error(f"运行 Alembic 迁移时出错: {e}")
        return False


async def get_user_by_username(db: AsyncSession, username: str) -> User:
    """
    根据用户名获取用户
    
    Args:
        db: 数据库会话
        username: 用户名
    
    Returns:
        User: 用户对象，如不存在返回None
    """
    # 使用原生SQL避免可能的异步问题
    result = await db.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": username}
    )
    user_row = result.first()
    if not user_row:
        return None
    
    # 手动创建User实例
    return User(**dict(user_row._mapping))


async def get_role_by_name(db: AsyncSession, name: str) -> Role:
    """
    根据角色名获取角色
    
    Args:
        db: 数据库会话
        name: 角色名
    
    Returns:
        Role: 角色对象，如不存在返回None
    """
    # 使用原生SQL避免可能的异步问题
    result = await db.execute(
        text("SELECT * FROM roles WHERE name = :name"),
        {"name": name}
    )
    role_row = result.first()
    if not role_row:
        return None
    
    # 手动创建Role实例
    return Role(**dict(role_row._mapping))


async def create_initial_roles(db: AsyncSession) -> None:
    """
    创建初始角色
    """
    # 角色定义
    roles = [
        {"name": "admin", "description": "管理员角色，拥有所有权限"},
        {"name": "user", "description": "普通用户角色，拥有基本权限"}
    ]
    
    for role_data in roles:
        # 检查角色是否已存在
        role_name = role_data["name"]
        existing_role = await get_role_by_name(db, role_name)
        
        if existing_role:
            logger.info(f"角色 '{role_name}' 已存在，跳过创建")
            continue
        
        # 创建新角色
        role_id = uuid.uuid4()
        current_time = "NOW()"  # PostgreSQL的当前时间函数
        
        # 使用原生SQL执行插入
        await db.execute(
            text("""
                INSERT INTO roles (id, name, description, created_at, updated_at)
                VALUES (:id, :name, :description, NOW(), NOW())
            """),
            {
                "id": role_id,
                "name": role_data["name"],
                "description": role_data["description"]
            }
        )
        await db.commit()
        logger.info(f"角色 '{role_name}' 创建成功")


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    创建用户
    
    Args:
        db: 数据库会话
        user_data: 用户数据
    
    Returns:
        User: 创建的用户对象
    """
    # 使用UUID生成新用户ID
    user_id = uuid.uuid4()
    hashed_password = get_password_hash(user_data.password)
    
    # 使用原生SQL执行插入
    await db.execute(
        text("""
            INSERT INTO users (
                id, username, email, full_name, hashed_password,
                is_active, is_superuser, groups, created_at, updated_at
            )
            VALUES (
                :id, :username, :email, :full_name, :hashed_password,
                :is_active, :is_superuser, :groups, NOW(), NOW()
            )
        """),
        {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "is_active": user_data.is_active,
            "is_superuser": user_data.is_superuser,
            "groups": user_data.groups
        }
    )
    await db.commit()
    
    # 获取创建的用户
    return await get_user_by_username(db, user_data.username)


async def assign_role_to_user(db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    """
    为用户分配角色
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        role_id: 角色ID
    """
    # 检查关联是否已存在
    result = await db.execute(
        text("""
            SELECT 1 FROM user_role
            WHERE user_id = :user_id AND role_id = :role_id
        """),
        {"user_id": user_id, "role_id": role_id}
    )
    if result.first():
        logger.info(f"用户角色关联已存在，跳过创建")
        return
    
    # 创建关联
    await db.execute(
        text("""
            INSERT INTO user_role (user_id, role_id)
            VALUES (:user_id, :role_id)
        """),
        {"user_id": user_id, "role_id": role_id}
    )
    await db.commit()


async def create_superuser(db: AsyncSession) -> None:
    """
    创建超级管理员账号及关联角色
    如果账号已存在则跳过
    """
    # 先确保角色已创建
    await create_initial_roles(db)
    
    # 检查管理员是否已存在
    admin_username = "admin"
    existing_admin = await get_user_by_username(db, admin_username)
    
    if existing_admin:
        logger.info(f"超级管理员 '{admin_username}' 已存在，跳过创建")
        # 确保管理员有admin角色
        admin_role = await get_role_by_name(db, "admin")
        if admin_role:
            # 检查是否已有角色关联
            await assign_role_to_user(db, existing_admin.id, admin_role.id)
            logger.info(f"确保用户 '{admin_username}' 有admin角色")
        return
    
    # 创建新的超级管理员
    logger.info(f"创建超级管理员 '{admin_username}'")
    admin_data = UserCreate(
        username=admin_username,
        email="admin@example.com",
        full_name="系统管理员",
        password="admin123",  # 生产环境部署前必须修改！
        is_active=True,
        is_superuser=True,
        groups="admin"
    )
    
    # 创建用户
    admin_user = await create_user(db, admin_data)
    
    # 为管理员添加admin角色
    admin_role = await get_role_by_name(db, "admin")
    if admin_role:
        await assign_role_to_user(db, admin_user.id, admin_role.id)
        logger.info(f"已为用户 '{admin_username}' 添加admin角色")
    
    logger.info(f"超级管理员 '{admin_username}' 创建成功")


async def init_db() -> None:
    """
    初始化数据库
    - 检查表结构
    - 创建表结构(如果需要)
    - 创建角色和超级管理员账号
    """
    logger.info("开始初始化数据库...")
    
    try:
        # 1. 检查表是否存在 (使用users表而不是user表)
        users_table_exists = await check_table_exists("users")
        
        # 2. 如果表不存在，创建表结构
        if not users_table_exists:
            logger.info("数据库表不存在，将创建表结构")
            
            # 先尝试使用 Alembic
            alembic_success = run_alembic_migration()
            
            # 如果 Alembic 失败，使用 SQLAlchemy 直接创建
            if not alembic_success:
                logger.warning("Alembic 迁移失败，使用 SQLAlchemy 直接创建表")
                await create_tables()
        else:
            logger.info("数据库表已存在，跳过创建")
        
        # 3. 创建角色和超级管理员
        async with AsyncSessionLocal() as db:
            await create_superuser(db)
            
        logger.info("数据库初始化完成！")
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise


if __name__ == "__main__":
    logger.info("正在初始化数据库...")
    asyncio.run(init_db())