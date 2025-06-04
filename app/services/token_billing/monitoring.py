# app/services/token_billing/monitoring.py

import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_usage_daily import ModelUsageDaily
from app.models.model_usage_hourly import ModelUsageHourly
from app.models.model_configuration import ModelConfiguration

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """告警严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    HIGH_USAGE = "high_usage"
    HIGH_COST = "high_cost"
    ERROR_RATE = "error_rate"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    BUDGET_EXCEEDED = "budget_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class Alert:
    """告警数据结构"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    model_id: Optional[UUID] = None
    model_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}


class AlertHandler:
    """告警处理器基类"""
    
    async def handle_alert(self, alert: Alert) -> bool:
        """
        处理告警
        
        Args:
            alert: 告警对象
            
        Returns:
            bool: 是否处理成功
        """
        raise NotImplementedError


class LogAlertHandler(AlertHandler):
    """日志告警处理器"""
    
    async def handle_alert(self, alert: Alert) -> bool:
        """记录告警到日志"""
        try:
            log_level = {
                AlertSeverity.LOW: logger.info,
                AlertSeverity.MEDIUM: logger.warning,
                AlertSeverity.HIGH: logger.error,
                AlertSeverity.CRITICAL: logger.critical
            }.get(alert.severity, logger.warning)
            
            log_message = f"[{alert.alert_type.value.upper()}] {alert.title}: {alert.message}"
            if alert.model_name:
                log_message += f" (模型: {alert.model_name})"
            if alert.current_value is not None and alert.threshold_value is not None:
                log_message += f" (当前值: {alert.current_value}, 阈值: {alert.threshold_value})"
            
            log_level(log_message)
            return True
            
        except Exception as e:
            logger.error(f"日志告警处理失败: {str(e)}", exc_info=True)
            return False


class EmailAlertHandler(AlertHandler):
    """邮件告警处理器（示例实现）"""
    
    def __init__(self, email_config: Dict[str, Any]):
        self.email_config = email_config
    
    async def handle_alert(self, alert: Alert) -> bool:
        """发送邮件告警"""
        try:
            # 这里应该实现实际的邮件发送逻辑
            logger.info(f"邮件告警: {alert.title} - {alert.message}")
            # 实际实现中可以使用 aiosmtplib 或其他邮件库
            return True
            
        except Exception as e:
            logger.error(f"邮件告警处理失败: {str(e)}", exc_info=True)
            return False


class WebhookAlertHandler(AlertHandler):
    """Webhook告警处理器（示例实现）"""
    
    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def handle_alert(self, alert: Alert) -> bool:
        """发送Webhook告警"""
        try:
            # 这里应该实现实际的HTTP请求逻辑
            logger.info(f"Webhook告警: {alert.title} - {alert.message}")
            # 实际实现中可以使用 aiohttp 发送HTTP请求
            return True
            
        except Exception as e:
            logger.error(f"Webhook告警处理失败: {str(e)}", exc_info=True)
            return False


class TokenUsageMonitor:
    """Token使用监控器"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化监控器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger
        self.alert_handlers: List[AlertHandler] = []
        
        # 默认阈值配置
        self.thresholds = {
            'high_usage_multiplier': 3.0,  # 使用量异常阈值倍数
            'high_cost_daily_limit': 100.0,  # 日成本限制（美元）
            'error_rate_threshold': 0.1,  # 错误率阈值（10%）
            'response_time_threshold': 5000.0,  # 响应时间阈值（毫秒）
        }
    
    def add_alert_handler(self, handler: AlertHandler):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: AlertHandler):
        """移除告警处理器"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
    
    async def send_alert(self, alert: Alert):
        """发送告警"""
        if not self.alert_handlers:
            self.logger.warning("没有配置告警处理器")
            return
        
        for handler in self.alert_handlers:
            try:
                await handler.handle_alert(alert)
            except Exception as e:
                self.logger.error(f"告警处理器执行失败: {str(e)}", exc_info=True)
    
    async def check_usage_anomalies(self, target_date: date = None) -> List[Alert]:
        """
        检查使用量异常
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            List[Alert]: 检测到的告警列表
        """
        if target_date is None:
            target_date = date.today()
        
        alerts = []
        
        try:
            # 获取最近7天的平均使用量（排除目标日期）
            start_date = target_date - timedelta(days=8)
            end_date = target_date - timedelta(days=1)
            
            # 计算历史平均值
            avg_stmt = select(
                ModelUsageDaily.model_id,
                ModelConfiguration.name.label('model_name'),
                func.avg(ModelUsageDaily.request_count).label('avg_requests'),
                func.avg(ModelUsageDaily.input_tokens + ModelUsageDaily.output_tokens).label('avg_tokens')
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                and_(
                    ModelUsageDaily.usage_date >= start_date,
                    ModelUsageDaily.usage_date <= end_date,
                    ModelUsageDaily.request_count > 0
                )
            ).group_by(
                ModelUsageDaily.model_id, ModelConfiguration.name
            )
            
            avg_result = await self.db.execute(avg_stmt)
            avg_usage = {row.model_id: {
                'model_name': row.model_name,
                'avg_requests': row.avg_requests or 0,
                'avg_tokens': row.avg_tokens or 0
            } for row in avg_result}
            
            # 检查目标日期的使用量
            today_stmt = select(
                ModelUsageDaily.model_id,
                ModelConfiguration.name.label('model_name'),
                ModelUsageDaily.request_count,
                (ModelUsageDaily.input_tokens + ModelUsageDaily.output_tokens).label('total_tokens')
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                ModelUsageDaily.usage_date == target_date
            )
            
            today_result = await self.db.execute(today_stmt)
            today_usage = today_result.all()
            
            # 检测异常
            threshold_multiplier = self.thresholds['high_usage_multiplier']
            
            for row in today_usage:
                model_id = row.model_id
                if model_id not in avg_usage:
                    continue
                
                avg_data = avg_usage[model_id]
                
                # 检查请求数异常
                if (row.request_count > avg_data['avg_requests'] * threshold_multiplier and 
                    avg_data['avg_requests'] > 0):
                    
                    severity = AlertSeverity.HIGH if row.request_count > avg_data['avg_requests'] * threshold_multiplier * 2 else AlertSeverity.MEDIUM
                    
                    alert = Alert(
                        alert_type=AlertType.HIGH_USAGE,
                        severity=severity,
                        title="请求数异常",
                        message=f"模型 {row.model_name} 的请求数异常高",
                        model_id=model_id,
                        model_name=row.model_name,
                        current_value=row.request_count,
                        threshold_value=avg_data['avg_requests'] * threshold_multiplier,
                        metadata={
                            'metric': 'request_count',
                            'average_value': avg_data['avg_requests'],
                            'threshold_multiplier': threshold_multiplier
                        }
                    )
                    alerts.append(alert)
                
                # 检查Token数异常
                if (row.total_tokens > avg_data['avg_tokens'] * threshold_multiplier and 
                    avg_data['avg_tokens'] > 0):
                    
                    severity = AlertSeverity.HIGH if row.total_tokens > avg_data['avg_tokens'] * threshold_multiplier * 2 else AlertSeverity.MEDIUM
                    
                    alert = Alert(
                        alert_type=AlertType.HIGH_USAGE,
                        severity=severity,
                        title="Token使用量异常",
                        message=f"模型 {row.model_name} 的Token使用量异常高",
                        model_id=model_id,
                        model_name=row.model_name,
                        current_value=row.total_tokens,
                        threshold_value=avg_data['avg_tokens'] * threshold_multiplier,
                        metadata={
                            'metric': 'token_usage',
                            'average_value': avg_data['avg_tokens'],
                            'threshold_multiplier': threshold_multiplier
                        }
                    )
                    alerts.append(alert)
            
            # 发送告警
            for alert in alerts:
                await self.send_alert(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查使用量异常失败: {str(e)}", exc_info=True)
            return []
    
    async def check_cost_limits(self, target_date: date = None) -> List[Alert]:
        """
        检查成本限制
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            List[Alert]: 检测到的告警列表
        """
        if target_date is None:
            target_date = date.today()
        
        alerts = []
        
        try:
            # 查询当日成本
            stmt = select(
                ModelUsageDaily.model_id,
                ModelConfiguration.name.label('model_name'),
                ModelConfiguration.input_price,
                ModelConfiguration.output_price,
                ModelUsageDaily.input_tokens,
                ModelUsageDaily.output_tokens
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                ModelUsageDaily.usage_date == target_date
            )
            
            result = await self.db.execute(stmt)
            usage_data = result.all()
            
            daily_limit = self.thresholds['high_cost_daily_limit']
            total_cost = 0.0
            
            for row in usage_data:
                # 计算模型成本
                input_price = row.input_price or 0.0
                output_price = row.output_price or 0.0
                
                input_cost = (row.input_tokens * input_price) / 1_000_000
                output_cost = (row.output_tokens * output_price) / 1_000_000
                model_cost = input_cost + output_cost
                total_cost += model_cost
                
                # 检查单个模型成本
                model_daily_limit = daily_limit * 0.5  # 单个模型不超过总限制的50%
                if model_cost > model_daily_limit:
                    alert = Alert(
                        alert_type=AlertType.HIGH_COST,
                        severity=AlertSeverity.HIGH,
                        title="模型成本超限",
                        message=f"模型 {row.model_name} 的日成本超过限制",
                        model_id=row.model_id,
                        model_name=row.model_name,
                        current_value=model_cost,
                        threshold_value=model_daily_limit,
                        metadata={
                            'input_cost': input_cost,
                            'output_cost': output_cost,
                            'input_tokens': row.input_tokens,
                            'output_tokens': row.output_tokens
                        }
                    )
                    alerts.append(alert)
            
            # 检查总成本
            if total_cost > daily_limit:
                alert = Alert(
                    alert_type=AlertType.HIGH_COST,
                    severity=AlertSeverity.CRITICAL,
                    title="总成本超限",
                    message=f"日总成本超过限制",
                    current_value=total_cost,
                    threshold_value=daily_limit,
                    metadata={
                        'models_count': len(usage_data),
                        'date': str(target_date)
                    }
                )
                alerts.append(alert)
            
            # 发送告警
            for alert in alerts:
                await self.send_alert(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查成本限制失败: {str(e)}", exc_info=True)
            return []
    
    async def check_error_rates(self, target_date: date = None) -> List[Alert]:
        """
        检查错误率
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            List[Alert]: 检测到的告警列表
        """
        if target_date is None:
            target_date = date.today()
        
        alerts = []
        
        try:
            # 查询错误率数据
            stmt = select(
                ModelUsageDaily.model_id,
                ModelConfiguration.name.label('model_name'),
                ModelUsageDaily.request_count,
                ModelUsageDaily.success_count,
                ModelUsageDaily.error_count
            ).select_from(
                ModelUsageDaily.join(ModelConfiguration)
            ).where(
                and_(
                    ModelUsageDaily.usage_date == target_date,
                    ModelUsageDaily.request_count > 0
                )
            )
            
            result = await self.db.execute(stmt)
            usage_data = result.all()
            
            error_threshold = self.thresholds['error_rate_threshold']
            
            for row in usage_data:
                if row.request_count == 0:
                    continue
                
                error_rate = row.error_count / row.request_count
                
                if error_rate > error_threshold:
                    severity = AlertSeverity.CRITICAL if error_rate > error_threshold * 2 else AlertSeverity.HIGH
                    
                    alert = Alert(
                        alert_type=AlertType.ERROR_RATE,
                        severity=severity,
                        title="错误率过高",
                        message=f"模型 {row.model_name} 的错误率过高",
                        model_id=row.model_id,
                        model_name=row.model_name,
                        current_value=error_rate,
                        threshold_value=error_threshold,
                        metadata={
                            'total_requests': row.request_count,
                            'success_count': row.success_count,
                            'error_count': row.error_count,
                            'error_rate_percentage': round(error_rate * 100, 2)
                        }
                    )
                    alerts.append(alert)
            
            # 发送告警
            for alert in alerts:
                await self.send_alert(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查错误率失败: {str(e)}", exc_info=True)
            return []
    
    async def run_all_checks(self, target_date: date = None) -> Dict[str, List[Alert]]:
        """
        运行所有检查
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            Dict[str, List[Alert]]: 按检查类型分组的告警列表
        """
        results = {}
        
        try:
            results['usage_anomalies'] = await self.check_usage_anomalies(target_date)
            results['cost_limits'] = await self.check_cost_limits(target_date)
            results['error_rates'] = await self.check_error_rates(target_date)
            
            total_alerts = sum(len(alerts) for alerts in results.values())
            self.logger.info(f"监控检查完成，共发现 {total_alerts} 个告警")
            
            return results
            
        except Exception as e:
            self.logger.error(f"运行监控检查失败: {str(e)}", exc_info=True)
            return results
