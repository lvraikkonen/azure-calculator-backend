# app/services/token_billing/token_interceptor.py

import time
from typing import Any, Optional, Dict, Callable, Awaitable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.token_billing.token_cost_calculator import TokenCostCalculator
from app.models.token_usage import TokenUsageEvent

logger = get_logger(__name__)


class TokenUsageInterceptor:
    """Token使用拦截器，自动记录LLM调用的Token使用情况"""

    def __init__(self, db: AsyncSession):
        """
        初始化Token使用拦截器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger
        self.token_calculator = TokenCostCalculator()
        self._usage_service = None

    @property
    def usage_service(self):
        """延迟初始化ModelUsageService以避免循环导入"""
        if self._usage_service is None:
            from app.services.model_management.model_usage_service import ModelUsageService
            self._usage_service = ModelUsageService(self.db)
        return self._usage_service

    async def intercept_llm_call(self,
                                model_id: UUID,
                                model_name: str,
                                model_type: str,
                                input_text: str,
                                output_text: str,
                                start_time: float,
                                end_time: float,
                                user_id: Optional[UUID] = None,
                                conversation_id: Optional[UUID] = None,
                                request_id: Optional[str] = None,
                                success: bool = True,
                                error_type: Optional[str] = None) -> TokenUsageEvent:
        """
        拦截LLM调用并记录Token使用情况
        
        Args:
            model_id: 模型ID
            model_name: 模型名称
            model_type: 模型类型
            input_text: 输入文本
            output_text: 输出文本
            start_time: 开始时间戳
            end_time: 结束时间戳
            user_id: 用户ID
            conversation_id: 对话ID
            request_id: 请求ID
            success: 是否成功
            error_type: 错误类型
            
        Returns:
            TokenUsageEvent: Token使用事件
        """
        try:
            # 创建使用事件
            event = self.token_calculator.create_usage_event_from_response(
                model_id=str(model_id),
                model_name=model_name,
                model_type=model_type,
                input_text=input_text,
                output_text=output_text,
                start_time=start_time,
                end_time=end_time,
                user_id=str(user_id) if user_id else None,
                conversation_id=str(conversation_id) if conversation_id else None,
                request_id=request_id,
                success=success,
                error_message=error_type
            )
            
            # 记录到数据库
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            await self.usage_service.record_usage(
                model_id=model_id,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                response_time=response_time,
                success=success,
                error_type=error_type
            )
            
            self.logger.info(f"拦截并记录LLM调用: {model_name}, tokens={event.input_tokens}+{event.output_tokens}, cost=${event.total_cost:.6f}")
            
            return event
            
        except Exception as e:
            self.logger.error(f"拦截LLM调用失败: {str(e)}", exc_info=True)
            # 返回空事件
            return TokenUsageEvent(
                model_id=str(model_id),
                model_name=model_name,
                model_type=model_type,
                user_id=str(user_id) if user_id else None,
                conversation_id=str(conversation_id) if conversation_id else None,
                request_id=request_id,
                success=success,
                error_message=str(e)
            )

    def create_decorator(self) -> Callable:
        """
        创建装饰器用于自动拦截LLM调用
        
        Returns:
            Callable: 装饰器函数
        """
        def llm_usage_tracker(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            """
            LLM使用跟踪装饰器
            
            Args:
                func: 被装饰的LLM调用函数
                
            Returns:
                Callable: 装饰后的函数
            """
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    # 执行原函数
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    
                    # 从参数中提取信息（这里需要根据实际LLM调用接口调整）
                    model_id = kwargs.get('model_id')
                    model_name = kwargs.get('model_name', 'unknown')
                    model_type = kwargs.get('model_type', 'unknown')
                    input_text = kwargs.get('input_text', kwargs.get('prompt', ''))
                    output_text = getattr(result, 'content', str(result) if result else '')
                    user_id = kwargs.get('user_id')
                    conversation_id = kwargs.get('conversation_id')
                    request_id = kwargs.get('request_id')
                    
                    if model_id:
                        # 记录使用情况
                        await self.intercept_llm_call(
                            model_id=UUID(model_id) if isinstance(model_id, str) else model_id,
                            model_name=model_name,
                            model_type=model_type,
                            input_text=input_text,
                            output_text=output_text,
                            start_time=start_time,
                            end_time=end_time,
                            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                            conversation_id=UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id,
                            request_id=request_id,
                            success=True
                        )
                    
                    return result
                    
                except Exception as e:
                    end_time = time.time()
                    
                    # 记录失败的调用
                    model_id = kwargs.get('model_id')
                    if model_id:
                        await self.intercept_llm_call(
                            model_id=UUID(model_id) if isinstance(model_id, str) else model_id,
                            model_name=kwargs.get('model_name', 'unknown'),
                            model_type=kwargs.get('model_type', 'unknown'),
                            input_text=kwargs.get('input_text', kwargs.get('prompt', '')),
                            output_text='',
                            start_time=start_time,
                            end_time=end_time,
                            user_id=UUID(kwargs.get('user_id')) if kwargs.get('user_id') else None,
                            conversation_id=UUID(kwargs.get('conversation_id')) if kwargs.get('conversation_id') else None,
                            request_id=kwargs.get('request_id'),
                            success=False,
                            error_type=str(e)
                        )
                    
                    raise
            
            return wrapper
        
        return llm_usage_tracker


class TokenUsageContext:
    """Token使用上下文管理器"""
    
    def __init__(self, interceptor: TokenUsageInterceptor, 
                 model_id: UUID, model_name: str, model_type: str,
                 user_id: Optional[UUID] = None,
                 conversation_id: Optional[UUID] = None,
                 request_id: Optional[str] = None):
        """
        初始化Token使用上下文
        
        Args:
            interceptor: Token使用拦截器
            model_id: 模型ID
            model_name: 模型名称
            model_type: 模型类型
            user_id: 用户ID
            conversation_id: 对话ID
            request_id: 请求ID
        """
        self.interceptor = interceptor
        self.model_id = model_id
        self.model_name = model_name
        self.model_type = model_type
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.request_id = request_id
        self.start_time = None
        self.input_text = ""
        self.output_text = ""
        
    async def __aenter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        end_time = time.time()
        success = exc_type is None
        error_type = str(exc_val) if exc_val else None
        
        # 记录使用情况
        await self.interceptor.intercept_llm_call(
            model_id=self.model_id,
            model_name=self.model_name,
            model_type=self.model_type,
            input_text=self.input_text,
            output_text=self.output_text,
            start_time=self.start_time,
            end_time=end_time,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            request_id=self.request_id,
            success=success,
            error_type=error_type
        )
        
    def set_input(self, text: str):
        """设置输入文本"""
        self.input_text = text
        
    def set_output(self, text: str):
        """设置输出文本"""
        self.output_text = text


# 全局拦截器实例（可选）
_global_interceptor: Optional[TokenUsageInterceptor] = None


def get_global_interceptor() -> Optional[TokenUsageInterceptor]:
    """获取全局拦截器实例"""
    return _global_interceptor


def set_global_interceptor(interceptor: TokenUsageInterceptor):
    """设置全局拦截器实例"""
    global _global_interceptor
    _global_interceptor = interceptor


def track_llm_usage(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    全局LLM使用跟踪装饰器
    
    Args:
        func: 被装饰的LLM调用函数
        
    Returns:
        Callable: 装饰后的函数
    """
    interceptor = get_global_interceptor()
    if interceptor:
        return interceptor.create_decorator()(func)
    else:
        logger.warning("全局Token使用拦截器未设置，跳过使用跟踪")
        return func
