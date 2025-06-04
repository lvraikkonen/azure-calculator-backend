# app/services/token_billing/token_cost_calculator.py

import time
from typing import Dict, Any, Optional, Tuple
from app.core.logging import get_logger
from app.models.token_usage import TokenUsageStats, TokenUsageEvent
from app.services.model_management.model_configuration_service import ModelConfigurationService
from app.utils.token_counter import count_tokens

logger = get_logger(__name__)


class TokenCostCalculator:
    """Token成本计算器"""

    def __init__(self, model_config_service: ModelConfigurationService = None):
        """
        初始化Token成本计算器
        
        Args:
            model_config_service: 模型配置服务实例
        """
        self.model_config_service = model_config_service
        self.logger = logger

    async def get_model_pricing(self, model_id: str) -> Tuple[float, float]:
        """
        获取模型价格信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            Tuple[float, float]: (输入价格, 输出价格) 每百万token的价格
        """
        if not self.model_config_service:
            logger.warning("模型配置服务未初始化，使用默认价格")
            return 0.0, 0.0
        
        try:
            model_config = await self.model_config_service.get_model_by_id(model_id)
            if not model_config:
                logger.warning(f"模型不存在: {model_id}")
                return 0.0, 0.0
            
            input_price = model_config.input_price or 0.0
            output_price = model_config.output_price or 0.0
            
            return input_price, output_price
            
        except Exception as e:
            logger.error(f"获取模型价格失败: {str(e)}")
            return 0.0, 0.0

    def calculate_token_costs(self, input_tokens: int, output_tokens: int,
                            input_price: float, output_price: float) -> TokenUsageStats:
        """
        计算token统计和成本
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            input_price: 输入token价格（每百万token）
            output_price: 输出token价格（每百万token）
            
        Returns:
            TokenUsageStats: Token使用统计
        """
        stats = TokenUsageStats()
        stats.input_tokens = input_tokens
        stats.output_tokens = output_tokens

        # 计算成本（价格是每百万token的价格）
        stats.input_cost = (input_tokens * input_price) / 1_000_000
        stats.output_cost = (output_tokens * output_price) / 1_000_000

        return stats

    async def calculate_costs_by_model_id(self, model_id: str, input_tokens: int, 
                                        output_tokens: int) -> TokenUsageStats:
        """
        根据模型ID计算成本
        
        Args:
            model_id: 模型ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            
        Returns:
            TokenUsageStats: Token使用统计
        """
        input_price, output_price = await self.get_model_pricing(model_id)
        return self.calculate_token_costs(input_tokens, output_tokens, input_price, output_price)

    async def track_token_usage(self, model_id: str, model_name: str, model_type: str,
                              input_tokens: int, output_tokens: int, 
                              operation_name: str = "chat",
                              start_time: Optional[float] = None, 
                              end_time: Optional[float] = None,
                              user_id: Optional[str] = None,
                              conversation_id: Optional[str] = None,
                              request_id: Optional[str] = None,
                              success: bool = True,
                              error_message: Optional[str] = None) -> TokenUsageEvent:
        """
        跟踪token使用情况并创建使用事件
        
        Args:
            model_id: 模型ID
            model_name: 模型名称
            model_type: 模型类型
            input_tokens: 输入token数
            output_tokens: 输出token数
            operation_name: 操作名称
            start_time: 开始时间戳
            end_time: 结束时间戳
            user_id: 用户ID
            conversation_id: 对话ID
            request_id: 请求ID
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            TokenUsageEvent: Token使用事件
        """
        # 计算成本
        stats = await self.calculate_costs_by_model_id(model_id, input_tokens, output_tokens)
        
        # 计算性能指标
        response_time = None
        if start_time is not None and end_time is not None:
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

        # 创建使用事件
        event = TokenUsageEvent(
            model_id=model_id,
            model_name=model_name,
            model_type=model_type,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=stats.input_cost,
            output_cost=stats.output_cost,
            response_time=response_time,
            operation_name=operation_name,
            success=success,
            error_message=error_message
        )

        # 记录事件到日志
        self.log_usage_event(event)

        return event

    def log_usage_event(self, event: TokenUsageEvent):
        """记录token使用事件到日志"""
        speed = 0.0
        if event.response_time and event.response_time > 0:
            speed = (event.output_tokens / event.response_time) * 1000  # tokens/second

        log_message = (
            f"{event.operation_name} - 模型: {event.model_name} ({event.model_id}), "
            f"输入Token: {event.input_tokens}, "
            f"输出Token: {event.output_tokens}, "
            f"总Token: {event.total_tokens}, "
            f"总成本: ${event.total_cost:.6f}"
        )

        if event.response_time:
            log_message += f", 耗时: {event.response_time:.2f}ms, 速度: {speed:.2f}tokens/s"

        if not event.success and event.error_message:
            log_message += f", 错误: {event.error_message}"

        if event.success:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)

    def estimate_cost(self, input_tokens: int, output_tokens: int,
                     input_price: float, output_price: float) -> float:
        """
        估算成本
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            input_price: 输入token价格（每百万token）
            output_price: 输出token价格（每百万token）
            
        Returns:
            float: 估算成本
        """
        input_cost = (input_tokens * input_price) / 1_000_000
        output_cost = (output_tokens * output_price) / 1_000_000
        return input_cost + output_cost

    async def estimate_cost_by_model_id(self, model_id: str, input_tokens: int, 
                                      output_tokens: int) -> float:
        """
        根据模型ID估算成本
        
        Args:
            model_id: 模型ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            
        Returns:
            float: 估算成本
        """
        input_price, output_price = await self.get_model_pricing(model_id)
        return self.estimate_cost(input_tokens, output_tokens, input_price, output_price)

    def format_cost_summary(self, stats: TokenUsageStats, duration: Optional[float] = None) -> str:
        """
        格式化成本摘要
        
        Args:
            stats: Token使用统计
            duration: 持续时间（秒）
            
        Returns:
            str: 格式化的摘要
        """
        summary = (
            f"Token使用: {stats.input_tokens}输入 + {stats.output_tokens}输出 = {stats.total_tokens}总计, "
            f"成本: ${stats.input_cost:.6f} + ${stats.output_cost:.6f} = ${stats.total_cost:.6f}"
        )
        
        if duration and stats.output_tokens > 0:
            speed = stats.output_tokens / duration
            summary += f", 速度: {speed:.2f}tokens/s"
        
        return summary

    async def count_and_calculate_cost(self, text: str, model_id: str,
                                     is_input: bool = True) -> Tuple[int, float]:
        """
        计算文本的token数量和成本

        Args:
            text: 要计算的文本
            model_id: 模型ID
            is_input: 是否为输入文本

        Returns:
            Tuple[int, float]: (token数量, 成本)
        """
        try:
            # 获取模型信息
            if not self.model_config_service:
                logger.warning("模型配置服务未初始化")
                return 0, 0.0

            model_config = await self.model_config_service.get_model_by_id(model_id)
            if not model_config:
                logger.warning(f"模型不存在: {model_id}")
                return 0, 0.0

            # 计算token数量
            token_count = count_tokens(text, model_config.model_type, model_config.model_name)

            # 计算成本
            if is_input:
                price = model_config.input_price or 0.0
            else:
                price = model_config.output_price or 0.0

            cost = (token_count * price) / 1_000_000

            return token_count, cost

        except Exception as e:
            logger.error(f"计算token和成本失败: {str(e)}", exc_info=True)
            return 0, 0.0

    def create_usage_event_from_response(self, model_id: str, model_name: str,
                                       model_type: str, input_text: str,
                                       output_text: str, start_time: float,
                                       end_time: float, user_id: Optional[str] = None,
                                       conversation_id: Optional[str] = None,
                                       request_id: Optional[str] = None,
                                       success: bool = True,
                                       error_message: Optional[str] = None) -> TokenUsageEvent:
        """
        从LLM响应创建使用事件

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
            error_message: 错误信息

        Returns:
            TokenUsageEvent: Token使用事件
        """
        try:
            # 计算输入和输出token数量
            input_tokens = count_tokens(input_text, model_type, model_name)
            output_tokens = count_tokens(output_text, model_type, model_name) if output_text else 0

            # 计算性能指标
            response_time = None
            if start_time is not None and end_time is not None:
                response_time = (end_time - start_time) * 1000  # 转换为毫秒

            # 创建使用事件（不计算成本，因为需要异步获取模型价格）
            event = TokenUsageEvent(
                model_id=model_id,
                model_name=model_name,
                model_type=model_type,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=0.0,  # 成本需要在调用方异步计算
                output_cost=0.0,
                response_time=response_time,
                operation_name="llm_response",
                success=success,
                error_message=error_message
            )

            return event

        except Exception as e:
            logger.error(f"创建使用事件失败: {str(e)}", exc_info=True)
            # 返回空事件
            return TokenUsageEvent(
                model_id=model_id,
                model_name=model_name,
                model_type=model_type,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                success=success,
                error_message=error_message
            )
