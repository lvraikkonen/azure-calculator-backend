from uuid import UUID
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.services.intent_analysis import IntentAnalysisService
from app.services.llm.factory import LLMServiceFactory
from celery_tasks.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(name="analyze_intent")
def analyze_intent(conversation_id: str, user_message: str):
    """
    后台分析用户意图并更新到会话元数据

    Args:
        conversation_id: 会话ID
        user_message: 用户消息
    """
    try:
        # 创建必要的服务实例
        llm_factory = LLMServiceFactory()
        intent_service = IntentAnalysisService(llm_factory)

        # 异步操作转同步执行
        import asyncio

        async def _analyze_and_update():
            # 执行意图分析
            intent_analysis = await intent_service.analyze_intent(user_message)
            logger.info(f"完成意图分析: {intent_analysis.get('intent', '未知')}")

            # 使用项目定义的异步会话
            async with AsyncSessionLocal() as session:
                # 获取会话
                stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()

                if conversation:
                    # 更新会话元数据
                    metadata = conversation.metadata or {}
                    metadata["intent_analysis"] = intent_analysis
                    conversation.metadata = metadata

                    # 提交到数据库
                    await session.commit()
                    logger.info(f"已更新会话 {conversation_id} 的意图分析: {intent_analysis.get('intent')}")
                else:
                    logger.warning(f"找不到会话 {conversation_id} 进行意图分析更新")

        # 执行异步函数
        asyncio.run(_analyze_and_update())

        return {"status": "success", "message": f"已完成会话 {conversation_id} 的意图分析"}
    except Exception as e:
        logger.error(f"意图分析任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}