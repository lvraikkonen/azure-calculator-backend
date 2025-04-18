import json
import re
from typing import Dict, Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import ModelType

settings = get_settings()
logger = get_logger(__name__)


class IntentAnalysisService:
    """专门的意图分析服务"""

    def __init__(self, llm_factory: LLMServiceFactory):
        """初始化意图分析服务"""
        self.llm_factory = llm_factory
        self.model_type = ModelType(settings.INTENT_ANALYSIS_MODEL_TYPE)
        self.model_name = settings.INTENT_ANALYSIS_MODEL
        self.temperature = settings.INTENT_ANALYSIS_TEMPERATURE
        self.max_tokens = settings.INTENT_ANALYSIS_MAX_TOKENS
        self.similarity_threshold = settings.INTENT_SIMILARITY_THRESHOLD

        logger.info(f"意图分析服务初始化: 模型类型={self.model_type.value}, "
                   f"模型名称={self.model_name}, 温度={self.temperature}")

    async def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            # 获取专用的意图分析服务实例
            llm_service = await self.llm_factory.get_intent_analyzer_service()

            # 调用服务API进行分析
            from app.prompts import prompt_manager
            system_prompt = prompt_manager.get_intent_analyzer_prompt()

            # 构建分析提示
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]

            # 调用LLM API进行分析，使用配置的参数
            client = llm_service._client if hasattr(llm_service, '_client') else llm_service.client
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            # 解析响应
            analysis_text = response.choices[0].message.content
            return self._extract_json_from_text(analysis_text) or {"intent": "其他", "entities": {}}

        except Exception as e:
            logger.error(f"分析用户输入失败: {str(e)}", exc_info=True)
            return {"intent": "其他", "entities": {}}

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取JSON对象"""
        try:
            # 清理可能包含的Markdown代码块标记
            cleaned_text = text

            # 移除可能的```json和```标记
            if "```json" in cleaned_text or "```" in cleaned_text:
                cleaned_text = re.sub(r'```json\s*', '', cleaned_text)
                cleaned_text = re.sub(r'```\s*', '', cleaned_text)

            # 尝试解析JSON响应
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # 尝试提取JSON内容 - 使用正则表达式
            json_match = re.search(r'({.*})', text.replace('\n', ''), re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            return None