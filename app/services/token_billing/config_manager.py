# app/services/token_billing/config_manager.py

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class ConfigScope(Enum):
    """配置作用域"""
    GLOBAL = "global"
    USER = "user"
    MODEL = "model"
    TENANT = "tenant"


class ConfigType(Enum):
    """配置类型"""
    SYSTEM = "system"
    ALERT = "alert"
    BUDGET = "budget"
    CACHE = "cache"
    MONITORING = "monitoring"
    PLUGIN = "plugin"


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    config_type: ConfigType
    scope: ConfigScope
    scope_id: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[Any] = None
    validation_rules: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1


@dataclass
class ConfigValidationRule:
    """配置验证规则"""
    rule_type: str  # "range", "enum", "regex", "custom"
    parameters: Dict[str, Any]
    error_message: str


class ConfigurationManager:
    """动态配置管理器"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        初始化配置管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logger
        self._cache: Dict[str, ConfigItem] = {}
        self._watchers: Dict[str, List[Callable]] = {}
        self._validation_rules: Dict[str, List[ConfigValidationRule]] = {}
        
        # 初始化默认配置
        self._init_default_configs()
    
    def _init_default_configs(self):
        """初始化默认配置"""
        default_configs = [
            ConfigItem(
                key="token_billing.cache.enabled",
                value=True,
                config_type=ConfigType.CACHE,
                scope=ConfigScope.GLOBAL,
                description="是否启用Token计数缓存",
                default_value=True,
                validation_rules={"type": "boolean"}
            ),
            ConfigItem(
                key="token_billing.cache.ttl",
                value=3600,
                config_type=ConfigType.CACHE,
                scope=ConfigScope.GLOBAL,
                description="缓存TTL（秒）",
                default_value=3600,
                validation_rules={"type": "integer", "min": 60, "max": 86400}
            ),
            ConfigItem(
                key="token_billing.cache.max_size",
                value=10000,
                config_type=ConfigType.CACHE,
                scope=ConfigScope.GLOBAL,
                description="缓存最大条目数",
                default_value=10000,
                validation_rules={"type": "integer", "min": 100, "max": 100000}
            ),
            ConfigItem(
                key="token_billing.monitoring.enabled",
                value=True,
                config_type=ConfigType.MONITORING,
                scope=ConfigScope.GLOBAL,
                description="是否启用监控",
                default_value=True,
                validation_rules={"type": "boolean"}
            ),
            ConfigItem(
                key="token_billing.monitoring.check_interval",
                value=300,
                config_type=ConfigType.MONITORING,
                scope=ConfigScope.GLOBAL,
                description="监控检查间隔（秒）",
                default_value=300,
                validation_rules={"type": "integer", "min": 60, "max": 3600}
            ),
            ConfigItem(
                key="token_billing.alert.usage_threshold",
                value=3.0,
                config_type=ConfigType.ALERT,
                scope=ConfigScope.GLOBAL,
                description="使用量异常阈值倍数",
                default_value=3.0,
                validation_rules={"type": "float", "min": 1.0, "max": 10.0}
            ),
            ConfigItem(
                key="token_billing.alert.cost_daily_limit",
                value=100.0,
                config_type=ConfigType.ALERT,
                scope=ConfigScope.GLOBAL,
                description="日成本限制（美元）",
                default_value=100.0,
                validation_rules={"type": "float", "min": 0.0}
            ),
            ConfigItem(
                key="token_billing.alert.error_rate_threshold",
                value=0.1,
                config_type=ConfigType.ALERT,
                scope=ConfigScope.GLOBAL,
                description="错误率阈值",
                default_value=0.1,
                validation_rules={"type": "float", "min": 0.0, "max": 1.0}
            ),
            ConfigItem(
                key="token_billing.budget.enabled",
                value=False,
                config_type=ConfigType.BUDGET,
                scope=ConfigScope.GLOBAL,
                description="是否启用预算控制",
                default_value=False,
                validation_rules={"type": "boolean"}
            ),
            ConfigItem(
                key="token_billing.budget.monthly_limit",
                value=1000.0,
                config_type=ConfigType.BUDGET,
                scope=ConfigScope.GLOBAL,
                description="月度预算限制（美元）",
                default_value=1000.0,
                validation_rules={"type": "float", "min": 0.0}
            ),
            ConfigItem(
                key="token_billing.system.retention_days",
                value=90,
                config_type=ConfigType.SYSTEM,
                scope=ConfigScope.GLOBAL,
                description="数据保留天数",
                default_value=90,
                validation_rules={"type": "integer", "min": 7, "max": 365}
            )
        ]
        
        for config in default_configs:
            self._cache[self._get_cache_key(config.key, config.scope, config.scope_id)] = config
    
    def _get_cache_key(self, key: str, scope: ConfigScope, scope_id: Optional[str] = None) -> str:
        """生成缓存键"""
        if scope_id:
            return f"{scope.value}:{scope_id}:{key}"
        return f"{scope.value}:{key}"
    
    async def get_config(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL, 
                        scope_id: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            scope: 配置作用域
            scope_id: 作用域ID
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        cache_key = self._get_cache_key(key, scope, scope_id)
        
        # 先从缓存获取
        if cache_key in self._cache:
            return self._cache[cache_key].value
        
        # 从数据库获取
        if self.db:
            try:
                # 这里应该查询配置表，简化实现
                pass
            except Exception as e:
                self.logger.error(f"从数据库获取配置失败: {str(e)}")
        
        # 返回默认值
        return default
    
    async def set_config(self, key: str, value: Any, scope: ConfigScope = ConfigScope.GLOBAL,
                        scope_id: Optional[str] = None, description: Optional[str] = None) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            scope: 配置作用域
            scope_id: 作用域ID
            description: 配置描述
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 验证配置值
            if not await self._validate_config(key, value):
                return False
            
            cache_key = self._get_cache_key(key, scope, scope_id)
            
            # 获取现有配置或创建新配置
            if cache_key in self._cache:
                config_item = self._cache[cache_key]
                old_value = config_item.value
                config_item.value = value
                config_item.updated_at = datetime.now(timezone.utc)
                config_item.version += 1
            else:
                config_item = ConfigItem(
                    key=key,
                    value=value,
                    config_type=self._infer_config_type(key),
                    scope=scope,
                    scope_id=scope_id,
                    description=description,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                old_value = None
            
            # 更新缓存
            self._cache[cache_key] = config_item
            
            # 保存到数据库
            if self.db:
                await self._save_to_database(config_item)
            
            # 触发配置变更监听器
            await self._notify_watchers(key, old_value, value, scope, scope_id)
            
            self.logger.info(f"配置更新成功: {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置配置失败: {str(e)}", exc_info=True)
            return False
    
    async def get_configs_by_type(self, config_type: ConfigType, 
                                scope: ConfigScope = ConfigScope.GLOBAL,
                                scope_id: Optional[str] = None) -> Dict[str, Any]:
        """
        按类型获取配置
        
        Args:
            config_type: 配置类型
            scope: 配置作用域
            scope_id: 作用域ID
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        configs = {}
        
        for cache_key, config_item in self._cache.items():
            if (config_item.config_type == config_type and 
                config_item.scope == scope and
                config_item.scope_id == scope_id):
                configs[config_item.key] = config_item.value
        
        return configs
    
    async def delete_config(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL,
                          scope_id: Optional[str] = None) -> bool:
        """
        删除配置
        
        Args:
            key: 配置键
            scope: 配置作用域
            scope_id: 作用域ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            cache_key = self._get_cache_key(key, scope, scope_id)
            
            if cache_key in self._cache:
                old_value = self._cache[cache_key].value
                del self._cache[cache_key]
                
                # 从数据库删除
                if self.db:
                    await self._delete_from_database(key, scope, scope_id)
                
                # 触发配置变更监听器
                await self._notify_watchers(key, old_value, None, scope, scope_id)
                
                self.logger.info(f"配置删除成功: {key}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"删除配置失败: {str(e)}", exc_info=True)
            return False
    
    def watch_config(self, key: str, callback: Callable):
        """
        监听配置变更
        
        Args:
            key: 配置键
            callback: 回调函数
        """
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
    
    def unwatch_config(self, key: str, callback: Callable):
        """
        取消监听配置变更
        
        Args:
            key: 配置键
            callback: 回调函数
        """
        if key in self._watchers and callback in self._watchers[key]:
            self._watchers[key].remove(callback)
    
    async def _validate_config(self, key: str, value: Any) -> bool:
        """验证配置值"""
        try:
            # 获取验证规则
            rules = self._get_validation_rules(key)
            if not rules:
                return True
            
            for rule in rules:
                if not await self._apply_validation_rule(value, rule):
                    self.logger.error(f"配置验证失败: {key} = {value}, 规则: {rule}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证异常: {str(e)}")
            return False
    
    def _get_validation_rules(self, key: str) -> List[ConfigValidationRule]:
        """获取配置验证规则"""
        # 从缓存中查找配置项的验证规则
        for config_item in self._cache.values():
            if config_item.key == key and config_item.validation_rules:
                rules = []
                for rule_type, params in config_item.validation_rules.items():
                    if rule_type == "type":
                        rules.append(ConfigValidationRule(
                            rule_type="type",
                            parameters={"expected_type": params},
                            error_message=f"期望类型: {params}"
                        ))
                    elif rule_type in ["min", "max"]:
                        rules.append(ConfigValidationRule(
                            rule_type=rule_type,
                            parameters={"value": params},
                            error_message=f"{rule_type}: {params}"
                        ))
                return rules
        
        return []
    
    async def _apply_validation_rule(self, value: Any, rule: ConfigValidationRule) -> bool:
        """应用验证规则"""
        try:
            if rule.rule_type == "type":
                expected_type = rule.parameters["expected_type"]
                if expected_type == "boolean":
                    return isinstance(value, bool)
                elif expected_type == "integer":
                    return isinstance(value, int)
                elif expected_type == "float":
                    return isinstance(value, (int, float))
                elif expected_type == "string":
                    return isinstance(value, str)
            
            elif rule.rule_type == "min":
                return value >= rule.parameters["value"]
            
            elif rule.rule_type == "max":
                return value <= rule.parameters["value"]
            
            return True
            
        except Exception:
            return False
    
    async def _notify_watchers(self, key: str, old_value: Any, new_value: Any,
                             scope: ConfigScope, scope_id: Optional[str]):
        """通知配置变更监听器"""
        if key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(key, old_value, new_value, scope, scope_id)
                    else:
                        callback(key, old_value, new_value, scope, scope_id)
                except Exception as e:
                    self.logger.error(f"配置变更回调执行失败: {str(e)}")
    
    def _infer_config_type(self, key: str) -> ConfigType:
        """推断配置类型"""
        if "cache" in key:
            return ConfigType.CACHE
        elif "alert" in key:
            return ConfigType.ALERT
        elif "budget" in key:
            return ConfigType.BUDGET
        elif "monitoring" in key:
            return ConfigType.MONITORING
        elif "plugin" in key:
            return ConfigType.PLUGIN
        else:
            return ConfigType.SYSTEM
    
    async def _save_to_database(self, config_item: ConfigItem):
        """保存配置到数据库"""
        # 这里应该实现实际的数据库保存逻辑
        # 简化实现，仅记录日志
        self.logger.debug(f"保存配置到数据库: {config_item.key}")
    
    async def _delete_from_database(self, key: str, scope: ConfigScope, scope_id: Optional[str]):
        """从数据库删除配置"""
        # 这里应该实现实际的数据库删除逻辑
        # 简化实现，仅记录日志
        self.logger.debug(f"从数据库删除配置: {key}")
    
    async def export_configs(self, config_type: Optional[ConfigType] = None) -> Dict[str, Any]:
        """
        导出配置
        
        Args:
            config_type: 配置类型，为None则导出所有配置
            
        Returns:
            Dict[str, Any]: 配置数据
        """
        configs = {}
        
        for config_item in self._cache.values():
            if config_type is None or config_item.config_type == config_type:
                configs[config_item.key] = {
                    'value': config_item.value,
                    'type': config_item.config_type.value,
                    'scope': config_item.scope.value,
                    'scope_id': config_item.scope_id,
                    'description': config_item.description,
                    'version': config_item.version,
                    'updated_at': config_item.updated_at.isoformat() if config_item.updated_at else None
                }
        
        return configs
    
    async def import_configs(self, configs: Dict[str, Any]) -> bool:
        """
        导入配置
        
        Args:
            configs: 配置数据
            
        Returns:
            bool: 是否导入成功
        """
        try:
            for key, config_data in configs.items():
                await self.set_config(
                    key=key,
                    value=config_data['value'],
                    scope=ConfigScope(config_data.get('scope', 'global')),
                    scope_id=config_data.get('scope_id'),
                    description=config_data.get('description')
                )
            
            self.logger.info(f"配置导入成功: {len(configs)} 项")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导入失败: {str(e)}", exc_info=True)
            return False


# 全局配置管理器实例
_global_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """获取全局配置管理器"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
    return _global_config_manager


def set_config_manager(manager: ConfigurationManager):
    """设置全局配置管理器"""
    global _global_config_manager
    _global_config_manager = manager
