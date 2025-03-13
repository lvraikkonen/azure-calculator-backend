"""
完整的数据库初始化脚本
- 创建表结构
- 添加初始超级用户
"""

import asyncio
import logging
import sys
import subprocess
from pathlib import Path
from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.database import engine
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import create_user, get_user_by_username

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
        async with engine.connect() as conn:
            # PostgreSQL 特定的查询表是否存在的方法
            query = text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables " 
                "WHERE table_name = :table_name)"
            )
            result = await conn.execute(query, {"table_name": table_name})
            return await result.scalar()
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


async def create_superuser(db: AsyncSession) -> None:
    """
    创建超级管理员账号
    如果账号已存在则跳过
    """
    # 检查管理员是否已存在
    admin_username = "admin"
    existing_admin = await get_user_by_username(db, admin_username)
    
    if existing_admin:
        logger.info(f"超级管理员 '{admin_username}' 已存在，跳过创建")
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
    )
    
    # 创建用户
    await create_user(db, admin_data)
    logger.info(f"超级管理员 '{admin_username}' 创建成功")


async def init_db() -> None:
    """
    初始化数据库
    - 检查表结构
    - 创建表结构(如果需要)
    - 创建超级管理员账号
    """
    logger.info("开始初始化数据库...")
    
    try:
        # 1. 检查表是否存在
        user_table_exists = await check_table_exists("user")
        
        # 2. 如果表不存在，创建表结构
        if not user_table_exists:
            logger.info("数据库表不存在，将创建表结构")
            
            # 先尝试使用 Alembic
            alembic_success = run_alembic_migration()
            
            # 如果 Alembic 失败，使用 SQLAlchemy 直接创建
            if not alembic_success:
                logger.warning("Alembic 迁移失败，使用 SQLAlchemy 直接创建表")
                await create_tables()
        else:
            logger.info("数据库表已存在，跳过创建")
        
        # 3. 创建超级管理员
        async with AsyncSessionLocal() as db:
            await create_superuser(db)
            
        logger.info("数据库初始化完成！")
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise


if __name__ == "__main__":
    logger.info("正在初始化数据库...")
    asyncio.run(init_db())