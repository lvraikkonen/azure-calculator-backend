import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.schemas.chat import MessageCreate, MessageResponse, ConversationResponse, ConversationSummary
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class ConversationService:
    """对话管理服务"""

    def __init__(self, db: AsyncSession, llm_service: LLMService):
        """初始化对话服务"""
        self.db = db
        self.llm_service = llm_service

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
                recommendation=msg.context.get("recommendation") if msg.context else None
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
        conversation.updated_at = datetime.utcnow()
        
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
        """
        添加用户消息并获取AI回复
        
        Args:
            message_create: 消息创建模型
            user_id: 用户ID
            
        Returns:
            MessageResponse: AI回复消息
        """
        # 获取或创建对话
        conversation_id = message_create.conversation_id
        if not conversation_id:
            conversation_id = await self.create_conversation(user_id)
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
        
        # 调用LLM获取回复
        ai_response = await self.llm_service.chat(message_create.content, history)
        
        # 补充对话ID
        ai_response.conversation_id = conversation_id
        
        # 存储AI回复
        context = {}
        if ai_response.suggestions:
            context["suggestions"] = ai_response.suggestions
        if ai_response.recommendation:
            context["recommendation"] = ai_response.recommendation.dict()
            
        ai_message_id = await self._store_message(
            conversation_id,
            ai_response.content,
            "ai",
            context
        )
        
        # 更新对话时间
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one()
        conversation.updated_at = datetime.utcnow()
        await self.db.commit()
        
        # 设置AI回复的ID
        ai_response.id = ai_message_id
        
        return ai_response

    async def add_message_stream(self, message_create: MessageCreate, user_id: UUID) -> AsyncGenerator[str, None]:
        """
        添加用户消息并获取流式AI回复
        
        Args:
            message_create: 消息创建模型
            user_id: 用户ID
            
        Yields:
            str: 生成的消息块，按SSE格式
        """
        # 获取或创建对话
        conversation_id = message_create.conversation_id
        if not conversation_id:
            conversation_id = await self.create_conversation(user_id)
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
        
        # 创建空的AI消息记录占位，稍后更新
        ai_message_id = await self._store_message(
            conversation_id,
            "", # 初始内容为空
            "ai",
            {}
        )
        
        # 启动流式生成
        full_content = ""
        recommendations = {}
        suggestions = []
        
        try:
            # 从LLM服务获取流式响应
            async for chunk in self.llm_service.chat_stream(message_create.content, history):
                # 累积完整内容
                if 'content' in chunk:
                    full_content += chunk['content']
                
                # 检测是否包含建议或推荐
                if 'suggestions' in chunk:
                    suggestions = chunk['suggestions']
                if 'recommendation' in chunk:
                    recommendations = chunk['recommendation']
                
                # 发送SSE格式的消息
                yield f"data: {json.dumps({'id': str(ai_message_id), 'content': chunk.get('content', ''), 'done': False})}\n\n"
                await asyncio.sleep(0.01)  # 适当的流控制
                
            # 发送完成事件，包含完整的推荐等额外信息
            final_message = {
                'id': str(ai_message_id),
                'content': full_content,
                'conversation_id': str(conversation_id),
                'done': True,
                'suggestions': suggestions,
                'recommendation': recommendations
            }
            yield f"data: {json.dumps(final_message)}\n\n"
            
            # 更新数据库中的消息
            context = {}
            if suggestions:
                context["suggestions"] = suggestions
            if recommendations:
                context["recommendation"] = recommendations
                
            await self._update_message(ai_message_id, full_content, context)
            
            # 更新对话时间
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await self.db.execute(stmt)
            conversation = result.scalar_one()
            conversation.updated_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            # 如果出错，发送错误消息
            error_message = {"error": str(e), "done": True}
            yield f"data: {json.dumps(error_message)}\n\n"
            
            # 记录错误并更新消息
            logger.error(f"流式生成错误: {str(e)}")
            await self._update_message(ai_message_id, f"生成错误: {str(e)}", {})
            await self.db.commit()
    
    async def _update_message(self, message_id: UUID, content: str, context: Dict[str, Any] = None) -> None:
        """
        更新现有消息
        
        Args:
            message_id: 消息ID
            content: 新消息内容
            context: 新消息上下文
        """
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
            sender: 发送者，'user'或'ai'
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
        """
        获取对话历史
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            List[Dict[str, Any]]: 对话历史列表
        """
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