# app/services/token_billing/analytics_service.py

import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
from scipy import stats

from app.core.logging import get_logger
from app.models.model_usage_daily import ModelUsageDaily
from app.models.model_usage_hourly import ModelUsageHourly
from app.models.model_usage_log import ModelUsageLog
from app.models.model_configuration import ModelConfiguration

logger = get_logger(__name__)


class TrendDirection(Enum):
    """趋势方向"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnalyticsPeriod(Enum):
    """分析周期"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    direction: TrendDirection
    slope: float
    correlation: float
    confidence: float
    prediction_7d: float
    prediction_30d: float
    volatility: float
    seasonal_pattern: Optional[Dict[str, float]] = None


@dataclass
class UsagePattern:
    """使用模式"""
    peak_hours: List[int]
    peak_days: List[str]
    usage_distribution: Dict[str, float]
    efficiency_score: float
    cost_optimization_potential: float


@dataclass
class CostForecast:
    """成本预测"""
    period: str
    predicted_cost: float
    confidence_interval: Tuple[float, float]
    factors: Dict[str, float]
    recommendations: List[str]


class TokenUsageAnalytics:
    """Token使用分析服务"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化分析服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger
    
    async def analyze_usage_trends(self, model_id: Optional[UUID] = None, 
                                 days: int = 30) -> Dict[str, TrendAnalysis]:
        """
        分析使用趋势
        
        Args:
            model_id: 模型ID，为None则分析所有模型
            days: 分析天数
            
        Returns:
            Dict[str, TrendAnalysis]: 按指标分组的趋势分析
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 构建查询
            stmt = select(
                ModelUsageDaily.usage_date,
                func.sum(ModelUsageDaily.request_count).label('total_requests'),
                func.sum(ModelUsageDaily.input_tokens + ModelUsageDaily.output_tokens).label('total_tokens'),
                func.avg(ModelUsageDaily.avg_response_time).label('avg_response_time'),
                func.sum(ModelUsageDaily.error_count).label('total_errors')
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= start_date,
                    ModelUsageDaily.usage_date <= end_date
                )
            ).group_by(ModelUsageDaily.usage_date).order_by(ModelUsageDaily.usage_date)
            
            if model_id:
                stmt = stmt.where(ModelUsageDaily.model_id == model_id)
            
            result = await self.db.execute(stmt)
            data = result.all()
            
            if len(data) < 7:  # 需要至少7天数据进行趋势分析
                return {}
            
            # 准备数据
            dates = [row.usage_date for row in data]
            requests = [row.total_requests or 0 for row in data]
            tokens = [row.total_tokens or 0 for row in data]
            response_times = [row.avg_response_time or 0 for row in data]
            errors = [row.total_errors or 0 for row in data]
            
            # 分析各项指标的趋势
            trends = {}
            
            # 请求数趋势
            trends['requests'] = self._analyze_metric_trend(dates, requests, 'requests')
            
            # Token使用趋势
            trends['tokens'] = self._analyze_metric_trend(dates, tokens, 'tokens')
            
            # 响应时间趋势
            if any(rt > 0 for rt in response_times):
                trends['response_time'] = self._analyze_metric_trend(dates, response_times, 'response_time')
            
            # 错误率趋势
            if any(e > 0 for e in errors):
                error_rates = [e / max(r, 1) for e, r in zip(errors, requests)]
                trends['error_rate'] = self._analyze_metric_trend(dates, error_rates, 'error_rate')
            
            return trends
            
        except Exception as e:
            self.logger.error(f"分析使用趋势失败: {str(e)}", exc_info=True)
            return {}
    
    def _analyze_metric_trend(self, dates: List[date], values: List[float], 
                            metric_name: str) -> TrendAnalysis:
        """分析单个指标的趋势"""
        try:
            # 转换日期为数值
            x = np.array([(d - dates[0]).days for d in dates])
            y = np.array(values)
            
            # 线性回归分析趋势
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # 确定趋势方向
            if abs(slope) < np.std(y) * 0.1:  # 斜率很小
                direction = TrendDirection.STABLE
            elif slope > 0:
                direction = TrendDirection.INCREASING
            else:
                direction = TrendDirection.DECREASING
            
            # 计算波动性
            volatility = np.std(y) / (np.mean(y) + 1e-8)
            if volatility > 0.5:
                direction = TrendDirection.VOLATILE
            
            # 预测未来值
            last_x = x[-1]
            prediction_7d = slope * (last_x + 7) + intercept
            prediction_30d = slope * (last_x + 30) + intercept
            
            # 确保预测值不为负
            prediction_7d = max(0, prediction_7d)
            prediction_30d = max(0, prediction_30d)
            
            # 计算置信度
            confidence = abs(r_value) * (1 - p_value) if p_value < 0.05 else 0.0
            
            return TrendAnalysis(
                direction=direction,
                slope=slope,
                correlation=r_value,
                confidence=confidence,
                prediction_7d=prediction_7d,
                prediction_30d=prediction_30d,
                volatility=volatility
            )
            
        except Exception as e:
            self.logger.error(f"分析指标趋势失败 ({metric_name}): {str(e)}")
            return TrendAnalysis(
                direction=TrendDirection.STABLE,
                slope=0.0,
                correlation=0.0,
                confidence=0.0,
                prediction_7d=0.0,
                prediction_30d=0.0,
                volatility=0.0
            )
    
    async def analyze_usage_patterns(self, model_id: Optional[UUID] = None, 
                                   days: int = 30) -> UsagePattern:
        """
        分析使用模式
        
        Args:
            model_id: 模型ID
            days: 分析天数
            
        Returns:
            UsagePattern: 使用模式分析结果
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 查询小时级数据
            stmt = select(
                func.extract('hour', ModelUsageHourly.hour_timestamp).label('hour'),
                func.extract('dow', ModelUsageHourly.hour_timestamp).label('day_of_week'),
                func.sum(ModelUsageHourly.request_count).label('total_requests'),
                func.sum(ModelUsageHourly.input_tokens + ModelUsageHourly.output_tokens).label('total_tokens')
            ).where(
                and_(
                    func.date(ModelUsageHourly.hour_timestamp) >= start_date,
                    func.date(ModelUsageHourly.hour_timestamp) <= end_date
                )
            ).group_by('hour', 'day_of_week')
            
            if model_id:
                stmt = stmt.where(ModelUsageHourly.model_id == model_id)
            
            result = await self.db.execute(stmt)
            data = result.all()
            
            # 分析小时模式
            hour_usage = {}
            for row in data:
                hour = int(row.hour)
                requests = row.total_requests or 0
                hour_usage[hour] = hour_usage.get(hour, 0) + requests
            
            # 找出峰值小时（使用量前25%）
            if hour_usage:
                sorted_hours = sorted(hour_usage.items(), key=lambda x: x[1], reverse=True)
                peak_count = max(1, len(sorted_hours) // 4)
                peak_hours = [hour for hour, _ in sorted_hours[:peak_count]]
            else:
                peak_hours = []
            
            # 分析星期模式
            day_usage = {}
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            for row in data:
                day = int(row.day_of_week)
                requests = row.total_requests or 0
                day_usage[day] = day_usage.get(day, 0) + requests
            
            # 找出峰值天
            if day_usage:
                sorted_days = sorted(day_usage.items(), key=lambda x: x[1], reverse=True)
                peak_day_count = max(1, len(sorted_days) // 2)
                peak_days = [day_names[day] for day, _ in sorted_days[:peak_day_count]]
            else:
                peak_days = []
            
            # 计算使用分布
            total_usage = sum(hour_usage.values()) if hour_usage else 1
            usage_distribution = {
                'morning': sum(hour_usage.get(h, 0) for h in range(6, 12)) / total_usage,
                'afternoon': sum(hour_usage.get(h, 0) for h in range(12, 18)) / total_usage,
                'evening': sum(hour_usage.get(h, 0) for h in range(18, 24)) / total_usage,
                'night': sum(hour_usage.get(h, 0) for h in range(0, 6)) / total_usage
            }
            
            # 计算效率分数（基于使用分布的均匀性）
            distribution_values = list(usage_distribution.values())
            efficiency_score = 1.0 - np.std(distribution_values) if distribution_values else 0.0
            
            # 计算成本优化潜力（基于峰值集中度）
            if hour_usage:
                max_usage = max(hour_usage.values())
                avg_usage = np.mean(list(hour_usage.values()))
                cost_optimization_potential = (max_usage - avg_usage) / max_usage if max_usage > 0 else 0.0
            else:
                cost_optimization_potential = 0.0
            
            return UsagePattern(
                peak_hours=peak_hours,
                peak_days=peak_days,
                usage_distribution=usage_distribution,
                efficiency_score=efficiency_score,
                cost_optimization_potential=cost_optimization_potential
            )
            
        except Exception as e:
            self.logger.error(f"分析使用模式失败: {str(e)}", exc_info=True)
            return UsagePattern(
                peak_hours=[],
                peak_days=[],
                usage_distribution={},
                efficiency_score=0.0,
                cost_optimization_potential=0.0
            )
    
    async def forecast_costs(self, model_id: Optional[UUID] = None, 
                           forecast_days: int = 30) -> CostForecast:
        """
        预测成本
        
        Args:
            model_id: 模型ID
            forecast_days: 预测天数
            
        Returns:
            CostForecast: 成本预测结果
        """
        try:
            # 获取历史成本数据
            end_date = date.today()
            start_date = end_date - timedelta(days=60)  # 使用60天历史数据
            
            stmt = select(
                ModelUsageDaily.usage_date,
                ModelUsageDaily.model_id,
                ModelConfiguration.input_price,
                ModelConfiguration.output_price,
                ModelUsageDaily.input_tokens,
                ModelUsageDaily.output_tokens
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= start_date,
                    ModelUsageDaily.usage_date <= end_date
                )
            ).order_by(ModelUsageDaily.usage_date)
            
            if model_id:
                stmt = stmt.where(ModelUsageDaily.model_id == model_id)
            
            result = await self.db.execute(stmt)
            data = result.all()
            
            # 计算每日成本
            daily_costs = {}
            for row in data:
                date_key = row.usage_date
                input_price = row.input_price or 0.0
                output_price = row.output_price or 0.0
                
                input_cost = (row.input_tokens * input_price) / 1_000_000
                output_cost = (row.output_tokens * output_price) / 1_000_000
                daily_cost = input_cost + output_cost
                
                daily_costs[date_key] = daily_costs.get(date_key, 0.0) + daily_cost
            
            if len(daily_costs) < 7:
                return CostForecast(
                    period=f"{forecast_days}天",
                    predicted_cost=0.0,
                    confidence_interval=(0.0, 0.0),
                    factors={},
                    recommendations=["历史数据不足，无法进行准确预测"]
                )
            
            # 使用线性回归预测
            dates = sorted(daily_costs.keys())
            costs = [daily_costs[d] for d in dates]
            
            x = np.array([(d - dates[0]).days for d in dates])
            y = np.array(costs)
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # 预测未来成本
            last_x = x[-1]
            future_x = np.array([last_x + i for i in range(1, forecast_days + 1)])
            predicted_daily_costs = slope * future_x + intercept
            predicted_total_cost = np.sum(np.maximum(0, predicted_daily_costs))  # 确保不为负
            
            # 计算置信区间
            residuals = y - (slope * x + intercept)
            mse = np.mean(residuals ** 2)
            prediction_std = np.sqrt(mse * forecast_days)
            
            confidence_interval = (
                max(0, predicted_total_cost - 1.96 * prediction_std),
                predicted_total_cost + 1.96 * prediction_std
            )
            
            # 分析影响因素
            factors = {
                'trend_factor': abs(slope) / (np.mean(y) + 1e-8),
                'volatility_factor': np.std(y) / (np.mean(y) + 1e-8),
                'correlation_strength': abs(r_value),
                'data_quality': 1.0 - p_value if p_value < 0.05 else 0.0
            }
            
            # 生成建议
            recommendations = []
            if slope > 0:
                recommendations.append("成本呈上升趋势，建议优化使用模式")
            if factors['volatility_factor'] > 0.3:
                recommendations.append("成本波动较大，建议设置预算告警")
            if factors['correlation_strength'] < 0.5:
                recommendations.append("成本趋势不明显，建议增加监控频率")
            
            return CostForecast(
                period=f"{forecast_days}天",
                predicted_cost=predicted_total_cost,
                confidence_interval=confidence_interval,
                factors=factors,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"预测成本失败: {str(e)}", exc_info=True)
            return CostForecast(
                period=f"{forecast_days}天",
                predicted_cost=0.0,
                confidence_interval=(0.0, 0.0),
                factors={},
                recommendations=["预测失败，请检查数据质量"]
            )
