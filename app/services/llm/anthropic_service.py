import json
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import BaseLLMService, ContextProvider, ModelType, ModelCapability
from app.prompts import prompt_manager, parameter_controller

settings = get_settings()
logger = get_logger(__name__)


class AnthropicService(BaseLLMService):
    """Anthropic Claude服务实现"""

    def __init__(self, model_name=None, api_key=None):
        """初始化Anthropic服务"""
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model_name = model_name or settings.ANTHROPIC_MODEL

        # 初始化客户端
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

        # 确定模型能力
        self._capabilities = [ModelCapability.TEXT]

        # Claude 3 Opus和Haiku支持推理能力
        if any(x in self.model_name.lower() for x in ['opus', 'sonnet-3']):
            self._capabilities.append(ModelCapability.REASONING)

        # Claude 3多模态支持
        if 'claude-3' in self.model_name.lower():
            self._capabilities.append(ModelCapability.IMAGE_UNDERSTANDING)

        logger.info(f"初始化Anthropic服务: {self.model_name}, 能力: {self._capabilities}")

    @property
    def capabilities(self) -> List[ModelCapability]:
        return self._capabilities

    @property
    def model_type(self) -> ModelType:
        return ModelType.ANTHROPIC

    async def _build_system_prompt(self, context_providers: List[ContextProvider] = None) -> str:
        """构建系统提示，基于上下文提供者"""
        context_dict = {}

        if context_providers:
            for provider in context_providers:
                context = await provider.get_context()
                context_dict[provider.provider_name] = context

        # 使用提示词管理器获取渲染后的提示词
        product_info = context_dict.get("product_context", "未提供产品信息")
        knowledge_base = context_dict.get("knowledge_base", "")

        # 构建额外指令
        additional_instructions = ""
        if knowledge_base:
            additional_instructions += f"\n参考以下知识进行回答:\n{knowledge_base}"

        # 获取提示词
        return prompt_manager.get_advisor_prompt(
            product_info=product_info,
            additional_instructions=additional_instructions
        )

    def _format_conversation_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化对话历史为Anthropic消息格式"""
        formatted_messages = []

        for msg in messages:
            role = "user" if msg["sender"] == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg["content"]
            })

        return formatted_messages

    async def chat(self,
                   user_message: str,
                   conversation_history: List[Dict[str, Any]] = None,
                   context_providers: List[ContextProvider] = None,
                   extra_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用Anthropic进行对话"""
        try:
            extra_context = extra_context or {}

            # 使用传入的意图分析，现在必须由调用者提供
            intent_analysis = extra_context.get("intent_analysis", {"intent": "其他", "entities": {}})
            intent = intent_analysis.get("intent", "其他")

            logger.debug(f"流式对话使用意图: {intent}, 来源: 外部预分析")

            # 确定上下文特征
            context_features = {
                "detailed": "详细" in user_message or "具体" in user_message,
                "technical": any(term in user_message for term in ["配置", "架构", "技术", "原理"]),
                "first_time": conversation_history is None or len(conversation_history) <= 2
            }

            # 获取动态参数
            params = parameter_controller.get_parameters(
                intent=intent,
                query_length=len(user_message),
                context_features=context_features
            )

            # 获取系统提示
            system_prompt = await self._build_system_prompt(context_providers)

            # 构建消息数组
            messages = []

            if conversation_history:
                messages.extend(self._format_conversation_history(conversation_history))

            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})

            logger.info(f"发送到Anthropic的消息总数: {len(messages)} | 意图: {intent} | 温度: {params['temperature']}")

            # 调用Anthropic API
            response = await self.client.messages.create(
                model=self.model_name,
                system=system_prompt,
                messages=messages,
                temperature=params['temperature'],
                max_tokens=params.get('max_tokens', 2000)
            )

            # 解析响应
            ai_message = response.content[0].text
            return self._parse_ai_response(ai_message)

        except Exception as e:
            logger.error(f"Anthropic调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"AI服务暂时不可用: {str(e)}")

    async def chat_stream(self,
                          user_message: str,
                          conversation_history: List[Dict[str, Any]] = None,
                          context_providers: List[ContextProvider] = None,
                          extra_context: Dict[str, Any] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用Anthropic进行对话"""
        try:
            extra_context = extra_context or {}

            # 使用传入的意图分析，现在必须由调用者提供
            intent_analysis = extra_context.get("intent_analysis", {"intent": "其他", "entities": {}})
            intent = intent_analysis.get("intent", "其他")

            logger.debug(f"流式对话使用意图: {intent}, 来源: 外部预分析")

            # 确定上下文特征
            context_features = {
                "detailed": "详细" in user_message or "具体" in user_message,
                "technical": any(term in user_message for term in ["配置", "架构", "技术", "原理"]),
                "first_time": conversation_history is None or len(conversation_history) <= 2
            }

            # 获取动态参数
            params = parameter_controller.get_parameters(
                intent=intent,
                query_length=len(user_message),
                context_features=context_features
            )

            # 获取系统提示
            system_prompt = await self._build_system_prompt(context_providers)

            # 构建消息数组
            messages = []

            if conversation_history:
                messages.extend(self._format_conversation_history(conversation_history))

            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})

            logger.info(
                f"发送到Anthropic的流式请求，消息总数: {len(messages)} | 意图: {intent} | 温度: {params['temperature']}")

            # 调用Anthropic API - 启用流式输出
            with await self.client.messages.stream(
                    model=self.model_name,
                    system=system_prompt,
                    messages=messages,
                    temperature=params['temperature'],
                    max_tokens=params.get('max_tokens', 2000)
            ) as stream:
                # 处理流式响应
                buffer = ""
                thinking_buffer = ""
                in_thinking = False

                async for chunk in stream:
                    if not chunk.delta.text:
                        continue

                    content = chunk.delta.text
                    buffer += content

                    # 处理推理模式
                    if "<thinking>" in content and not in_thinking:
                        in_thinking = True
                        thinking_start_index = buffer.find("<thinking>") + len("<thinking>")
                        thinking_buffer = buffer[thinking_start_index:]
                        # 从用户可见内容中移除thinking开始标记
                        buffer = buffer[:buffer.find("<thinking>")]

                        # 通知客户端进入推理模式
                        yield {"mode": "thinking_started"}
                        continue

                    if in_thinking and "</thinking>" in content:
                        in_thinking = False
                        thinking_end_index = thinking_buffer.find("</thinking>")
                        if thinking_end_index != -1:
                            thinking_content = thinking_buffer[:thinking_end_index]
                            # 更新thinking_buffer移除已处理的内容
                            thinking_buffer = ""

                            # 通知客户端推理结束，并发送推理内容
                            yield {"mode": "thinking_ended", "thinking": thinking_content}

                            # 提取推理之后的内容添加到缓冲区
                            post_thinking = content[content.find("</thinking>") + len("</thinking>"):]
                            if post_thinking:
                                buffer += post_thinking
                                yield {"content": post_thinking}
                            continue

                    # 正常文本内容流式输出
                    if in_thinking:
                        thinking_buffer += content
                        yield {"mode": "thinking", "thinking": content}
                    else:
                        yield {"content": content}

                # 流结束后提取结构化数据
                extracted_data = self._extract_structured_data(buffer)
                if extracted_data:
                    if 'suggestions' in extracted_data:
                        yield {"suggestions": extracted_data['suggestions']}
                    if 'recommendation' in extracted_data:
                        yield {"recommendation": extracted_data['recommendation']}

        except Exception as e:
            logger.error(f"流式Anthropic调用失败: {str(e)}", exc_info=True)
            yield {"error": f"AI服务暂时不可用: {str(e)}"}

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """解析AI响应，提取结构化数据和推理内容"""
        try:
            result = {"content": response_text, "sender": "ai", "suggestions": [], "recommendation": None}

            # 提取thinking内容
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', response_text, re.DOTALL)
            if thinking_match:
                thinking_content = thinking_match.group(1).strip()
                # 从响应中移除thinking部分
                result["thinking"] = thinking_content
                result["content"] = re.sub(r'<thinking>.*?</thinking>', '', response_text, flags=re.DOTALL).strip()

            # 尝试提取JSON结构数据
            structured_data = self._extract_structured_data(result["content"])
            if structured_data:
                if 'message' in structured_data:
                    result["content"] = structured_data['message']
                if 'suggestions' in structured_data:
                    result["suggestions"] = structured_data['suggestions']
                if 'recommendation' in structured_data:
                    result["recommendation"] = structured_data['recommendation']

            return result
        except Exception as e:
            logger.error(f"解析AI响应失败: {str(e)}", exc_info=True)
            return {
                "content": response_text,
                "sender": "ai",
                "suggestions": [],
                "recommendation": None
            }

    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """从文本中提取结构化数据"""
        result = {}

        # 尝试多种方式提取JSON
        patterns = [
            r'```json\s*([\s\S]*?)```',  # Markdown JSON代码块
            r'{[\s\S]*?}',  # 任意JSON对象
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    json_str = match.strip()
                    # 对于第二个模式，确保它以{开始，}结束
                    if not json_str.startswith('{'):
                        json_str = '{' + json_str
                    if not json_str.endswith('}'):
                        json_str = json_str + '}'

                    parsed_data = json.loads(json_str)
                    # 提取关键字段
                    if 'recommendation' in parsed_data:
                        result['recommendation'] = parsed_data['recommendation']
                    if 'suggestions' in parsed_data:
                        result['suggestions'] = parsed_data['suggestions']
                    if 'message' in parsed_data:
                        result['message'] = parsed_data['message']

                    # 如果找到了有效的JSON，返回结果
                    if result:
                        return result
                except json.JSONDecodeError:
                    continue

        # 如果JSON提取失败，尝试使用正则表达式提取建议
        if 'suggestions' not in result:
            suggestions = re.findall(r'(?:建议|问题)[:：]\s*(.+?)(?=\n|$)', text)
            if suggestions:
                result['suggestions'] = suggestions

        return result

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