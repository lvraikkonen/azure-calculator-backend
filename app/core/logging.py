import json
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_logger(name: str):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logger: 配置好的日志记录器
    """
    return logger.bind(name=name)


def setup_logging():
    """配置应用日志系统"""
    # 确保日志目录存在
    log_path = Path(settings.LOG_FILE).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出处理器
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        colorize=True,
    )
    
    # 添加文件输出处理器
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
    )
    
    logger.info(f"日志系统已初始化，日志级别: {settings.LOG_LEVEL}")


def sync_log_user_operation(
    user: Optional[str],
    action: str,
    details: Dict[str, Any],
    status: str = "成功",
):
    """
    同步记录用户操作日志
    
    Args:
        user: 用户名
        action: 操作类型
        details: 操作详情
        status: 操作状态
    """
    operation_logger = get_logger("user_operation")
    
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user or "未认证用户",
            "action": action,
            "status": status,
            "details": details,
        }
        
        operation_logger.info(f"用户操作: {json.dumps(log_entry, ensure_ascii=False)}")
        
    except Exception as e:
        logger.error(f"记录用户操作日志失败: {e}")


async def async_log_user_operation(
    user: Optional[str],
    action: str,
    details: Dict[str, Any],
    status: str = "成功",
):
    """
    异步记录用户操作日志
    
    Args:
        user: 用户名
        action: 操作类型
        details: 操作详情
        status: 操作状态
    """
    # 实际项目中，可能需要将日志写入数据库或消息队列
    # 这里简化为调用同步日志函数
    sync_log_user_operation(user, action, details, status)