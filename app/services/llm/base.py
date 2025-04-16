from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from uuid import UUID


class ModelType(Enum):
    """模型类型枚举"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class ModelCapability(Enum):
    """模型能力枚举"""
    TEXT = auto()  # 文本处理
    REASONING = auto()  # 推理能力
    IMAGE_UNDERSTANDING = auto()  # 图像理解
    IMAGE_GENERATION = auto()  # 图像生成


class ContextProvider(ABC):
    """上下文提供者抽象接口"""

    @abstractmethod
    async def get_context(self) -> str:
        """获取上下文信息"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """上下文提供者名称"""
        pass


class BaseLLMService(ABC):
    """LLM服务基类"""

    @abstractmethod
    async def chat(self,
                   user_message: str,
                   conversation_history: List[Dict[str, Any]] = None,
                   context_providers: List[ContextProvider] = None) -> Dict[str, Any]:
        """基本对话方法"""
        pass

    @abstractmethod
    async def chat_stream(self,
                          user_message: str,
                          conversation_history: List[Dict[str, Any]] = None,
                          context_providers: List[ContextProvider] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式对话方法"""
        pass

    @abstractmethod
    async def analyze_intent(self,
                             user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[ModelCapability]:
        """获取模型能力列表"""
        pass

    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """获取模型类型"""
        pass

    @property
    def supports_reasoning(self) -> bool:
        """是否支持推理"""
        return ModelCapability.REASONING in self.capabilities

    @property
    def supports_image_understanding(self) -> bool:
        """是否支持图像理解"""
        return ModelCapability.IMAGE_UNDERSTANDING in self.capabilities

    @property
    def supports_image_generation(self) -> bool:
        """是否支持图像生成"""
        return ModelCapability.IMAGE_GENERATION in self.capabilities