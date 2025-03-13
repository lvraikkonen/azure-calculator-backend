import time
import uuid
from functools import wraps
from typing import List, Optional, Any, Dict
from fastapi import HTTPException
from app.core.logging import async_log_user_operation

def mask_value(key: str, value: Any) -> str:
    """智能掩码处理，根据不同字段类型采用不同掩码策略"""
    if isinstance(value, str):
        # 对邮箱进行部分掩码
        if key.lower() in ["email", "emailaddress"] and "@" in value:
            username, domain = value.split("@", 1)
            if len(username) > 3:
                return f"{username[:2]}***@{domain}"
            else:
                return f"***@{domain}"
        
        # 对电话进行部分掩码
        elif key.lower() in ["phone", "mobile", "tel", "mobilephone"]:
            if len(value) > 7:
                return f"{value[:3]}****{value[-4:]}"
            else:
                return "******" + value[-2:] if len(value) > 2 else "******"
    
    # 默认掩码处理
    return "***"

def log_employee_operation(action: str, sensitive_params: List[str] = [], log_start: bool = False):
    """
    员工操作日志装饰器（优化版）
    Args:
        action: 操作名称（需遵循规范：动词+业务对象）
        sensitive_params: 需要过滤的敏感参数名列表
        log_start: 是否记录开始日志（对于频繁/快速操作可省略开始日志）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            username = current_user.username if current_user else "未认证用户"
            
            # 创建唯一事务ID用于关联开始和结束日志
            txn_id = str(uuid.uuid4())[:8]
            
            # 过滤敏感参数和不可序列化的对象
            non_serializable = ["db", "current_user", "file"]
            filtered_kwargs = {}
            
            for k, v in kwargs.items():
                if k in non_serializable:
                    filtered_kwargs[k] = "<non-serializable>"
                elif k in sensitive_params:
                    filtered_kwargs[k] = mask_value(k, v)
                else:
                    filtered_kwargs[k] = str(v) if not isinstance(v, (int, float, bool, type(None))) else v
            
            start_time = time.time()
            try:
                # 记录操作开始（可选）
                if log_start:
                    await async_log_user_operation(
                        user=username,
                        action=action,
                        details={"txn_id": txn_id, "status": "开始"},
                        status="进行中"
                    )
                
                # 执行原函数
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 构建日志详情
                log_details: Dict[str, Any] = {
                    "txn_id": txn_id,
                    "params": filtered_kwargs,
                    "duration_sec": round(duration, 3)
                }
                
                # 处理不同类型的结果
                if isinstance(result, list):
                    log_details["result_stats"] = {
                        "count": len(result),
                        "empty": len(result) == 0
                    }
                elif isinstance(result, dict):
                    # 处理API元数据响应
                    if "result_metadata" in result:
                        log_details.update(result["result_metadata"])
                    
                    # 特殊处理分页响应
                    if "total" in result and "items" in result:
                        log_details["result_stats"] = {
                            "count": len(result["items"]),
                            "total": result["total"],
                            "pages": (result["total"] + 99) // 100  # 假设页面大小为100
                        }
                    else:
                        log_details["result_stats"] = {"count": 1}
                else:
                    log_details["result_stats"] = {"count": 1}
                
                await async_log_user_operation(
                    user=username,
                    action=action,
                    details=log_details,
                    status="成功"
                )
                return result
                
            except HTTPException as e:
                await async_log_user_operation(
                    user=username,
                    action=action,
                    details={
                        "txn_id": txn_id,
                        "status_code": e.status_code,
                        "detail": e.detail,
                        "params": filtered_kwargs,
                        "duration_sec": round(time.time() - start_time, 3)
                    },
                    status="失败"
                )
                raise
                
            except Exception as e:
                await async_log_user_operation(
                    user=username,
                    action=action,
                    details={
                        "txn_id": txn_id,
                        "error": str(e),
                        "params": filtered_kwargs,
                        "duration_sec": round(time.time() - start_time, 3)
                    },
                    status="失败"
                )
                raise HTTPException(status_code=500, detail=str(e))
                
        return wrapper
    return decorator