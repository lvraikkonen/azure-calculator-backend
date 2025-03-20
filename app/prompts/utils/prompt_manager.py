"""
提示词管理器
负责加载、组装和管理提示词模板
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from app.core.logging import get_logger
from app.prompts.utils.template_engine import template_engine

logger = get_logger(__name__)

class PromptType(Enum):
    """提示词类型枚举"""
    ADVISOR = "system/advisor.j2"
    INTENT_ANALYZER = "system/intent_analyzer.j2"


class PromptManager:
    """提示词管理器类"""
    
    def __init__(self):
        """初始化提示词管理器"""
        logger.info("提示词管理器初始化")
    
    def get_advisor_prompt(self, product_info: str, **kwargs) -> str:
        """
        获取Azure云服务成本计算器AI顾问助手的系统提示词
        
        Args:
            product_info: 产品信息文本
            **kwargs: 其他上下文变量
            
        Returns:
            str: 渲染后的系统提示词
        """
        variables = {
            "product_info": product_info,
            **kwargs
        }
        
        logger.debug(f"生成顾问提示词 | 变量数量: {len(variables)}")
        return template_engine.render(PromptType.ADVISOR.value, variables)
    
    def get_intent_analyzer_prompt(self, **kwargs) -> str:
        """
        获取意图分析器的系统提示词
        
        Args:
            **kwargs: 上下文变量
            
        Returns:
            str: 渲染后的系统提示词
        """
        logger.debug("生成意图分析器提示词")
        return template_engine.render(PromptType.INTENT_ANALYZER.value, kwargs)
    
    def compose_prompt(self, base_template: str, components: List[str], variables: Dict[str, Any]) -> str:
        """
        组合多个提示词组件
        
        Args:
            base_template: 基础模板路径
            components: 组件模板路径列表
            variables: 模板变量
            
        Returns:
            str: 组合后的提示词
        """
        result = template_engine.render(base_template, variables)
        
        for component in components:
            component_text = template_engine.render(component, variables)
            result += "\n\n" + component_text
        
        return result
    
    def get_custom_prompt(self, template_path: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        获取自定义提示词模板
        
        Args:
            template_path: 模板路径
            variables: 模板变量
            
        Returns:
            str: 渲染后的提示词
        """
        return template_engine.render(template_path, variables)


# 创建全局提示词管理器实例
prompt_manager = PromptManager()