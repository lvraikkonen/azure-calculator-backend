import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.core.logging import get_logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.schemas.chat import MessageCreate, MessageResponse, ConversationResponse, ConversationSummary
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.base import ModelType, ContextProvider, BaseLLMService
from app.services.product import ProductService
from app.services.llm.context_providers import ProductContextProvider

logger = get_logger(__name__)


class ConversationService:
    """对话管理服务"""

    def __init__(self, db: AsyncSession, llm_factory: LLMServiceFactory,
                 product_service: Optional[ProductService] = None):
        """初始化对话服务"""
        self.db = db
        self.llm_factory = llm_factory
        self.product_service = product_service

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
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc)
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
        conversation.updated_at = datetime.now(tz=timezone.utc)

        await self.db.commit()
        return True

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

    async def add_message(self, message_create: MessageCreate, user_id: UUID) -> MessageResponse:
        """添加用户消息并获取AI回复"""
        # 获取或创建对话
        conversation_id = message_create.conversation_id
        is_new_conversation = False
        conversation = None

        if not conversation_id:
            conversation_id = await self.create_conversation(user_id)
            is_new_conversation = True
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

        # 获取LLM服务
        model_type = message_create.context.get("model_type") if message_create.context else None
        model_name = message_create.context.get("model_name") if message_create.context else None
        llm_service = await self._get_llm_service(model_type, model_name)

        # 调用LLM获取回复
        ai_response = await llm_service.chat(message_create.content, history, context_providers)

        # 构建消息响应
        message_response = MessageResponse(
            id=None,  # 稍后设置
            conversation_id=conversation_id,
            content=ai_response.get("content", ""),
            sender="ai",
            suggestions=ai_response.get("suggestions", []),
            recommendation=ai_response.get("recommendation"),
            thinking=ai_response.get("thinking")
        )

        # 存储AI回复
        context = {}
        if message_response.suggestions:
            context["suggestions"] = message_response.suggestions
        if message_response.recommendation:
            context[
                "recommendation"] = message_response.recommendation.dict() if message_response.recommendation else None
        if ai_response.get("thinking"):
            context["thinking"] = ai_response["thinking"]

        ai_message_id = await self._store_message(
            conversation_id,
            message_response.content,
            "ai",
            context
        )

        # 更新对话时间和获取完整对话对象（如果之前没有获取）
        if not conversation:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await self.db.execute(stmt)
            conversation = result.scalar_one()

        conversation.updated_at = datetime.utcnow()
        title_updated = False

        # 自动生成对话标题 - 条件：
        # 1. 至少有一轮对话（当前这轮加上之前的历史）
        # 2. 当前标题是默认的"新对话"
        if (len(history) >= 2 or (is_new_conversation and len(history) == 0)) and conversation.title == "新对话":
            # 调用辅助方法生成标题
            new_title = await self._generate_conversation_title(
                user_message=message_create.content,
                ai_response=message_response.content,
                llm_service=llm_service
            )
            conversation.title = new_title
            title_updated = True

        await self.db.commit()

        # 设置AI回复的ID
        message_response.id = ai_message_id

        # 在响应中包含标题更新信息
        if title_updated:
            message_response.title_updated = True
            message_response.new_title = conversation.title

        return message_response

    async def add_message_stream(self, message_create: MessageCreate, user_id: UUID) -> AsyncGenerator[str, None]:
        """添加用户消息并获取流式AI回复"""
        # 获取或创建对话
        logger.info(f"流式消息请求参数: {message_create}")
        conversation_id = message_create.conversation_id
        is_new_conversation = False
        conversation = None

        if not conversation_id:
            # 只有在未提供会话ID时才创建新会话
            logger.warning("请求中未提供会话ID，将创建新会话")
            conversation_id = await self.create_conversation(user_id)
            is_new_conversation = True
            logger.info(f"创建新会话: {conversation_id}")
        else:
            # 验证对话存在且属于该用户
            logger.info(f"请求中提供了会话ID: {conversation_id}，尝试使用现有会话")
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            result = await self.db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"提供的会话ID {conversation_id} 无效或无权访问，将创建新会话")
                conversation_id = await self.create_conversation(user_id)
                is_new_conversation = True
                logger.info(f"创建新会话: {conversation_id}")
            else:
                logger.info(f"使用现有会话: {conversation_id}")

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

        # 创建空的AI消息记录占位，稍后更新
        ai_message_id = await self._store_message(
            conversation_id,
            "",  # 初始内容为空
            "ai",
            {}
        )

        # 首先发送包含会话ID的初始消息
        initial_message = {
            'id': str(ai_message_id),
            'conversation_id': str(conversation_id),
            'content': '',
            'is_new_conversation': is_new_conversation,
            'done': False
        }
        yield f"data: {json.dumps(initial_message)}\n\n"

        # 获取LLM服务
        model_type = message_create.context.get("model_type") if message_create.context else None
        model_name = message_create.context.get("model_name") if message_create.context else None
        llm_service = await self._get_llm_service(model_type, model_name)

        # 启动流式生成
        full_content = ""
        reasoning_content = ""  # 直接用于收集推理内容
        recommendations = None
        suggestions = []
        in_reasoning_mode = False  # 用于跟踪状态

        try:
            # 从LLM服务获取流式响应
            async for chunk in llm_service.chat_stream(message_create.content, history, context_providers):
                # 处理错误情况
                if 'error' in chunk:
                    yield f"data: {json.dumps({'error': chunk['error'], 'done': True})}\n\n"
                    continue

                # 处理推理内容 - 基于官方示例
                if 'reasoning_content' in chunk:
                    new_reasoning = chunk.get('reasoning_content', '')
                    if new_reasoning:
                        # 第一次收到推理内容，通知客户端进入推理模式
                        if not in_reasoning_mode:
                            in_reasoning_mode = True
                            yield f"data: {json.dumps({'thinking_mode': True, 'done': False})}\n\n"

                        reasoning_content += new_reasoning
                        yield f"data: {json.dumps({'thinking_chunk': new_reasoning, 'done': False})}\n\n"
                    continue

                # 常规推理状态跟踪（用于兼容旧版接口）
                if 'mode' in chunk:
                    mode = chunk['mode']
                    if mode == 'thinking_started':
                        in_reasoning_mode = True
                        yield f"data: {json.dumps({'thinking_mode': True, 'done': False})}\n\n"
                        continue
                    elif mode == 'thinking_ended':
                        thinking_content = chunk.get('thinking', '')
                        reasoning_content = thinking_content  # 更新总推理内容
                        in_reasoning_mode = False
                        yield f"data: {json.dumps({'thinking_mode': False, 'thinking': thinking_content, 'done': False})}\n\n"
                        continue
                    elif mode == 'thinking':
                        # 流式传输推理内容
                        yield f"data: {json.dumps({'thinking_chunk': chunk.get('thinking', ''), 'done': False})}\n\n"
                        continue

                # 如果收到常规内容且仍在推理模式，退出推理模式
                if 'content' in chunk and in_reasoning_mode:
                    in_reasoning_mode = False
                    yield f"data: {json.dumps({'thinking_mode': False, 'thinking': reasoning_content, 'done': False})}\n\n"

                # 处理内容块
                if 'content' in chunk:
                    content = chunk['content']
                    full_content += content
                    yield f"data: {json.dumps({'id': str(ai_message_id), 'content': content, 'conversation_id': str(conversation_id), 'done': False})}\n\n"

                # 检测是否包含建议或推荐
                if 'suggestions' in chunk:
                    suggestions = chunk['suggestions']
                if 'recommendation' in chunk:
                    recommendations = chunk['recommendation']

                await asyncio.sleep(0.01)  # 适当的流控制

            # 更新数据库中的消息
            context = {}
            if suggestions:
                context["suggestions"] = suggestions
            if recommendations:
                context["recommendation"] = recommendations
            if reasoning_content:
                context["thinking"] = reasoning_content

            await self._update_message(ai_message_id, full_content, context)

            # 更新对话信息
            if not conversation:
                stmt = select(Conversation).where(Conversation.id == conversation_id)
                result = await self.db.execute(stmt)
                conversation = result.scalar_one()

            conversation.updated_at = datetime.utcnow()
            title_updated = False
            new_title = None

            # 检查是否需要生成新标题
            if (len(history) >= 2 or (is_new_conversation and len(history) == 0)) and conversation.title == "新对话":
                try:
                    # 生成对话标题
                    new_title = await self._generate_conversation_title(
                        user_message=message_create.content,
                        ai_response=full_content,
                        llm_service=llm_service
                    )
                    conversation.title = new_title
                    title_updated = True
                    logger.info(f"已为对话 {conversation_id} 生成新标题: {new_title}")
                except Exception as e:
                    logger.error(f"生成标题时出错: {str(e)}")

            await self.db.commit()

            # 发送完成事件，包含标题更新信息
            final_message = {
                'id': str(ai_message_id),
                'conversation_id': str(conversation_id),
                'content': full_content,
                'done': True,
                'suggestions': suggestions,
                'recommendation': recommendations,
                'thinking': reasoning_content
            }

            # 如果标题已更新，添加相关信息
            if title_updated and new_title:
                final_message['title_updated'] = True
                final_message['new_title'] = new_title

            yield f"data: {json.dumps(final_message)}\n\n"

        except Exception as e:
            # 如果出错，发送错误消息
            error_message = {
                "error": str(e),
                "done": True,
                "conversation_id": str(conversation_id)
            }
            yield f"data: {json.dumps(error_message)}\n\n"

            # 记录错误并更新消息
            logger.error(f"流式生成错误: {str(e)}")
            await self._update_message(ai_message_id, f"生成错误: {str(e)}", {})
            await self.db.commit()

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
            timestamp=datetime.now(tz=timezone.utc),
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
            existing_feedback.created_at = datetime.now(tz=timezone.utc)
        else:
            feedback = Feedback(
                message_id=message_id,
                feedback_type=feedback_type,
                comment=comment,
                created_at=datetime.now(tz=timezone.utc)
            )
            self.db.add(feedback)
            
        await self.db.commit()
        return True
