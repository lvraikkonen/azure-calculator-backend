from typing import List, AsyncGenerator, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.api.deps import get_current_user, get_conversation_service, get_llm_factory
from app.models.user import User
from app.schemas.chat import (
    MessageCreate,
    MessageResponse,
    ConversationResponse,
    ConversationSummary,
    ConversationBase,
    FeedbackCreate,
    FeedbackResponse, ModelInfo
)
from app.services.conversation import ConversationService
from app.services.llm.factory import LLMServiceFactory

router = APIRouter()
logger = get_logger(__name__)

@router.get("/models/", response_model=List[ModelInfo])
async def list_available_models(
    current_user: User = Depends(get_current_user),
    llm_factory: LLMServiceFactory = Depends(get_llm_factory)
):
    """
    获取可用的LLM模型列表
    """
    return await llm_factory.get_available_models()

@router.post("/models/recommend")
async def recommend_optimal_model(
    task_type: str = "general",
    performance_requirements: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    llm_factory: LLMServiceFactory = Depends(get_llm_factory)
):
    """
    基于任务类型和性能要求推荐最优模型

    Args:
        task_type: 任务类型 (general, reasoning, speed, cost_effective)
        performance_requirements: 性能要求字典
    """
    try:
        # 获取推荐的模型ID
        optimal_model_id = await llm_factory.select_optimal_model(
            task_type=task_type,
            performance_requirements=performance_requirements or {},
            fallback_to_default=True
        )

        if not optimal_model_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到符合要求的模型"
            )

        # 获取模型详细信息
        if llm_factory.performance_service:
            performance_summary = await llm_factory.performance_service.get_model_performance_summary(
                optimal_model_id
            )
        else:
            performance_summary = None

        # 获取模型配置信息
        model_info = None
        if llm_factory.model_config_service:
            try:
                model_config = await llm_factory.model_config_service.get_model_by_id(optimal_model_id)
                if model_config:
                    model_info = {
                        "id": str(model_config.id),
                        "name": model_config.name,
                        "display_name": model_config.display_name,
                        "model_type": model_config.model_type,
                        "model_name": model_config.model_name,
                        "description": model_config.description,
                        "capabilities": model_config.capabilities,
                        "input_price": model_config.input_price,
                        "output_price": model_config.output_price,
                        "max_tokens": model_config.max_tokens
                    }
            except Exception as e:
                logger.warning(f"获取模型配置信息失败: {str(e)}")

        return {
            "recommended_model_id": optimal_model_id,
            "task_type": task_type,
            "performance_requirements": performance_requirements,
            "model_info": model_info,
            "performance_summary": performance_summary,
            "recommendation_reason": f"基于 {task_type} 任务类型的性能优化选择"
        }

    except Exception as e:
        logger.error(f"模型推荐失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模型推荐失败: {str(e)}"
        )

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

@router.post("/messages/stream", status_code=status.HTTP_200_OK)
async def create_message_stream(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    发送消息并获取AI流式回复
    """
    try:
        return StreamingResponse(
            conversation_service.add_message_stream(message, current_user.id),
            media_type="text/event-stream"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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