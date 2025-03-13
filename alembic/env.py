import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Fix Windows encoding issues
# 解决 Windows 编码问题
import sys
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到 Python 路径
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# 导入 Base 类和所有模型
from app.db.base import Base
from app.models.user import User 
from app.core.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
settings = get_settings()

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set the target for 'autogenerate' support
target_metadata = Base.metadata

# 从应用配置中获取数据库 URL
config.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    # 替换 asyncpg 为 psycopg2 用于 Alembic
    sqlalchemy_url = str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql+asyncpg", "postgresql"
    )
    
    # 使用同步引擎连接
    connectable = engine_from_config(
        {"sqlalchemy.url": sqlalchemy_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())