from uuid import UUID
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.services.llm.base import ModelType
from app.services.llm.factory import LLMServiceFactory
from celery_tasks.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(name="generate_title")
def generate_title(
        conversation_id: str,
        user_message: str,
        ai_response: str,
        model_type: str = None,
        model_name: str = None
):
    """
    后台生成会话标题并更新到数据库

    Args:
        conversation_id: 会话ID
        user_message: 用户消息
        ai_response: AI响应
        model_type: 模型类型
        model_name: 模型名称
    """
    try:
        # 创建LLM工厂
        llm_factory = LLMServiceFactory()

        # 异步操作转同步执行
        import asyncio

        async def _generate_and_update():
            # 获取LLM服务
            model_type_enum = ModelType(model_type) if model_type else None
            llm_service = await llm_factory.get_service(model_type_enum, model_name)

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

            logger.info(f"已生成标题: {title}")

            # 使用项目定义的异步会话
            async with AsyncSessionLocal() as session:
                stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
                result = await session.execute(stmt)
                conversation = result.scalar_one_or_none()

                if conversation and (conversation.title == "新对话" or not conversation.title):
                    conversation.title = title
                    await session.commit()
                    logger.info(f"已为会话 {conversation_id} 更新标题: {title}")
                else:
                    logger.info(f"会话 {conversation_id} 已有标题，跳过更新")

        # 执行异步函数
        asyncio.run(_generate_and_update())

        return {"status": "success", "message": f"已完成会话 {conversation_id} 的标题生成"}
    except Exception as e:
        logger.error(f"生成标题任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}