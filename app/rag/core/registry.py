"""
RAG组件注册表 - 提供可插拔组件架构的核心
"""
from typing import Dict, Any, Type, Optional, List, Callable
import inspect
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGComponentRegistry:
    """RAG组件注册表 - 单例模式"""
    
    # 组件类型定义
    EMBEDDER = "embedder"
    CHUNKER = "chunker" 
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    QUERY_TRANSFORMER = "query_transformer"
    GENERATOR = "generator"
    VECTOR_STORE = "vector_store"
    DOCUMENT_LOADER = "document_loader"
    
    # 所有支持的组件类型
    COMPONENT_TYPES = [
        EMBEDDER, CHUNKER, RETRIEVER, RERANKER, 
        QUERY_TRANSFORMER, GENERATOR, VECTOR_STORE, DOCUMENT_LOADER
    ]
    
    # 组件存储字典
    _components: Dict[str, Dict[str, Type]] = {
        component_type: {} for component_type in COMPONENT_TYPES
    }
    
    @classmethod
    def register(cls, component_type: str, name: str, component_class: Type) -> None:
        """
        注册组件
        
        Args:
            component_type: 组件类型
            name: 组件名称
            component_class: 组件类
        """
        if component_type not in cls._components:
            raise ValueError(f"未知组件类型: {component_type}")
            
        cls._components[component_type][name] = component_class
        logger.info(f"已注册组件: {component_type}.{name}")
    
    @classmethod
    def get(cls, component_type: str, name: str) -> Type:
        """
        获取组件类
        
        Args:
            component_type: 组件类型
            name: 组件名称
            
        Returns:
            组件类
        """
        if component_type not in cls._components:
            raise ValueError(f"未知组件类型: {component_type}")
            
        if name not in cls._components[component_type]:
            raise ValueError(f"未注册的组件: {component_type}.{name}")
            
        return cls._components[component_type][name]
    
    @classmethod
    def create(cls, component_type: str, name: str, **kwargs) -> Any:
        """
        创建组件实例
        
        Args:
            component_type: 组件类型
            name: 组件名称
            **kwargs: 组件初始化参数
            
        Returns:
            组件实例
        """
        component_class = cls.get(component_type, name)
        
        # 检查哪些参数是组件初始化所必需的
        sig = inspect.signature(component_class.__init__)
        required_params = {
            name: param for name, param in sig.parameters.items()
            if name != 'self' and param.default == param.empty
        }
        
        # 检查必需参数是否都提供了
        missing_params = [name for name in required_params if name not in kwargs]
        if missing_params:
            raise ValueError(f"缺少必需参数: {', '.join(missing_params)}")
            
        # 创建组件实例
        try:
            return component_class(**kwargs)
        except Exception as e:
            logger.error(f"创建组件实例失败: {component_type}.{name}, 错误: {str(e)}")
            raise
    
    @classmethod
    def list_components(cls, component_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        列出已注册的组件
        
        Args:
            component_type: 可选的组件类型过滤器
            
        Returns:
            按类型分组的组件名称字典
        """
        if component_type:
            if component_type not in cls._components:
                raise ValueError(f"未知组件类型: {component_type}")
            return {component_type: list(cls._components[component_type].keys())}
        
        return {ctype: list(components.keys()) for ctype, components in cls._components.items()}
    
    @classmethod
    def component_info(cls, component_type: str, name: str) -> Dict[str, Any]:
        """
        获取组件信息
        
        Args:
            component_type: 组件类型
            name: 组件名称
            
        Returns:
            组件信息字典
        """
        component_class = cls.get(component_type, name)
        
        # 解析初始化参数
        sig = inspect.signature(component_class.__init__)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            params[param_name] = {
                "required": param.default == param.empty,
                "default": None if param.default == param.empty else param.default,
                "annotation": str(param.annotation) if param.annotation != param.empty else None
            }
        
        return {
            "name": name,
            "type": component_type,
            "class": component_class.__name__,
            "docstring": component_class.__doc__ or "",
            "parameters": params
        }


# 装饰器，方便注册组件
def register_component(component_type: str, name: str):
    """
    组件注册装饰器
    
    Args:
        component_type: 组件类型
        name: 组件名称
        
    Returns:
        装饰器函数
    """
    def decorator(cls):
        RAGComponentRegistry.register(component_type, name, cls)
        return cls
    return decorator
