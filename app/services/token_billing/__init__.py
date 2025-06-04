# app/services/token_billing/__init__.py

from .token_cost_calculator import TokenCostCalculator
from .token_interceptor import (
    TokenUsageInterceptor, TokenUsageContext,
    get_global_interceptor, set_global_interceptor, track_llm_usage
)
from .monitoring import (
    TokenUsageMonitor, Alert, AlertSeverity, AlertType,
    LogAlertHandler, EmailAlertHandler, WebhookAlertHandler
)
from .cache_manager import (
    TokenCountCache, BatchTokenCounter, PerformanceMetrics,
    get_global_cache_manager, get_global_batch_counter, get_global_performance_metrics,
    optimized_count_tokens, optimized_count_tokens_batch
)
from .analytics_service import TokenUsageAnalytics, TrendAnalysis, UsagePattern, CostForecast
from .report_generator import CustomReportGenerator, ReportConfig, ReportType, ReportFormat
from .plugin_system import (
    PluginManager, BasePlugin, AlertHandlerPlugin, DataExporterPlugin, IntegrationPlugin,
    get_plugin_manager
)
from .config_manager import ConfigurationManager, ConfigItem, ConfigScope, ConfigType, get_config_manager

__all__ = [
    # 核心服务
    'TokenCostCalculator',
    'TokenUsageInterceptor',
    'TokenUsageContext',
    'get_global_interceptor',
    'set_global_interceptor',
    'track_llm_usage',

    # 监控和告警
    'TokenUsageMonitor',
    'Alert',
    'AlertSeverity',
    'AlertType',
    'LogAlertHandler',
    'EmailAlertHandler',
    'WebhookAlertHandler',

    # 缓存和性能优化
    'TokenCountCache',
    'BatchTokenCounter',
    'PerformanceMetrics',
    'get_global_cache_manager',
    'get_global_batch_counter',
    'get_global_performance_metrics',
    'optimized_count_tokens',
    'optimized_count_tokens_batch',

    # 高级分析
    'TokenUsageAnalytics',
    'TrendAnalysis',
    'UsagePattern',
    'CostForecast',

    # 报告生成
    'CustomReportGenerator',
    'ReportConfig',
    'ReportType',
    'ReportFormat',

    # 插件系统
    'PluginManager',
    'BasePlugin',
    'AlertHandlerPlugin',
    'DataExporterPlugin',
    'IntegrationPlugin',
    'get_plugin_manager',

    # 配置管理
    'ConfigurationManager',
    'ConfigItem',
    'ConfigScope',
    'ConfigType',
    'get_config_manager'
]
