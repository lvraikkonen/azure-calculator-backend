from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_conversation_service
from app.models.user import User
from app.schemas.chat import (
    MessageCreate, 
    MessageResponse, 
    ConversationResponse, 
    ConversationSummary,
    ConversationBase,
    FeedbackCreate,
    FeedbackResponse
)
from app.services.conversation import ConversationService

router = APIRouter()

@router.post("/messages/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    发送消息并获取AI回复
    """
    try:
        response = await conversation_service.add_message(message, current_user.id)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消息处理失败: {str(e)}"
        )

@router.get("/conversations/", response_model=List[ConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取用户的所有对话列表
    """
    try:
        conversations = await conversation_service.list_conversations(current_user.id)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取特定对话的详细信息及消息历史
    """
    conversation = await conversation_service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或您无权访问"
        )
    return conversation

@router.patch("/conversations/{conversation_id}", response_model=ConversationBase)
async def update_conversation(
    conversation_id: UUID,
    conversation_update: ConversationBase,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新对话标题
    """
    success = await conversation_service.update_conversation_title(
        conversation_id, 
        current_user.id,
        conversation_update.title
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或您无权修改"
        )
    
    return conversation_update

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> None:  # 明确返回None
    """
    删除对话及其所有消息
    """
    success = await conversation_service.delete_conversation(conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或您无权删除"
        )

@router.post("/feedback/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    为消息添加反馈
    """
    success = await conversation_service.add_feedback(
        feedback.message_id,
        current_user.id,
        feedback.feedback_type,
        feedback.comment
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在或您无权添加反馈"
        )
    
    # 返回带ID的反馈响应
    feedback_response = FeedbackResponse(
        id=UUID('00000000-0000-0000-0000-000000000000'),  # 简化处理，实际应返回数据库生成的ID
        **feedback.dict(),
        created_at=datetime.utcnow()
    )
    
    return feedback_response