"""
动态参数控制模块
根据查询意图和上下文动态调整LLM参数
"""
from typing import Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class ParameterController:
    """LLM参数控制器"""
    
    def __init__(self):
        """初始化参数控制器"""
        # 意图到温度的映射 - 不同意图需要不同的创造性水平
        self.intent_temperature_map = {
            "推荐": 0.7,     # 推荐需要一定创造性
            "查询": 0.3,     # 查询需要精确性
            "比较": 0.5,     # 比较需要平衡
            "定价": 0.2,     # 定价需要高精确性
            "其他": 0.6      # 默认中等温度
        }
        
        # 上下文特征及其影响
        self.context_modifiers = {
            "detailed": 0.0,        # 如果需要细节，降低温度
            "creative": 0.2,        # 如果需要创意，增加温度
            "uncertain": 0.1,       # 如果信息不确定，稍微增加温度
            "technical": -0.1,      # 如果是技术性内容，降低温度
            "first_time": 0.1       # 如果是首次交互，稍微增加温度
        }
        
        logger.info("参数控制器初始化完成")
    
    def get_temperature(self, intent: str, context_features: Optional[Dict[str, bool]] = None) -> float:
        """
        根据意图和上下文特征计算合适的temperature值
        
        Args:
            intent: 查询意图，如"推荐"、"查询"等
            context_features: 上下文特征，如 {"detailed": True}
            
        Returns:
            float: 计算得到的temperature值，范围[0.1, 1.0]
        """
        # 从意图映射中获取基础温度
        base_temp = self.intent_temperature_map.get(intent, 0.6)
        
        # 应用上下文修饰器
        if context_features:
            for feature, is_present in context_features.items():
                if is_present and feature in self.context_modifiers:
                    base_temp += self.context_modifiers[feature]
        
        # 限制temperature在有效范围内
        final_temp = max(0.1, min(1.0, base_temp))
        
        logger.debug(f"动态Temperature计算 | 意图: {intent} | 最终值: {final_temp:.2f}")
        return final_temp
    
    def get_parameters(self, intent: str, query_length: int, context_features: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        获取完整的LLM参数集
        
        Args:
            intent: 查询意图
            query_length: 查询长度
            context_features: 上下文特征
            
        Returns:
            Dict[str, Any]: 参数字典
        """
        # 获取基础temperature
        temp = self.get_temperature(intent, context_features)
        
        # 根据查询长度和意图调整max_tokens
        base_tokens = 2000
        if query_length > 500:
            base_tokens = 3000
        if intent == "推荐" or intent == "比较":
            base_tokens += 500
            
        # 构建参数字典
        params = {
            "temperature": temp,
            "max_tokens": base_tokens,
            "top_p": 0.95 if temp > 0.5 else 0.85,
            "frequency_penalty": 0.2 if intent == "推荐" else 0,
            "presence_penalty": 0.2 if intent == "推荐" else 0,
        }
        
        logger.debug(f"生成LLM参数 | 意图: {intent} | 参数: {params}")
        return params


# 创建全局参数控制器实例
parameter_controller = ParameterController()