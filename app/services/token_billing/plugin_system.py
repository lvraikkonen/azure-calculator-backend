# app/services/token_billing/plugin_system.py

import asyncio
import importlib
import inspect
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Type, Callable, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger
from app.services.token_billing.monitoring import Alert

logger = get_logger(__name__)


class PluginType(Enum):
    """插件类型"""
    ALERT_HANDLER = "alert_handler"
    DATA_EXPORTER = "data_exporter"
    COST_CALCULATOR = "cost_calculator"
    USAGE_ANALYZER = "usage_analyzer"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"


class PluginStatus(Enum):
    """插件状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = None
    config_schema: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class PluginInfo:
    """插件信息"""
    metadata: PluginMetadata
    instance: Optional[Any] = None
    status: PluginStatus = PluginStatus.INACTIVE
    error_message: Optional[str] = None
    loaded_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化插件
        
        Args:
            config: 插件配置
        """
        self.config = config or {}
        self.logger = logger
        self._initialized = False
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """插件元数据"""
        pass
    
    async def initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            await self._initialize()
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"插件初始化失败 ({self.metadata.name}): {str(e)}", exc_info=True)
            return False
    
    async def _initialize(self):
        """子类实现的初始化逻辑"""
        pass
    
    async def cleanup(self):
        """清理资源"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


class AlertHandlerPlugin(BasePlugin):
    """告警处理器插件基类"""
    
    @abstractmethod
    async def handle_alert(self, alert: Alert) -> bool:
        """
        处理告警
        
        Args:
            alert: 告警对象
            
        Returns:
            bool: 是否处理成功
        """
        pass


class DataExporterPlugin(BasePlugin):
    """数据导出器插件基类"""
    
    @abstractmethod
    async def export_data(self, data: Dict[str, Any], 
                         export_format: str = "json") -> Union[str, bytes]:
        """
        导出数据
        
        Args:
            data: 要导出的数据
            export_format: 导出格式
            
        Returns:
            Union[str, bytes]: 导出的数据
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的导出格式"""
        pass


class IntegrationPlugin(BasePlugin):
    """集成插件基类"""
    
    @abstractmethod
    async def send_data(self, data: Dict[str, Any], 
                       endpoint: str = None) -> bool:
        """
        发送数据到外部系统
        
        Args:
            data: 要发送的数据
            endpoint: 目标端点
            
        Returns:
            bool: 是否发送成功
        """
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        """初始化插件管理器"""
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugin_types: Dict[PluginType, List[str]] = {
            plugin_type: [] for plugin_type in PluginType
        }
        self.logger = logger
        self._hooks: Dict[str, List[Callable]] = {}
    
    async def load_plugin(self, plugin_class: Type[BasePlugin], 
                         config: Optional[Dict[str, Any]] = None) -> bool:
        """
        加载插件
        
        Args:
            plugin_class: 插件类
            config: 插件配置
            
        Returns:
            bool: 是否加载成功
        """
        try:
            # 创建插件实例
            plugin_instance = plugin_class(config)
            metadata = plugin_instance.metadata
            
            # 检查依赖
            if not await self._check_dependencies(metadata.dependencies):
                self.logger.error(f"插件依赖检查失败: {metadata.name}")
                return False
            
            # 初始化插件
            if not await plugin_instance.initialize():
                self.logger.error(f"插件初始化失败: {metadata.name}")
                return False
            
            # 注册插件
            plugin_info = PluginInfo(
                metadata=metadata,
                instance=plugin_instance,
                status=PluginStatus.ACTIVE,
                loaded_at=datetime.now(timezone.utc),
                config=config
            )
            
            self.plugins[metadata.name] = plugin_info
            self.plugin_types[metadata.plugin_type].append(metadata.name)
            
            self.logger.info(f"插件加载成功: {metadata.name} v{metadata.version}")
            
            # 触发插件加载钩子
            await self._trigger_hook('plugin_loaded', plugin_info)
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载插件失败: {str(e)}", exc_info=True)
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否卸载成功
        """
        try:
            if plugin_name not in self.plugins:
                self.logger.warning(f"插件不存在: {plugin_name}")
                return False
            
            plugin_info = self.plugins[plugin_name]
            
            # 清理插件资源
            if plugin_info.instance:
                await plugin_info.instance.cleanup()
            
            # 从注册表中移除
            plugin_type = plugin_info.metadata.plugin_type
            if plugin_name in self.plugin_types[plugin_type]:
                self.plugin_types[plugin_type].remove(plugin_name)
            
            del self.plugins[plugin_name]
            
            self.logger.info(f"插件卸载成功: {plugin_name}")
            
            # 触发插件卸载钩子
            await self._trigger_hook('plugin_unloaded', plugin_info)
            
            return True
            
        except Exception as e:
            self.logger.error(f"卸载插件失败: {str(e)}", exc_info=True)
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[BasePlugin]: 插件实例
        """
        plugin_info = self.plugins.get(plugin_name)
        return plugin_info.instance if plugin_info else None
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """
        按类型获取插件
        
        Args:
            plugin_type: 插件类型
            
        Returns:
            List[BasePlugin]: 插件实例列表
        """
        plugin_names = self.plugin_types.get(plugin_type, [])
        plugins = []
        
        for name in plugin_names:
            plugin_info = self.plugins.get(name)
            if plugin_info and plugin_info.status == PluginStatus.ACTIVE:
                plugins.append(plugin_info.instance)
        
        return plugins
    
    def list_plugins(self) -> Dict[str, PluginInfo]:
        """列出所有插件"""
        return self.plugins.copy()
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否重新加载成功
        """
        if plugin_name not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_name]
        plugin_class = type(plugin_info.instance)
        config = plugin_info.config
        
        # 卸载现有插件
        await self.unload_plugin(plugin_name)
        
        # 重新加载
        return await self.load_plugin(plugin_class, config)
    
    async def execute_alert_handlers(self, alert: Alert) -> List[bool]:
        """
        执行所有告警处理器
        
        Args:
            alert: 告警对象
            
        Returns:
            List[bool]: 各处理器的执行结果
        """
        handlers = self.get_plugins_by_type(PluginType.ALERT_HANDLER)
        results = []
        
        for handler in handlers:
            try:
                result = await handler.handle_alert(alert)
                results.append(result)
            except Exception as e:
                self.logger.error(f"告警处理器执行失败 ({handler.metadata.name}): {str(e)}")
                results.append(False)
        
        return results
    
    async def export_data_with_plugins(self, data: Dict[str, Any], 
                                     export_format: str = "json") -> Dict[str, Any]:
        """
        使用插件导出数据
        
        Args:
            data: 要导出的数据
            export_format: 导出格式
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        exporters = self.get_plugins_by_type(PluginType.DATA_EXPORTER)
        results = {}
        
        for exporter in exporters:
            try:
                if export_format in exporter.get_supported_formats():
                    exported_data = await exporter.export_data(data, export_format)
                    results[exporter.metadata.name] = exported_data
            except Exception as e:
                self.logger.error(f"数据导出失败 ({exporter.metadata.name}): {str(e)}")
                results[exporter.metadata.name] = f"导出失败: {str(e)}"
        
        return results
    
    def register_hook(self, event: str, callback: Callable):
        """
        注册事件钩子
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    async def _trigger_hook(self, event: str, *args, **kwargs):
        """触发事件钩子"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"钩子执行失败 ({event}): {str(e)}")
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查插件依赖"""
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                self.logger.error(f"缺少依赖: {dep}")
                return False
        return True


# 全局插件管理器实例
_global_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager()
    return _global_plugin_manager


# 内置插件示例

class SlackAlertHandler(AlertHandlerPlugin):
    """Slack告警处理器插件示例"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="slack_alert_handler",
            version="1.0.0",
            description="发送告警到Slack",
            author="System",
            plugin_type=PluginType.ALERT_HANDLER,
            dependencies=["aiohttp"],
            config_schema={
                "webhook_url": {"type": "string", "required": True},
                "channel": {"type": "string", "default": "#alerts"}
            }
        )
    
    async def handle_alert(self, alert: Alert) -> bool:
        """发送告警到Slack"""
        try:
            webhook_url = self.config.get("webhook_url")
            if not webhook_url:
                self.logger.error("Slack webhook URL未配置")
                return False
            
            # 这里应该实现实际的Slack API调用
            self.logger.info(f"发送Slack告警: {alert.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Slack告警发送失败: {str(e)}")
            return False


class CSVExporter(DataExporterPlugin):
    """CSV导出器插件示例"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="csv_exporter",
            version="1.0.0",
            description="导出数据为CSV格式",
            author="System",
            plugin_type=PluginType.DATA_EXPORTER
        )
    
    async def export_data(self, data: Dict[str, Any], 
                         export_format: str = "csv") -> str:
        """导出为CSV格式"""
        import csv
        import io
        
        if export_format != "csv":
            raise ValueError("不支持的导出格式")
        
        output = io.StringIO()
        
        if 'records' in data and data['records']:
            writer = csv.DictWriter(output, fieldnames=data['records'][0].keys())
            writer.writeheader()
            writer.writerows(data['records'])
        
        return output.getvalue()
    
    def get_supported_formats(self) -> List[str]:
        return ["csv"]
