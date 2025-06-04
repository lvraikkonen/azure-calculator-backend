# app/services/model_management/model_usage_service.py

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.model_configuration import ModelConfiguration
from app.models.model_usage_daily import ModelUsageDaily
from app.models.model_usage_hourly import ModelUsageHourly
from app.models.model_usage_log import ModelUsageLog
from app.models.user_usage_stats import UserUsageStats
from app.schemas.model_management.usage import (
    UsageQueryParams, DailyUsageResponse, HourlyUsageResponse,
    UsageSummaryResponse, UserUsageResponse, TokenUsageData,
    UsageReportRequest, UsageReportResponse
)
from app.utils.token_counter import count_tokens

logger = get_logger(__name__)


class ModelUsageService:
    """模型使用统计服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化模型使用统计服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger

    async def record_usage(self, model_id: UUID, user_id: Optional[UUID] = None,
                          conversation_id: Optional[UUID] = None,
                          request_id: Optional[str] = None,
                          input_tokens: int = 0, output_tokens: int = 0,
                          response_time: Optional[float] = None,
                          first_token_time: Optional[float] = None,
                          success: bool = True, error_type: Optional[str] = None) -> bool:
        """
        记录模型使用情况

        Args:
            model_id: 模型ID
            user_id: 用户ID
            conversation_id: 对话ID
            request_id: 请求ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            response_time: 响应时间(ms)
            first_token_time: 首个token响应时间(ms)
            success: 是否成功
            error_type: 错误类型

        Returns:
            bool: 是否记录成功
        """
        try:
            # 记录详细日志（采样记录）
            usage_log = ModelUsageLog(
                model_id=model_id,
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_time=response_time,
                first_token_time=first_token_time,
                success=success,
                error_type=error_type,
                timestamp=datetime.now(timezone.utc)
            )

            self.db.add(usage_log)

            # 异步更新聚合统计（这里先同步实现，后续可以改为Celery任务）
            await self._update_daily_stats(model_id, user_id, input_tokens, output_tokens,
                                         response_time, first_token_time, success)
            await self._update_hourly_stats(model_id, input_tokens, output_tokens,
                                          response_time, first_token_time, success)

            await self.db.commit()

            self.logger.info(f"记录模型使用: model_id={model_id}, tokens={input_tokens}+{output_tokens}")
            return True

        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"记录模型使用失败: {str(e)}", exc_info=True)
            return False

    async def _update_daily_stats(self, model_id: UUID, user_id: Optional[UUID],
                                input_tokens: int, output_tokens: int,
                                response_time: Optional[float], first_token_time: Optional[float],
                                success: bool) -> None:
        """更新日统计"""
        today = date.today()

        # 查找或创建日统计记录
        stmt = select(ModelUsageDaily).where(
            and_(ModelUsageDaily.model_id == model_id,
                 ModelUsageDaily.usage_date == today)
        )
        result = await self.db.execute(stmt)
        daily_stats = result.scalar_one_or_none()

        if not daily_stats:
            daily_stats = ModelUsageDaily(
                model_id=model_id,
                usage_date=today
            )
            self.db.add(daily_stats)

        # 更新统计数据
        daily_stats.request_count += 1
        if success:
            daily_stats.success_count += 1
        else:
            daily_stats.error_count += 1

        daily_stats.input_tokens += input_tokens
        daily_stats.output_tokens += output_tokens

        # 更新性能统计
        if response_time is not None:
            if daily_stats.avg_response_time is None:
                daily_stats.avg_response_time = response_time
            else:
                # 计算移动平均
                total_requests = daily_stats.request_count
                daily_stats.avg_response_time = (
                    (daily_stats.avg_response_time * (total_requests - 1) + response_time) / total_requests
                )

            if daily_stats.max_response_time is None or response_time > daily_stats.max_response_time:
                daily_stats.max_response_time = response_time

        if first_token_time is not None:
            if daily_stats.avg_first_token_time is None:
                daily_stats.avg_first_token_time = first_token_time
            else:
                total_requests = daily_stats.request_count
                daily_stats.avg_first_token_time = (
                    (daily_stats.avg_first_token_time * (total_requests - 1) + first_token_time) / total_requests
                )

        # 更新用户统计
        if user_id:
            # 这里可以实现更复杂的用户分布统计
            daily_stats.unique_users = daily_stats.unique_users or 0
            # 简化实现，实际应该维护用户集合
            daily_stats.unique_users += 1

        daily_stats.updated_at = datetime.now(timezone.utc)

    async def _update_hourly_stats(self, model_id: UUID, input_tokens: int, output_tokens: int,
                                 response_time: Optional[float], first_token_time: Optional[float],
                                 success: bool) -> None:
        """更新小时统计"""
        now = datetime.now(timezone.utc)
        hour_timestamp = now.replace(minute=0, second=0, microsecond=0)

        # 查找或创建小时统计记录
        stmt = select(ModelUsageHourly).where(
            and_(ModelUsageHourly.model_id == model_id,
                 ModelUsageHourly.hour_timestamp == hour_timestamp)
        )
        result = await self.db.execute(stmt)
        hourly_stats = result.scalar_one_or_none()

        if not hourly_stats:
            hourly_stats = ModelUsageHourly(
                model_id=model_id,
                hour_timestamp=hour_timestamp
            )
            self.db.add(hourly_stats)

        # 更新统计数据
        hourly_stats.request_count += 1
        if success:
            hourly_stats.success_count += 1
        else:
            hourly_stats.error_count += 1

        hourly_stats.input_tokens += input_tokens
        hourly_stats.output_tokens += output_tokens

        # 更新性能统计
        if response_time is not None:
            if hourly_stats.avg_response_time is None:
                hourly_stats.avg_response_time = response_time
            else:
                total_requests = hourly_stats.request_count
                hourly_stats.avg_response_time = (
                    (hourly_stats.avg_response_time * (total_requests - 1) + response_time) / total_requests
                )

            if hourly_stats.max_response_time is None or response_time > hourly_stats.max_response_time:
                hourly_stats.max_response_time = response_time

            if hourly_stats.min_response_time is None or response_time < hourly_stats.min_response_time:
                hourly_stats.min_response_time = response_time

        if first_token_time is not None:
            if hourly_stats.avg_first_token_time is None:
                hourly_stats.avg_first_token_time = first_token_time
            else:
                total_requests = hourly_stats.request_count
                hourly_stats.avg_first_token_time = (
                    (hourly_stats.avg_first_token_time * (total_requests - 1) + first_token_time) / total_requests
                )

    async def get_daily_usage(self, params: UsageQueryParams) -> List[DailyUsageResponse]:
        """
        获取日使用量统计

        Args:
            params: 查询参数

        Returns:
            List[DailyUsageResponse]: 日使用量列表
        """
        try:
            # 构建查询
            stmt = select(ModelUsageDaily).options(
                selectinload(ModelUsageDaily.model)
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= params.start_date,
                    ModelUsageDaily.usage_date <= params.end_date
                )
            )

            # 添加模型过滤
            if params.model_id:
                stmt = stmt.where(ModelUsageDaily.model_id == params.model_id)

            # 排序
            stmt = stmt.order_by(desc(ModelUsageDaily.usage_date))

            result = await self.db.execute(stmt)
            daily_stats = result.scalars().all()

            # 转换为响应格式
            responses = []
            for stats in daily_stats:
                # 计算成本
                input_cost, output_cost = 0.0, 0.0
                if hasattr(stats, 'model') and stats.model:
                    input_price = stats.model.input_price or 0.0
                    output_price = stats.model.output_price or 0.0
                    input_cost = (stats.input_tokens * input_price) / 1_000_000
                    output_cost = (stats.output_tokens * output_price) / 1_000_000

                token_usage = TokenUsageData(
                    input_tokens=stats.input_tokens,
                    output_tokens=stats.output_tokens,
                    total_tokens=stats.input_tokens + stats.output_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    total_cost=input_cost + output_cost
                )

                response = DailyUsageResponse(
                    usage_date=stats.usage_date,
                    model_id=stats.model_id,
                    model_name=stats.model.name if hasattr(stats, 'model') and stats.model else None,
                    request_count=stats.request_count,
                    success_count=stats.success_count,
                    error_count=stats.error_count,
                    token_usage=token_usage,
                    avg_response_time=stats.avg_response_time,
                    avg_first_token_time=stats.avg_first_token_time,
                    unique_users=stats.unique_users
                )
                responses.append(response)

            return responses

        except Exception as e:
            self.logger.error(f"获取日使用量统计失败: {str(e)}", exc_info=True)
            return []

    async def get_hourly_usage(self, params: UsageQueryParams) -> List[HourlyUsageResponse]:
        """
        获取小时使用量统计

        Args:
            params: 查询参数

        Returns:
            List[HourlyUsageResponse]: 小时使用量列表
        """
        try:
            # 构建查询
            start_datetime = datetime.combine(params.start_date, datetime.min.time())
            end_datetime = datetime.combine(params.end_date, datetime.max.time())

            stmt = select(ModelUsageHourly).options(
                selectinload(ModelUsageHourly.model)
            ).where(
                and_(
                    ModelUsageHourly.hour_timestamp >= start_datetime,
                    ModelUsageHourly.hour_timestamp <= end_datetime
                )
            )

            # 添加模型过滤
            if params.model_id:
                stmt = stmt.where(ModelUsageHourly.model_id == params.model_id)

            # 排序
            stmt = stmt.order_by(desc(ModelUsageHourly.hour_timestamp))

            result = await self.db.execute(stmt)
            hourly_stats = result.scalars().all()

            # 转换为响应格式
            responses = []
            for stats in hourly_stats:
                # 计算成本
                input_cost, output_cost = 0.0, 0.0
                if hasattr(stats, 'model') and stats.model:
                    input_price = stats.model.input_price or 0.0
                    output_price = stats.model.output_price or 0.0
                    input_cost = (stats.input_tokens * input_price) / 1_000_000
                    output_cost = (stats.output_tokens * output_price) / 1_000_000

                token_usage = TokenUsageData(
                    input_tokens=stats.input_tokens,
                    output_tokens=stats.output_tokens,
                    total_tokens=stats.input_tokens + stats.output_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    total_cost=input_cost + output_cost
                )

                response = HourlyUsageResponse(
                    hour_timestamp=stats.hour_timestamp,
                    model_id=stats.model_id,
                    model_name=stats.model.name if hasattr(stats, 'model') and stats.model else None,
                    request_count=stats.request_count,
                    success_count=stats.success_count,
                    error_count=stats.error_count,
                    token_usage=token_usage,
                    avg_response_time=stats.avg_response_time
                )
                responses.append(response)

            return responses

        except Exception as e:
            self.logger.error(f"获取小时使用量统计失败: {str(e)}", exc_info=True)
            return []

    async def get_usage_summary(self, params: UsageQueryParams) -> UsageSummaryResponse:
        """
        获取使用量摘要

        Args:
            params: 查询参数

        Returns:
            UsageSummaryResponse: 使用量摘要
        """
        try:
            # 查询日统计数据进行聚合
            stmt = select(
                func.sum(ModelUsageDaily.request_count).label('total_requests'),
                func.sum(ModelUsageDaily.success_count).label('total_success'),
                func.sum(ModelUsageDaily.error_count).label('total_errors'),
                func.sum(ModelUsageDaily.input_tokens).label('total_input_tokens'),
                func.sum(ModelUsageDaily.output_tokens).label('total_output_tokens'),
                func.avg(ModelUsageDaily.avg_response_time).label('avg_response_time'),
                func.sum(ModelUsageDaily.unique_users).label('total_unique_users')
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= params.start_date,
                    ModelUsageDaily.usage_date <= params.end_date
                )
            )

            # 添加模型过滤
            if params.model_id:
                stmt = stmt.where(ModelUsageDaily.model_id == params.model_id)

            result = await self.db.execute(stmt)
            summary_data = result.first()

            # 计算成本（需要按模型分别计算）
            total_cost = 0.0
            if params.model_id:
                # 单个模型的成本计算
                model_stmt = select(ModelConfiguration).where(ModelConfiguration.id == params.model_id)
                model_result = await self.db.execute(model_stmt)
                model = model_result.scalar_one_or_none()

                if model:
                    input_price = model.input_price or 0.0
                    output_price = model.output_price or 0.0
                    input_cost = (summary_data.total_input_tokens * input_price) / 1_000_000
                    output_cost = (summary_data.total_output_tokens * output_price) / 1_000_000
                    total_cost = input_cost + output_cost

            # 计算成功率
            success_rate = 0.0
            if summary_data.total_requests and summary_data.total_requests > 0:
                success_rate = (summary_data.total_success / summary_data.total_requests) * 100

            # 获取模型分布
            model_distribution = await self._get_model_distribution(params)

            token_usage = TokenUsageData(
                input_tokens=summary_data.total_input_tokens or 0,
                output_tokens=summary_data.total_output_tokens or 0,
                total_tokens=(summary_data.total_input_tokens or 0) + (summary_data.total_output_tokens or 0),
                input_cost=0.0,  # 这里简化处理，实际需要按模型计算
                output_cost=0.0,
                total_cost=total_cost
            )

            return UsageSummaryResponse(
                period_start=params.start_date,
                period_end=params.end_date,
                total_requests=summary_data.total_requests or 0,
                total_success=summary_data.total_success or 0,
                total_errors=summary_data.total_errors or 0,
                success_rate=success_rate,
                token_usage=token_usage,
                model_distribution=model_distribution,
                avg_response_time=summary_data.avg_response_time,
                unique_users=summary_data.total_unique_users or 0
            )

        except Exception as e:
            self.logger.error(f"获取使用量摘要失败: {str(e)}", exc_info=True)
            # 返回空摘要
            return UsageSummaryResponse(
                period_start=params.start_date,
                period_end=params.end_date,
                total_requests=0,
                total_success=0,
                total_errors=0,
                success_rate=0.0,
                token_usage=TokenUsageData(),
                model_distribution={},
                avg_response_time=None,
                unique_users=0
            )

    async def _get_model_distribution(self, params: UsageQueryParams) -> Dict[str, int]:
        """获取模型使用分布"""
        try:
            stmt = select(
                ModelConfiguration.name,
                func.sum(ModelUsageDaily.request_count).label('total_requests')
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= params.start_date,
                    ModelUsageDaily.usage_date <= params.end_date
                )
            ).group_by(ModelConfiguration.name)

            if params.model_id:
                stmt = stmt.where(ModelUsageDaily.model_id == params.model_id)

            result = await self.db.execute(stmt)
            distribution = {row.name: row.total_requests for row in result}

            return distribution

        except Exception as e:
            self.logger.error(f"获取模型分布失败: {str(e)}", exc_info=True)
            return {}

    async def calculate_token_costs(self, model_id: UUID, input_tokens: int,
                                  output_tokens: int) -> TokenUsageData:
        """
        计算Token成本

        Args:
            model_id: 模型ID
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            TokenUsageData: Token使用数据
        """
        try:
            # 获取模型价格
            model_stmt = select(ModelConfiguration).where(ModelConfiguration.id == model_id)
            result = await self.db.execute(model_stmt)
            model = result.scalar_one_or_none()

            if not model:
                self.logger.warning(f"模型不存在: {model_id}")
                return TokenUsageData(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                )

            # 计算成本
            input_price = model.input_price or 0.0
            output_price = model.output_price or 0.0
            input_cost = (input_tokens * input_price) / 1_000_000
            output_cost = (output_tokens * output_price) / 1_000_000

            return TokenUsageData(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=input_cost + output_cost
            )

        except Exception as e:
            self.logger.error(f"计算Token成本失败: {str(e)}", exc_info=True)
            return TokenUsageData(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens
            )

    async def estimate_tokens_for_text(self, text: str, model_id: UUID) -> int:
        """
        估算文本的token数量

        Args:
            text: 要估算的文本
            model_id: 模型ID

        Returns:
            int: 估算的token数量
        """
        try:
            # 获取模型信息
            model_stmt = select(ModelConfiguration).where(ModelConfiguration.id == model_id)
            result = await self.db.execute(model_stmt)
            model = result.scalar_one_or_none()

            if not model:
                self.logger.warning(f"模型不存在: {model_id}")
                return 0

            # 使用token计数器
            token_count = count_tokens(text, model.model_type, model.model_name)

            return token_count

        except Exception as e:
            self.logger.error(f"估算token数量失败: {str(e)}", exc_info=True)
            return 0

    async def get_user_usage_stats(self, user_id: UUID, start_date: date,
                                 end_date: date) -> UserUsageResponse:
        """
        获取用户使用统计

        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            UserUsageResponse: 用户使用统计
        """
        try:
            # 查询用户统计数据
            stmt = select(
                func.sum(ModelUsageLog.input_tokens).label('total_input_tokens'),
                func.sum(ModelUsageLog.output_tokens).label('total_output_tokens'),
                func.count(ModelUsageLog.id).label('total_requests')
            ).where(
                and_(
                    ModelUsageLog.user_id == user_id,
                    func.date(ModelUsageLog.timestamp) >= start_date,
                    func.date(ModelUsageLog.timestamp) <= end_date
                )
            )

            result = await self.db.execute(stmt)
            user_stats = result.first()

            # 获取模型使用分布
            model_stmt = select(
                ModelConfiguration.name,
                func.count(ModelUsageLog.id).label('usage_count')
            ).select_from(
                ModelUsageLog.join(ModelConfiguration)
            ).where(
                and_(
                    ModelUsageLog.user_id == user_id,
                    func.date(ModelUsageLog.timestamp) >= start_date,
                    func.date(ModelUsageLog.timestamp) <= end_date
                )
            ).group_by(ModelConfiguration.name)

            model_result = await self.db.execute(model_stmt)
            model_usage = {row.name: row.usage_count for row in model_result}

            # 计算总成本（简化处理）
            total_cost = 0.0
            # 这里可以根据具体需求实现更精确的成本计算

            token_usage = TokenUsageData(
                input_tokens=user_stats.total_input_tokens or 0,
                output_tokens=user_stats.total_output_tokens or 0,
                total_tokens=(user_stats.total_input_tokens or 0) + (user_stats.total_output_tokens or 0),
                total_cost=total_cost
            )

            return UserUsageResponse(
                user_id=user_id,
                username=None,  # 这里可以从用户表获取用户名
                total_requests=user_stats.total_requests or 0,
                token_usage=token_usage,
                model_usage=model_usage
            )

        except Exception as e:
            self.logger.error(f"获取用户使用统计失败: {str(e)}", exc_info=True)
            return UserUsageResponse(
                user_id=user_id,
                username=None,
                total_requests=0,
                token_usage=TokenUsageData(),
                model_usage={}
            )

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        清理旧的使用日志

        Args:
            days_to_keep: 保留天数

        Returns:
            int: 清理的记录数
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            # 删除旧的使用日志
            stmt = select(func.count(ModelUsageLog.id)).where(
                ModelUsageLog.timestamp < cutoff_date
            )
            result = await self.db.execute(stmt)
            count_to_delete = result.scalar()

            # 执行删除
            delete_stmt = ModelUsageLog.__table__.delete().where(
                ModelUsageLog.timestamp < cutoff_date
            )
            await self.db.execute(delete_stmt)
            await self.db.commit()

            self.logger.info(f"清理了 {count_to_delete} 条旧的使用日志")
            return count_to_delete

        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"清理旧日志失败: {str(e)}", exc_info=True)
            return 0