import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from datetime import datetime, timezone
from app.core.logging import get_logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.schemas.chat import MessageCreate, MessageResponse, ConversationResponse, ConversationSummary
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import ModelType, ContextProvider, BaseLLMService
from app.services.intent_analysis import IntentAnalysisService
from app.services.product import ProductService
from app.services.llm.context_providers import ProductContextProvider

settings = get_settings()
logger = get_logger(__name__)


class ConversationService:
    """对话管理服务"""

    def __init__(self, db: AsyncSession, llm_factory: LLMServiceFactory,
                 product_service: Optional[ProductService] = None):
        """初始化对话服务"""
        self.db = db
        self.llm_factory = llm_factory
        self.product_service = product_service

        # 创建意图分析服务
        self.intent_analysis_service = IntentAnalysisService(llm_factory)

        # 添加意图缓存
        self.intent_cache = {}  # 格式: {conversation_id: {"intent": intent, "message_count": count, "last_message": str}}
        self.intent_cache_enabled = settings.INTENT_CACHE_ENABLED
        self.intent_cache_ttl = settings.INTENT_CACHE_TTL

        logger.info(
            f"对话服务初始化，意图缓存: {'已启用' if self.intent_cache_enabled else '已禁用'}, TTL: {self.intent_cache_ttl}")

    async def _get_context_providers(self) -> List[ContextProvider]:
        """获取上下文提供者列表"""
        providers = []

        # 如果有产品服务，添加产品上下文提供者
        if self.product_service:
            providers.append(ProductContextProvider(self.product_service))

        # TODO: 添加其他上下文提供者

        return providers

    async def _get_llm_service(self, model_type: str = None, model_name: str = None):
        """获取LLM服务实例"""
        model_type_enum = ModelType(model_type) if model_type else None
        return await self.llm_factory.get_service(model_type_enum, model_name)

    async def _should_analyze_intent(self, conversation_id: UUID, message: str) -> bool:
        """
        决定是否需要重新分析意图

        Args:
            conversation_id: 对话ID
            message: 用户消息内容

        Returns:
            bool: 是否需要分析意图
        """
        # 如果禁用了缓存，始终进行分析
        if not self.intent_cache_enabled:
            return True

        # 将UUID转为字符串作为缓存键
        cache_key = str(conversation_id)

        # 新对话总是分析
        if cache_key not in self.intent_cache:
            return True

        # 获取缓存的意图和计数
        cache_data = self.intent_cache[cache_key]
        message_count = cache_data.get("message_count", 0)
        last_message = cache_data.get("last_message", "")

        # 检查是否超过消息阈值
        if message_count >= self.intent_cache_ttl:
            return True

        # 消息较长可能是新话题
        if len(message) > 100:
            return True

        # 检测话题转换词
        topic_change_indicators = ["另外", "换个话题", "顺便问一下", "对了", "还有", "新问题", "请问"]
        if any(indicator in message for indicator in topic_change_indicators):
            return True

        # 如果与上一条消息差异较大，可能是新话题
        if last_message and len(message) > 15:
            # 简单的相似度检测 - 可以未来改进为更复杂的算法
            common_words = set(message.split()) & set(last_message.split())
            if len(common_words) < 2:
                return True

        return False  # 默认不重新分析

    async def _update_intent_cache(self, conversation_id: UUID, message: str, intent_analysis: Dict[str, Any]) -> None:
        """
        更新意图缓存

        Args:
            conversation_id: 对话ID
            message: 当前消息
            intent_analysis: 意图分析结果
        """
        if not self.intent_cache_enabled:
            return

        cache_key = str(conversation_id)
        # 如果之前有缓存，保留计数并增加
        message_count = 1
        if cache_key in self.intent_cache:
            message_count = self.intent_cache[cache_key].get("message_count", 0) + 1

        # 更新缓存
        self.intent_cache[cache_key] = {
            "intent": intent_analysis,
            "message_count": message_count,
            "last_message": message
        }

        # 日志记录缓存状态
        logger.debug(
            f"更新意图缓存: 对话={cache_key}, 消息计数={message_count}, 意图={intent_analysis.get('intent', '其他')}")

    async def _get_intent_analysis(self, conversation_id: UUID, message: str) -> Dict[str, Any]:
        """
        获取意图分析结果，如果需要则重新分析

        Args:
            conversation_id: 对话ID
            message: 用户消息

        Returns:
            Dict[str, Any]: 意图分析结果
        """
        # 检查是否需要分析
        if await self._should_analyze_intent(conversation_id, message):
            # 使用专用意图分析服务
            intent_analysis = await self.intent_analysis_service.analyze_intent(message)
            # 更新缓存
            await self._update_intent_cache(conversation_id, message, intent_analysis)
            logger.info(f"对话 {conversation_id} 的消息进行了意图分析: {intent_analysis.get('intent', '其他')}")
            return intent_analysis

        # 从缓存获取
        cache_key = str(conversation_id)
        intent_data = self.intent_cache.get(cache_key, {})
        intent_analysis = intent_data.get("intent", {"intent": "其他", "entities": {}})

        # 更新消息计数
        if self.intent_cache_enabled:
            intent_data["message_count"] = intent_data.get("message_count", 0) + 1
            self.intent_cache[cache_key] = intent_data

        logger.info(f"对话 {conversation_id} 使用缓存的意图分析: {intent_analysis.get('intent', '其他')}")
        return intent_analysis

    async def _generate_conversation_title(self, user_message: str, ai_response: str,
                                           llm_service: BaseLLMService) -> str:
        """
        基于对话内容生成摘要标题

        Args:
            user_message: 用户消息
            ai_response: AI回复
            llm_service: LLM服务实例

        Returns:
            str: 生成的标题
        """
        try:
            # 截取部分内容来生成标题
            user_content = user_message[:100] + ("..." if len(user_message) > 100 else "")
            ai_content = ai_response[:150] + ("..." if len(ai_response) > 150 else "")

            # 构建生成标题的提示
            prompt = f"""
            请为以下对话生成一个简短的标题（15字以内），清晰概括对话主题：
        
            用户: {user_content}
            AI: {ai_content}
        
            只返回标题文本，不要包含引号或其他格式。
            """

            # 使用低温度参数，确保生成简洁清晰的标题
            title_response = await llm_service.chat(
                prompt,
                [],
                [],
                {"temperature": 0.3, "max_tokens": 30}  # 使用低温度和限制输出长度
            )

            # 提取标题文本
            title = title_response.get("content", "").strip()

            # 清理标题中可能的多余字符
            title = title.replace("标题：", "").replace("《", "").replace("》", "").strip()

            # 截断过长标题
            if len(title) > 20:
                title = title[:17] + "..."

            # 如果没有成功生成标题，使用用户消息作为备选
            if not title:
                title = user_message[:15] + ("..." if len(user_message) > 15 else "")

            logger.info(f"已为对话生成标题: {title}")
            return title
        except Exception as e:
            logger.error(f"生成对话标题失败: {str(e)}")
            # 发生错误时返回用户消息的前几个字作为标题
            return user_message[:15] + ("..." if len(user_message) > 15 else "")

    async def create_conversation(self, user_id: UUID, title: str = "新对话") -> UUID:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题，默认"新对话"

        Returns:
            UUID: 新创建的对话ID
        """
        conversation = Conversation(
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        return conversation.id

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Optional[ConversationResponse]:
        """
        获取对话详情及消息

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于验证访问权限）

        Returns:
            Optional[ConversationResponse]: 对话详情，如不存在或无权限则返回None
        """
        # 查询对话基本信息
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        # 查询对话消息
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc())

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # 格式化消息
        message_responses = [
            MessageResponse(
                id=msg.id,
                conversation_id=conversation_id,
                content=msg.content,
                sender=msg.sender,
                timestamp=msg.timestamp,
                suggestions=msg.context.get("suggestions", []) if msg.context else [],
                recommendation=msg.context.get("recommendation") if msg.context else None,
                thinking=msg.context.get("thinking") if msg.context else None
            )
            for msg in messages
        ]

        # 构建响应
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses
        )

    async def _get_conversation_history(self, conversation_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        """获取对话历史，限制条数防止性能问题"""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.desc()).limit(limit)

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # 需要按时间正序返回，因此这里需要反转结果
        messages = list(reversed(messages))

        return [
            {
                "id": str(msg.id),
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]

    async def list_conversations(self, user_id: UUID) -> List[ConversationSummary]:
        """
        获取用户的对话列表

        Args:
            user_id: 用户ID

        Returns:
            List[ConversationSummary]: 对话摘要列表
        """
        # 获取用户所有对话
        stmt = select(Conversation).where(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc())

        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        summaries = []

        for conv in conversations:
            # 获取每个对话的消息数和最后一条消息
            messages_stmt = select(Message).where(
                Message.conversation_id == conv.id
            ).order_by(Message.timestamp.desc())

            result = await self.db.execute(messages_stmt)
            messages = result.scalars().all()

            last_message = messages[0].content if messages else None

            summaries.append(
                ConversationSummary(
                    id=conv.id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=len(messages),
                    last_message=last_message
                )
            )

        return summaries

    async def update_conversation_title(self, conversation_id: UUID, user_id: UUID, title: str) -> bool:
        """
        更新对话标题

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于验证访问权限）
            title: 新标题

        Returns:
            bool: 更新是否成功
        """
        # 确认对话属于该用户
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return False

        # 更新标题
        conversation.title = title
        conversation.updated_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def _update_conversation_if_needed(self,
                                             conversation: Optional[Conversation],
                                             conversation_id: UUID,
                                             is_new_conversation: bool,
                                             user_message: str,
                                             ai_response: str,
                                             llm_service: BaseLLMService) -> Dict[str, Any]:
        """更新会话信息，如需要则生成标题"""
        result = {"title_updated": False, "new_title": None}

        # 如果没有会话对象，需要获取
        if not conversation:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result_query = await self.db.execute(stmt)
            conversation = result_query.scalar_one_or_none()
            if not conversation:
                return result

        # 更新对话时间
        conversation.updated_at = datetime.utcnow()

        # 检查是否需要生成标题
        if is_new_conversation or conversation.title == "新对话":
            try:
                new_title = await self._generate_conversation_title(
                    user_message=user_message,
                    ai_response=ai_response,
                    llm_service=llm_service
                )
                conversation.title = new_title
                result["title_updated"] = True
                result["new_title"] = new_title
                logger.info(f"为对话 {conversation_id} 生成新标题: {new_title}")
            except Exception as e:
                logger.error(f"生成标题失败: {str(e)}")

        return result

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """
        删除对话

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于验证访问权限）

        Returns:
            bool: 删除是否成功
        """
        # 确认对话属于该用户
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return False

        # 删除对话（级联删除相关消息和反馈）
        await self.db.delete(conversation)
        await self.db.commit()

        return True

    async def _prepare_conversation_context(self, message_create: MessageCreate, user_id: UUID):
        """准备对话上下文，处理会话验证/创建和基本设置"""
        conversation_id = message_create.conversation_id
        is_new_conversation = False
        conversation = None

        if not conversation_id:
            conversation_id = await self.create_conversation(user_id)
            is_new_conversation = True
            logger.info(f"创建新会话: {conversation_id}")
        else:
            # 验证对话存在且属于该用户
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            result = await self.db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                raise ValueError("对话不存在或无权限访问")

        # 存储用户消息
        user_message_id = await self._store_message(
            conversation_id,
            message_create.content,
            "user",
            message_create.context
        )

        # 获取历史对话
        history = await self._get_conversation_history(conversation_id)

        # 获取上下文提供者
        context_providers = await self._get_context_providers()

        # 获取意图分析
        intent_analysis = await self._get_intent_analysis(conversation_id, message_create.content)

        # 构建额外上下文
        extra_context = message_create.context or {}
        extra_context["intent_analysis"] = intent_analysis

        # 获取LLM服务
        model_type = message_create.context.get("model_type") if message_create.context else None
        model_name = message_create.context.get("model_name") if message_create.context else None
        llm_service = await self._get_llm_service(model_type, model_name)

        return {
            "conversation_id": conversation_id,
            "conversation": conversation,
            "is_new_conversation": is_new_conversation,
            "history": history,
            "context_providers": context_providers,
            "extra_context": extra_context,
            "llm_service": llm_service,
            "intent_analysis": intent_analysis
        }

    async def add_message(self, message_create: MessageCreate, user_id: UUID) -> MessageResponse:
        """添加用户消息并获取AI回复"""
        try:
            # 1. 准备对话上下文
            context = await self._prepare_conversation_context(message_create, user_id)
            conversation_id = context["conversation_id"]
            conversation = context["conversation"]
            is_new_conversation = context["is_new_conversation"]
            llm_service = context["llm_service"]

            # 2. 调用LLM获取回复
            ai_response = await llm_service.chat(
                message_create.content,
                context["history"],
                context["context_providers"],
                context["extra_context"]
            )

            # 3. 构建消息响应
            message_response = MessageResponse(
                id=None,  # 稍后设置
                conversation_id=conversation_id,
                content=ai_response.get("content", ""),
                sender="ai",
                suggestions=ai_response.get("suggestions", []),
                recommendation=ai_response.get("recommendation"),
                thinking=ai_response.get("thinking")
            )

            # 4. 存储AI回复
            response_context = {}
            if message_response.suggestions:
                response_context["suggestions"] = message_response.suggestions
            if message_response.recommendation:
                response_context[
                    "recommendation"] = message_response.recommendation.dict() if message_response.recommendation else None
            if ai_response.get("thinking"):
                response_context["thinking"] = ai_response["thinking"]

            ai_message_id = await self._store_message(
                conversation_id,
                message_response.content,
                "ai",
                response_context
            )

            # 5. 更新对话信息
            title_info = await self._update_conversation_if_needed(
                conversation,
                conversation_id,
                is_new_conversation,
                message_create.content,
                message_response.content,
                llm_service
            )

            await self.db.commit()

            # 6. 设置响应属性
            message_response.id = ai_message_id
            if title_info["title_updated"]:
                message_response.title_updated = True
                message_response.new_title = title_info["new_title"]

            return message_response

        except ValueError as e:
            logger.warning(f"添加消息值错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}", exc_info=True)
            # 确保数据库会话回滚
            await self.db.rollback()
            raise RuntimeError(f"消息处理失败: {str(e)}")

    async def add_message_stream(self, message_create: MessageCreate, user_id: UUID) -> AsyncGenerator[str, None]:
        """添加用户消息并获取流式AI回复"""
        ai_message_id = None

        try:
            # 1. 准备对话上下文
            context = await self._prepare_conversation_context(message_create, user_id)
            conversation_id = context["conversation_id"]
            conversation = context["conversation"]
            is_new_conversation = context["is_new_conversation"]
            llm_service = context["llm_service"]

            # 2. 创建空的AI消息记录占位
            ai_message_id = await self._store_message(
                conversation_id,
                "",  # 初始内容为空
                "ai",
                {}
            )

            # 3. 发送包含会话ID的初始消息
            initial_message = {
                'id': str(ai_message_id),
                'conversation_id': str(conversation_id),
                'content': '',
                'is_new_conversation': is_new_conversation,
                'done': False
            }
            yield f"data: {json.dumps(initial_message)}\n\n"

            # 4. 启动流式生成
            full_content = ""
            reasoning_content = ""
            recommendations = None
            suggestions = []
            in_reasoning_mode = False

            # 处理流式响应
            async for chunk in llm_service.chat_stream(
                    message_create.content,
                    context["history"],
                    context["context_providers"],
                    context["extra_context"]
            ):
                # 错误处理
                if 'error' in chunk:
                    yield f"data: {json.dumps({'error': chunk['error'], 'done': True})}\n\n"
                    continue

                # 处理推理内容
                if 'reasoning_content' in chunk:
                    new_reasoning = chunk.get('reasoning_content', '')
                    if new_reasoning:
                        if not in_reasoning_mode:
                            in_reasoning_mode = True
                            yield f"data: {json.dumps({'thinking_mode': True, 'done': False})}\n\n"

                        reasoning_content += new_reasoning
                        yield f"data: {json.dumps({'thinking_chunk': new_reasoning, 'done': False})}\n\n"
                    continue

                # 模式处理
                if 'mode' in chunk:
                    mode = chunk['mode']
                    if mode == 'thinking_started':
                        in_reasoning_mode = True
                        yield f"data: {json.dumps({'thinking_mode': True, 'done': False})}\n\n"
                        continue
                    elif mode == 'thinking_ended':
                        thinking_content = chunk.get('thinking', '')
                        reasoning_content = thinking_content
                        in_reasoning_mode = False
                        yield f"data: {json.dumps({'thinking_mode': False, 'thinking': thinking_content, 'done': False})}\n\n"
                        continue
                    elif mode == 'thinking':
                        yield f"data: {json.dumps({'thinking_chunk': chunk.get('thinking', ''), 'done': False})}\n\n"
                        continue

                # 退出推理模式
                if 'content' in chunk and in_reasoning_mode:
                    in_reasoning_mode = False
                    yield f"data: {json.dumps({'thinking_mode': False, 'thinking': reasoning_content, 'done': False})}\n\n"

                # 处理内容块
                if 'content' in chunk:
                    content = chunk['content']
                    full_content += content
                    yield f"data: {json.dumps({'id': str(ai_message_id), 'content': content, 'conversation_id': str(conversation_id), 'done': False})}\n\n"

                # 建议和推荐
                if 'suggestions' in chunk:
                    suggestions = chunk['suggestions']
                if 'recommendation' in chunk:
                    recommendations = chunk['recommendation']

                await asyncio.sleep(0.01)  # 流控制

            # 5. 更新数据库中的消息
            response_context = {}
            if suggestions:
                response_context["suggestions"] = suggestions
            if recommendations:
                response_context["recommendation"] = recommendations
            if reasoning_content:
                response_context["thinking"] = reasoning_content

            await self._update_message(ai_message_id, full_content, response_context)

            # 6. 更新对话信息
            title_info = await self._update_conversation_if_needed(
                conversation,
                conversation_id,
                is_new_conversation,
                message_create.content,
                full_content,
                llm_service
            )

            await self.db.commit()

            # 7. 发送完成事件
            final_message = {
                'id': str(ai_message_id),
                'conversation_id': str(conversation_id),
                'content': full_content,
                'done': True,
                'suggestions': suggestions,
                'recommendation': recommendations,
                'thinking': reasoning_content
            }

            # 添加标题更新信息
            if title_info["title_updated"]:
                final_message['title_updated'] = True
                final_message['new_title'] = title_info["new_title"]

            yield f"data: {json.dumps(final_message)}\n\n"

        except Exception as e:
            # 错误处理
            error_message = {
                "error": str(e),
                "done": True,
                "conversation_id": str(conversation_id) if conversation_id else None
            }
            yield f"data: {json.dumps(error_message)}\n\n"

            # 记录错误并尝试更新消息
            logger.error(f"流式生成错误: {str(e)}", exc_info=True)
            if ai_message_id:
                try:
                    await self._update_message(ai_message_id, f"生成错误: {str(e)}", {"error": str(e)})
                    await self.db.commit()
                except Exception as db_error:
                    logger.critical(f"无法更新错误消息状态: {db_error}")
                    await self.db.rollback()

    async def _update_message(self, message_id: UUID, content: str, context: Dict[str, Any] = None) -> None:
        """更新现有消息"""
        stmt = select(Message).where(Message.id == message_id)
        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()

        if message:
            message.content = content
            if context:
                message.context = context
            await self.db.commit()
    
    async def _store_message(
        self, 
        conversation_id: UUID, 
        content: str, 
        sender: str,
        context: Dict[str, Any] = None
    ) -> UUID:
        """
        存储消息到数据库
        
        Args:
            conversation_id: 对话ID
            content: 消息内容
            sender: 发送者，'user' 或 'ai'
            context: 消息上下文，可选
            
        Returns:
            UUID: 消息ID
        """
        message = Message(
            conversation_id=conversation_id,
            content=content,
            sender=sender,
            timestamp=datetime.utcnow(),
            context=context or {}
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        return message.id

    async def _get_conversation_history(self, conversation_id: UUID) -> List[Dict[str, Any]]:
        """获取对话历史"""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc())

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]

    async def add_feedback(self, message_id: UUID, user_id: UUID, feedback_type: str, comment: Optional[str] = None) -> bool:
        """
        为消息添加反馈
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            feedback_type: 反馈类型
            comment: 反馈评论，可选
            
        Returns:
            bool: 添加是否成功
        """
        # 验证消息存在且用户有权访问
        stmt = select(Message).join(Conversation).where(
            Message.id == message_id,
            Conversation.user_id == user_id
        )
        
        result = await self.db.execute(stmt)
        message = result.scalar_one_or_none()
        
        if not message:
            return False
            
        # 查询现有反馈
        stmt = select(Feedback).where(Feedback.message_id == message_id)
        result = await self.db.execute(stmt)
        existing_feedback = result.scalar_one_or_none()
        
        # 添加或更新反馈
        if existing_feedback:
            existing_feedback.feedback_type = feedback_type
            existing_feedback.comment = comment
            existing_feedback.created_at = datetime.utcnow()
        else:
            feedback = Feedback(
                message_id=message_id,
                feedback_type=feedback_type,
                comment=comment,
                created_at=datetime.utcnow()
            )
            self.db.add(feedback)
            
        await self.db.commit()
        return True
