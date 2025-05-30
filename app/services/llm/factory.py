from typing import Dict, Any, Optional, List, Type
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import BaseLLMService, ModelType, ContextProvider
from app.services.llm.openai_service import OpenAIService
from app.services.llm.anthropic_service import AnthropicService
from app.services.llm.deepseek_service import DeepseekService

settings = get_settings()
logger = get_logger(__name__)


class LLMServiceFactory:
    """LLM服务工厂，支持多种模型类型"""

    def __init__(self):
        """初始化LLM服务工厂"""
        # 服务类映射
        self.service_classes: Dict[ModelType, Type[BaseLLMService]] = {
            ModelType.OPENAI: OpenAIService,
            ModelType.AZURE_OPENAI: OpenAIService,  # 使用相同实现，配置不同
            ModelType.ANTHROPIC: AnthropicService,
            ModelType.DEEPSEEK: DeepseekService
        }

        self.model_features = {
            # Deepseek模型特性
            "deepseek-reasoner": {
                "is_reasoning": True
            },
            "deepseek-chat": {
                "is_reasoning": False
            }
        }

        # 服务实例缓存
        self.service_instances: Dict[str, BaseLLMService] = {}

        # 默认模型
        self.default_model_type = ModelType(settings.DEFAULT_MODEL_TYPE)

        logger.info(f"LLM服务工厂初始化完成，默认模型类型: {self.default_model_type}")

    def _get_model_features(self, model_name: str) -> Dict[str, Any]:
        """获取模型特性"""
        # 首先尝试精确匹配
        if model_name in self.model_features:
            return self.model_features[model_name]

        # 尝试部分匹配
        for key, features in self.model_features.items():
            if key in model_name:
                return features

        # 默认特性
        return {"is_reasoning": False}

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的模型信息

        Returns:
            List[Dict[str, Any]]: 模型信息列表
        """
        # 定义可用模型
        models = [
            {
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_V3_MODEL,
                "display_name": "Deepseek Chat",
                "description": "适合一般对话和推荐任务的基础模型",
                "supports_reasoning": False,
                "is_default": settings.DEFAULT_MODEL_TYPE == "deepseek" and settings.DEEPSEEK_V3_MODEL == settings.DEEPSEEK_V3_MODEL
            },
            {
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_R1_MODEL,
                "display_name": "Deepseek Reasoner",
                "description": "支持推理能力的高级模型，适合复杂问题分析",
                "supports_reasoning": True,
                "is_default": settings.DEFAULT_MODEL_TYPE == "deepseek" and settings.DEEPSEEK_R1_MODEL == settings.DEEPSEEK_R1_MODEL
            }
        ]

        # 如果配置了OpenAI模型，也添加到列表中
        if settings.OPENAI_API_KEY:
            models.append({
                "model_type": "openai",
                "model_name": settings.OPENAI_CHAT_MODEL,
                "display_name": f"OpenAI {settings.OPENAI_CHAT_MODEL}",
                "description": "OpenAI的对话模型",
                "supports_reasoning": False,
                "is_default": settings.DEFAULT_MODEL_TYPE == "openai"
            })

        return models

    async def create_service(self,
                             model_type: ModelType = None,
                             model_name: str = None,
                             config: Dict[str, Any] = None) -> BaseLLMService:
        """
        创建LLM服务实例

        Args:
            model_type: 模型类型枚举
            model_name: 具体模型名称
            config: 其他配置参数

        Returns:
            BaseLLMService: LLM服务实例
        """
        model_type = model_type or self.default_model_type
        config = config or {}

        # 如果未指定模型名称，根据类型选择默认模型
        if not model_name:
            if model_type == ModelType.DEEPSEEK:
                # 检查是否请求了推理能力
                if config.get("reasoning", False):
                    model_name = settings.DEEPSEEK_R1_MODEL
                else:
                    model_name = settings.DEEPSEEK_V3_MODEL
            elif model_type == ModelType.OPENAI:
                model_name = settings.OPENAI_CHAT_MODEL
            elif model_type == ModelType.ANTHROPIC:
                model_name = settings.ANTHROPIC_MODEL

        # 构建缓存键
        cache_key = f"{model_type.value}:{model_name or 'default'}"

        # 检查缓存中是否存在
        if cache_key in self.service_instances:
            return self.service_instances[cache_key]

        # 获取服务类
        service_class = self.service_classes.get(model_type)
        if not service_class:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 创建实例
        if model_type == ModelType.OPENAI:
            service = service_class(
                model_name=model_name,
                api_key=config.get('api_key'),
                base_url=config.get('base_url')
            )
        elif model_type == ModelType.AZURE_OPENAI:
            service = OpenAIService(
                model_name=model_name,
                api_key=config.get('api_key') or settings.AZURE_OPENAI_API_KEY,
                base_url=config.get('base_url') or settings.AZURE_OPENAI_ENDPOINT
            )
        elif model_type == ModelType.ANTHROPIC:
            service = service_class(
                model_name=model_name,
                api_key=config.get('api_key')
            )
        elif model_type == ModelType.DEEPSEEK:
            service = service_class(
                model_name=model_name,
                api_key=config.get('api_key'),
                base_url=config.get('base_url')
            )

        # 缓存实例
        self.service_instances[cache_key] = service

        logger.info(f"创建LLM服务实例: {cache_key}")
        return service

    async def get_service(self,
                          model_type: ModelType = None,
                          model_name: str = None,
                          reasoning: bool = False) -> BaseLLMService:
        """
        获取LLM服务实例（工厂方法）

        Args:
            model_type: 模型类型
            model_name: 具体模型名称
            reasoning: 是否需要推理能力

        Returns:
            BaseLLMService: LLM服务实例
        """
        # 配置参数
        config = {"reasoning": reasoning}

        # 如果请求了推理能力但未指定模型类型，自动选择支持推理的模型
        if reasoning and not model_type and not model_name:
            model_type = ModelType.DEEPSEEK
            model_name = settings.DEEPSEEK_REASONER_MODEL

        # 直接调用创建方法
        return await self.create_service(model_type, model_name, config)

    async def get_intent_analyzer_service(self) -> BaseLLMService:
        """
        获取专用于意图分析的服务实例

        Returns:
            BaseLLMService: 意图分析专用的LLM服务实例
        """
        model_type = ModelType(settings.INTENT_ANALYSIS_MODEL_TYPE)
        model_name = settings.INTENT_ANALYSIS_MODEL

        # 构建缓存键
        cache_key = f"intent_analyzer:{model_type.value}:{model_name}"

        # 检查缓存中是否存在
        if cache_key in self.service_instances:
            return self.service_instances[cache_key]

        # 创建新实例 - 使用配置的温度
        config = {
            "temperature": settings.INTENT_ANALYSIS_TEMPERATURE,
            "max_tokens": settings.INTENT_ANALYSIS_MAX_TOKENS
        }
        service = await self.create_service(model_type, model_name, config)

        # 添加到缓存
        self.service_instances[cache_key] = service

        logger.info(f"创建意图分析专用服务: {cache_key}")
        return service
