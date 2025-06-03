"""
自定义异常类定义
"""

from typing import Optional, Dict, Any


class BaseApplicationError(Exception):
    """应用程序基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(BaseApplicationError):
    """数据库相关异常"""
    pass


class SecurityError(BaseApplicationError):
    """安全相关异常"""
    pass


class ModelNotFoundError(BaseApplicationError):
    """模型未找到异常"""
    
    def __init__(self, model_id: str, message: Optional[str] = None):
        self.model_id = model_id
        message = message or f"模型未找到: {model_id}"
        super().__init__(message, "MODEL_NOT_FOUND", {"model_id": model_id})


class ModelValidationError(BaseApplicationError):
    """模型验证异常"""
    
    def __init__(self, validation_errors: list, message: Optional[str] = None):
        self.validation_errors = validation_errors
        message = message or f"模型验证失败: {', '.join(validation_errors)}"
        super().__init__(message, "MODEL_VALIDATION_ERROR", {"errors": validation_errors})


class ModelOperationError(BaseApplicationError):
    """模型操作异常"""
    pass


class ConfigurationError(BaseApplicationError):
    """配置相关异常"""
    pass


class ServiceUnavailableError(BaseApplicationError):
    """服务不可用异常"""
    pass


class RateLimitExceededError(BaseApplicationError):
    """速率限制超出异常"""
    pass


class AuthenticationError(BaseApplicationError):
    """认证异常"""
    pass


class AuthorizationError(BaseApplicationError):
    """授权异常"""
    pass
