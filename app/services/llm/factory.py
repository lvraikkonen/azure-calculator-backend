from typing import Dict, Any, List, Type
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import BaseLLMService, ModelType
from app.services.llm.openai_service import OpenAIService
from app.services.llm.anthropic_service import AnthropicService
from app.services.llm.deepseek_service import DeepseekService

settings = get_settings()
logger = get_logger(__name__)


class LLMServiceFactory:
    """LLM服务工厂，支持多种模型类型"""

    def __init__(self, model_config_service=None, performance_service=None):
        """
        初始化LLM服务工厂

        Args:
            model_config_service: 模型配置服务实例，可选
            performance_service: 性能测试服务实例，可选
        """
        # 模型配置服务（用于从数据库获取模型配置）
        self.model_config_service = model_config_service

        # 性能测试服务（用于智能模型选择）
        self.performance_service = performance_service

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

        logger.info(f"LLM服务工厂初始化完成，默认模型类型: {self.default_model_type}, 模型配置服务: {'已注入' if model_config_service else '未注入'}, 性能测试服务: {'已注入' if performance_service else '未注入'}")

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
        优先从数据库获取，如果没有配置服务则回退到硬编码列表

        Returns:
            List[Dict[str, Any]]: 模型信息列表
        """
        try:
            # 如果有模型配置服务，从数据库获取
            if self.model_config_service:
                logger.debug("从数据库获取可用模型列表")
                db_models = await self.model_config_service.list_models(
                    is_active=True,
                    is_visible=True
                )

                models = []
                for model in db_models:
                    model_info = self._convert_db_model_to_info(model)
                    models.append(model_info)

                logger.info(f"从数据库获取到 {len(models)} 个可用模型")

                # 如果数据库中有模型，返回数据库结果
                if models:
                    return models

                logger.warning("数据库中没有可用模型，回退到硬编码列表")

            # 回退到硬编码模型列表
            return self._get_hardcoded_models()

        except Exception as e:
            logger.error(f"获取可用模型失败: {str(e)}, 回退到硬编码列表")
            return self._get_hardcoded_models()

    def _convert_db_model_to_info(self, model) -> Dict[str, Any]:
        """将数据库模型转换为模型信息格式"""
        return {
            "id": str(model.id),
            "model_type": model.model_type,
            "model_name": model.model_name,
            "display_name": model.display_name,
            "description": model.description or "",
            "supports_reasoning": "reasoning" in (model.capabilities or []),
            "is_default": False,  # 可以后续根据配置确定
            "is_active": model.is_active,  # 添加is_active字段
            "is_custom": model.is_custom,
            "input_price": model.input_price,
            "output_price": model.output_price,
            "max_tokens": model.max_tokens,
            "capabilities": model.capabilities or []
        }

    def _get_hardcoded_models(self) -> List[Dict[str, Any]]:
        """获取硬编码的模型列表（回退方案）"""
        logger.debug("使用硬编码模型列表")

        # 定义可用模型
        models = [
            {
                "id": "hardcoded-deepseek-chat",  # 添加ID字段
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_V3_MODEL,
                "display_name": "Deepseek Chat",
                "description": "适合一般对话和推荐任务的基础模型",
                "supports_reasoning": False,
                "is_default": settings.DEFAULT_MODEL_TYPE == "deepseek" and settings.DEEPSEEK_V3_MODEL == settings.DEEPSEEK_V3_MODEL,
                "is_active": True,  # 添加is_active字段
                "is_custom": False,
                "input_price": 0.0,
                "output_price": 0.0,
                "max_tokens": 4096,
                "capabilities": ["chat", "completion"]
            },
            {
                "id": "hardcoded-deepseek-reasoner",  # 添加ID字段
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_R1_MODEL,
                "display_name": "Deepseek Reasoner",
                "description": "支持推理能力的高级模型，适合复杂问题分析",
                "supports_reasoning": True,
                "is_default": settings.DEFAULT_MODEL_TYPE == "deepseek" and settings.DEEPSEEK_R1_MODEL == settings.DEEPSEEK_R1_MODEL,
                "is_active": True,  # 添加is_active字段
                "is_custom": False,
                "input_price": 0.0,
                "output_price": 0.0,
                "max_tokens": 4096,
                "capabilities": ["chat", "completion", "reasoning"]
            }
        ]

        # 如果配置了OpenAI模型，也添加到列表中
        if settings.OPENAI_API_KEY:
            models.append({
                "id": "hardcoded-openai-chat",  # 添加ID字段
                "model_type": "openai",
                "model_name": settings.OPENAI_CHAT_MODEL,
                "display_name": f"OpenAI {settings.OPENAI_CHAT_MODEL}",
                "description": "OpenAI的对话模型",
                "supports_reasoning": False,
                "is_default": settings.DEFAULT_MODEL_TYPE == "openai",
                "is_active": True,  # 添加is_active字段
                "is_custom": False,
                "input_price": 0.0,
                "output_price": 0.0,
                "max_tokens": 4096,
                "capabilities": ["chat", "completion"]
            })

        return models

    async def create_service_from_model_id(self, model_id: str) -> BaseLLMService:
        """
        通过模型ID创建LLM服务实例

        Args:
            model_id: 数据库中的模型ID或硬编码模型ID

        Returns:
            BaseLLMService: LLM服务实例

        Raises:
            ValueError: 如果模型不存在或不可用
        """
        try:
            # 检查是否是硬编码模型ID
            if model_id.startswith("hardcoded-"):
                return await self._create_service_from_hardcoded_id(model_id)

            # 处理数据库模型ID
            if not self.model_config_service:
                raise ValueError("模型配置服务未注入，无法通过数据库模型ID创建服务")

            # 从数据库获取模型配置
            model_config = await self.model_config_service.get_model_by_id(model_id)
            if not model_config:
                raise ValueError(f"模型不存在: {model_id}")

            if not model_config.is_active:
                raise ValueError(f"模型未激活: {model_config.name}")

            # 解密API密钥
            from app.core.security import decrypt_api_key
            decrypted_api_key = None
            if model_config.api_key:
                try:
                    decrypted_api_key = decrypt_api_key(model_config.api_key)
                except Exception as e:
                    logger.error(f"API密钥解密失败: {str(e)}")
                    raise ValueError("API密钥解密失败")

            # 创建服务配置，包含模型能力信息
            config = {
                "api_key": decrypted_api_key,
                "base_url": model_config.base_url,
                "capabilities": model_config.capabilities or [],  # 传递数据库中的能力信息
                "model_id": model_id  # 传递模型ID用于日志和调试
            }

            # 通过现有方法创建服务
            model_type_enum = ModelType(model_config.model_type)
            return await self.create_service(
                model_type=model_type_enum,
                model_name=model_config.model_name,
                config=config
            )

        except Exception as e:
            logger.error(f"通过模型ID创建服务失败: {str(e)}")
            raise

    async def _create_service_from_hardcoded_id(self, model_id: str) -> BaseLLMService:
        """
        通过硬编码模型ID创建服务实例

        Args:
            model_id: 硬编码模型ID

        Returns:
            BaseLLMService: LLM服务实例
        """
        # 获取硬编码模型列表
        hardcoded_models = self._get_hardcoded_models()

        # 查找对应的模型
        model_info = None
        for model in hardcoded_models:
            if model["id"] == model_id:
                model_info = model
                break

        if not model_info:
            raise ValueError(f"硬编码模型不存在: {model_id}")

        # 创建服务配置
        config = {
            "capabilities": model_info.get("capabilities", []),
            "model_id": model_id
        }

        # 根据模型类型创建服务
        model_type_enum = ModelType(model_info["model_type"])
        return await self.create_service(
            model_type=model_type_enum,
            model_name=model_info["model_name"],
            config=config
        )

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
                base_url=config.get('base_url'),
                capabilities=config.get('capabilities'),
                model_id=config.get('model_id')
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

    async def select_optimal_model(
        self,
        task_type: str = "general",
        performance_requirements: Dict[str, Any] = None,
        fallback_to_default: bool = True
    ) -> str:
        """
        基于性能测试结果选择最优模型

        Args:
            task_type: 任务类型 (general, reasoning, speed, cost_effective)
            performance_requirements: 性能要求字典
            fallback_to_default: 是否回退到默认模型

        Returns:
            str: 最优模型ID，如果没有找到则返回None或默认模型ID
        """
        if not self.performance_service:
            logger.warning("性能测试服务未注入，无法进行智能模型选择")
            if fallback_to_default:
                return await self._get_default_model_id()
            return None

        try:
            # 设置默认性能要求
            requirements = performance_requirements or {}
            min_success_rate = requirements.get("min_success_rate", 90.0)
            max_response_time = requirements.get("max_response_time", 5000)  # 5秒
            max_cost = requirements.get("max_cost", None)

            # 根据任务类型确定排序指标
            if task_type == "speed":
                metric = "avg_response_time"
            elif task_type == "cost_effective":
                metric = "total_cost"
            elif task_type == "reasoning":
                metric = "tokens_per_second"  # 推理任务更关注生成质量
            else:
                metric = "avg_response_time"  # 默认优化响应时间

            logger.debug(f"智能模型选择: 任务类型={task_type}, 指标={metric}, 最小成功率={min_success_rate}")

            # 获取最佳性能模型
            best_models = await self.performance_service.get_best_performing_models(
                task_type=task_type if task_type != "general" else None,
                metric=metric,
                limit=10,  # 获取前10个候选
                min_success_rate=min_success_rate
            )

            if not best_models:
                logger.warning(f"没有找到符合要求的性能测试结果")
                if fallback_to_default:
                    return await self._get_default_model_id()
                return None

            # 应用额外的筛选条件
            filtered_models = []
            for model in best_models:
                # 检查响应时间要求
                if max_response_time and model.get("avg_response_time"):
                    if model["avg_response_time"] > max_response_time:
                        continue

                # 检查成本要求
                if max_cost and model.get("total_cost"):
                    if model["total_cost"] > max_cost:
                        continue

                # 验证模型是否仍然可用
                if await self._is_model_available(model["model_id"]):
                    filtered_models.append(model)

            if filtered_models:
                selected_model = filtered_models[0]
                logger.info(f"智能选择模型: {selected_model['model_id']}, 评分指标: {metric}={selected_model.get(metric)}")
                return selected_model["model_id"]

            logger.warning("所有候选模型都不满足要求")
            if fallback_to_default:
                return await self._get_default_model_id()
            return None

        except Exception as e:
            logger.error(f"智能模型选择失败: {str(e)}")
            if fallback_to_default:
                return await self._get_default_model_id()
            return None

    async def get_service_with_smart_selection(
        self,
        task_type: str = "general",
        performance_requirements: Dict[str, Any] = None,
        reasoning: bool = False
    ) -> BaseLLMService:
        """
        使用智能模型选择获取LLM服务实例

        Args:
            task_type: 任务类型
            performance_requirements: 性能要求
            reasoning: 是否需要推理能力

        Returns:
            BaseLLMService: LLM服务实例
        """
        try:
            # 如果需要推理能力，调整任务类型
            if reasoning:
                task_type = "reasoning"

            # 智能选择模型
            optimal_model_id = await self.select_optimal_model(
                task_type=task_type,
                performance_requirements=performance_requirements,
                fallback_to_default=True
            )

            if optimal_model_id:
                # 尝试通过模型ID创建服务
                try:
                    return await self.create_service_from_model_id(optimal_model_id)
                except Exception as e:
                    logger.warning(f"通过智能选择的模型ID创建服务失败: {str(e)}, 回退到传统方式")

            # 回退到传统方式
            return await self.get_service(reasoning=reasoning)

        except Exception as e:
            logger.error(f"智能服务选择失败: {str(e)}, 回退到传统方式")
            return await self.get_service(reasoning=reasoning)

    async def _get_default_model_id(self) -> str:
        """获取默认模型ID"""
        if not self.model_config_service:
            return None

        try:
            # 获取默认模型（第一个激活的模型）
            models = await self.model_config_service.list_models(
                is_active=True,
                limit=1
            )

            if models:
                return str(models[0].id)

            return None

        except Exception as e:
            logger.error(f"获取默认模型ID失败: {str(e)}")
            return None

    async def _is_model_available(self, model_id: str) -> bool:
        """检查模型是否可用"""
        if not self.model_config_service:
            return False

        try:
            model = await self.model_config_service.get_model_by_id(model_id)
            return model is not None and model.is_active
        except Exception:
            return False
