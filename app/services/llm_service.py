import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import MessageResponse, Recommendation
from app.services.product import ProductService
from app.prompts import prompt_manager, parameter_controller

settings = get_settings()
logger = get_logger(__name__)


class LLMService:
    """大语言模型服务，使用标准OpenAI API"""

    def __init__(self, product_service: Optional[ProductService] = None):
        """初始化LLM服务"""
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            # 如果设置了自定义基础URL，则使用它
            base_url=settings.OPENAI_API_BASE if hasattr(settings, 'OPENAI_API_BASE') and settings.OPENAI_API_BASE else None
        )
        self.model = settings.OPENAI_CHAT_MODEL
        self.product_service = product_service

    async def _build_system_prompt(self) -> str:
        """
        构建系统提示，包含产品信息
        """
        if self.product_service:
            # 获取产品数据用于构建知识库
            products = await self.product_service.get_all_products()
            product_info = "\n".join(
                [f"{p.name} (ID: {p.product_code}): {p.description}. 价格: {p.price} {p.price_unit}." 
                 for p in products]
            )
        else:
            product_info = "未能获取产品信息，请稍后再试。"

        # 使用提示词管理器获取渲染后的提示词
        return prompt_manager.get_advisor_prompt(product_info=product_info)

    def _format_conversation_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """格式化对话历史为OpenAI对话格式"""
        return [
            {"role": "user" if msg["sender"] == "user" else "assistant", "content": msg["content"]}
            for msg in messages
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def chat(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> MessageResponse:
        """
        调用LLM进行对话
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史记录
            
        Returns:
            MessageResponse: 包含AI回复的消息响应对象
        """
        try:
            # 首先分析用户意图（这是一种简化的方法，实际可能需要更高效的方式）
            intent_analysis = await self.analyze_user_input(user_message)
            intent = intent_analysis.get("intent", "其他")
            
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
            
            # 获取系统提示，并传入温度参数
            system_prompt = await self._build_system_prompt()
            
            # 构建消息数组
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                messages.extend(self._format_conversation_history(conversation_history))
                
            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"发送到LLM的消息总数: {len(messages)} | 意图: {intent} | 温度: {params['temperature']}")
            
            # 调用LLM API - 使用动态参数
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **params
            )
            
            # 解析响应
            ai_message = response.choices[0].message.content
            return self._parse_ai_response(ai_message)
            
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"AI服务暂时不可用: {str(e)}")

    def _parse_ai_response(self, response_text: str) -> MessageResponse:
        """
        解析LLM响应，提取结构化数据
        """
        try:
            # 尝试找到并解析JSON
            json_match = response_text.strip().find('{')
            if json_match != -1:
                json_str = response_text[json_match:]
                parsed_data = json.loads(json_str)
                
                # 提取推荐
                recommendation = None
                if "recommendation" in parsed_data and parsed_data["recommendation"]:
                    recommendation = Recommendation(**parsed_data["recommendation"])
                
                # 构建响应
                message_content = parsed_data.get("message", response_text)
                suggestions = parsed_data.get("suggestions", [])
                
                return MessageResponse(
                    id=None,  # ID会在DAO层生成
                    conversation_id=None,  # 会话ID会在服务层设置
                    content=message_content,
                    sender="ai",
                    suggestions=suggestions,
                    recommendation=recommendation
                )
            
            # 如果无法解析JSON，返回原始文本响应
            return MessageResponse(
                id=None,
                conversation_id=None,
                content=response_text,
                sender="ai",
                suggestions=[],
                recommendation=None
            )
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {str(e)}", exc_info=True)
            # 回退到纯文本响应
            return MessageResponse(
                id=None,
                conversation_id=None,
                content=response_text,
                sender="ai",
                suggestions=[],
                recommendation=None
            )

    async def chat_stream(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用LLM进行对话
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史记录
            
        Yields:
            Dict[str, Any]: 包含部分内容、建议或推荐的字典
        """
        try:
            # 首先分析用户意图
            intent_analysis = await self.analyze_user_input(user_message)
            intent = intent_analysis.get("intent", "其他")
            
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
            system_prompt = await self._build_system_prompt()
            
            # 构建消息数组
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                messages.extend(self._format_conversation_history(conversation_history))
                
            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"发送到LLM的流式请求，消息总数: {len(messages)} | 意图: {intent} | 温度: {params['temperature']}")
            
            # 调用LLM API - 启用流式输出, 使用动态参数
            stream_params = {**params, "stream": True}  # 添加流式参数
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **stream_params
            )
            
            # 处理流式响应
            buffer = ""
            recommendation = None
            suggestions = []
            json_started = False
            json_buffer = ""
            
            async for chunk in stream:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # 如果delta有内容
                if delta.content:
                    content = delta.content
                    buffer += content
                    
                    # 检测JSON开始
                    if "{" in content and not json_started:
                        json_started = True
                        json_buffer = content[content.find("{"):]
                    # JSON已经开始，继续收集
                    elif json_started:
                        json_buffer += content
                    
                    # 尝试解析收集到的JSON
                    if json_started and json_buffer.count('{') == json_buffer.count('}') and json_buffer[-1] == '}':
                        try:
                            parsed_json = json.loads(json_buffer)
                            if 'recommendation' in parsed_json:
                                recommendation = parsed_json['recommendation']
                            if 'suggestions' in parsed_json:
                                suggestions = parsed_json['suggestions']
                            json_started = False
                            json_buffer = ""
                        except:
                            # 如果解析失败，可能JSON还不完整
                            pass
                    
                    # 只产出文本内容部分
                    yield {"content": content}
                    
            # 流结束后，如果有提取到建议或推荐，则输出
            if suggestions:
                yield {"suggestions": suggestions}
            if recommendation:
                yield {"recommendation": recommendation}
                
            # 如果没有从文本中提取到结构化数据，尝试从完整缓冲区解析
            if not suggestions and not recommendation and buffer:
                extracted_data = self._extract_structured_data(buffer)
                if 'suggestions' in extracted_data:
                    yield {"suggestions": extracted_data['suggestions']}
                if 'recommendation' in extracted_data:
                    yield {"recommendation": extracted_data['recommendation']}
                    
        except Exception as e:
            logger.error(f"流式LLM调用失败: {str(e)}", exc_info=True)
            yield {"error": f"AI服务暂时不可用: {str(e)}"}
            
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取结构化数据（推荐和建议）
        """
        result = {}
        
        # 尝试提取JSON
        json_match = re.search(r'({[\s\S]*})', text)
        if json_match:
            try:
                parsed_data = json.loads(json_match.group(1))
                if 'recommendation' in parsed_data:
                    result['recommendation'] = parsed_data['recommendation']
                if 'suggestions' in parsed_data:
                    result['suggestions'] = parsed_data['suggestions']
                return result
            except:
                pass
                
        # 如果JSON提取失败，尝试使用正则表达式提取建议
        suggestions = re.findall(r'(?:建议|问题)[:：]\s*(.+?)(?=\n|$)', text)
        if suggestions:
            result['suggestions'] = suggestions
            
        return result
    
    async def analyze_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        分析用户输入，识别意图和实体
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            Dict: 包含意图和实体的分析结果
        """
        try:
            # 获取意图分析器提示词
            system_prompt = prompt_manager.get_intent_analyzer_prompt()
            
            # 构建分析提示
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {"role": "user", "content": user_input}
            ]
            
            # 调用LLM API进行分析 - 使用模型名称而非部署名称
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # 低温度以获得更确定性的结果
                max_tokens=500
            )
            
            # 解析响应
            analysis_text = response.choices[0].message.content
            
            try:
                # 尝试解析JSON响应
                return json.loads(analysis_text)
            except json.JSONDecodeError:
                logger.warning(f"分析结果不是有效的JSON: {analysis_text}")
                return {"intent": "其他", "entities": {}}
                
        except Exception as e:
            logger.error(f"分析用户输入失败: {str(e)}", exc_info=True)
            return {"intent": "其他", "entities": {}}