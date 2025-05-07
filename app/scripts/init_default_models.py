import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from app.db.session import AsyncSessionLocal
from app.services.model_management.model_configuration_service import ModelConfigurationService
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.security import encrypt_api_key, decrypt_api_key

# 设置日志
setup_logging()
logger = logging.getLogger("init_default_models")
logger.setLevel(logging.INFO)

settings = get_settings()


async def init_default_models():
    """初始化默认模型配置"""
    logger.info("开始初始化默认模型配置")

    async with AsyncSessionLocal() as db:
        db_session = db
        service = ModelConfigurationService(db_session)

        # 加密API密钥
        encrypted_api_key = None
        try:
            if settings.DEEPSEEK_API_KEY:
                encrypted_api_key = encrypt_api_key(settings.DEEPSEEK_API_KEY)
                logger.info("已加密API密钥")
            else:
                logger.warning("没有找到DEEPSEEK_API_KEY，将创建没有API密钥的模型配置")
        except Exception as e:
            logger.error(f"加密API密钥失败: {str(e)}")
            encrypted_api_key = None

        # 添加deepseek-chat模型
        try:
            deepseek_chat_config = {
                "name": "deepseek-chat",
                "display_name": "Deepseek Chat",
                "description": "Deepseek的通用对话模型，适合一般问答、创意写作和信息提取任务",
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_V3_MODEL,
                "api_key": encrypted_api_key,
                "base_url": settings.DEEPSEEK_API_BASE,
                "is_custom": False,
                "is_active": True,
                "is_visible": True,
                "capabilities": ["text_generation", "chat"],
                "input_price": 0.5,  # 每百万tokens价格，根据实际调整
                "output_price": 1.5,
                "max_tokens": 4096
            }

            model, created = await service.create_model(**deepseek_chat_config)
            if created:
                logger.info(f"成功创建模型: deepseek-chat (ID: {model.id})")
            else:
                logger.info(f"模型已存在: deepseek-chat (ID: {model.id})")

            # 查询并显示模型详情，验证创建成功
            model_details = await service.get_model_by_name("deepseek-chat")
            logger.info(f"模型详情: {model_details.name}, 状态: {'激活' if model_details.is_active else '未激活'}")

            # 验证API密钥加密/解密是否正常工作
            if model_details.api_key:
                try:
                    # 尝试解密API密钥（仅在log中显示前4位作为验证）
                    decrypted_key = decrypt_api_key(model_details.api_key)
                    masked_key = decrypted_key[:4] + "****" if decrypted_key else None
                    logger.info(f"API密钥解密验证通过，前缀: {masked_key}")
                except Exception as e:
                    logger.error(f"API密钥解密失败: {str(e)}")

        except Exception as e:
            logger.error(f"创建deepseek-chat模型时出错: {str(e)}")

        # 添加deepseek-reasoner模型
        try:
            deepseek_reasoner_config = {
                "name": "deepseek-reasoner",
                "display_name": "Deepseek Reasoner",
                "description": "Deepseek的推理增强模型，适合复杂推理、问题求解和多步骤分析任务",
                "model_type": "deepseek",
                "model_name": settings.DEEPSEEK_R1_MODEL,
                "api_key": encrypted_api_key,
                "base_url": settings.DEEPSEEK_API_BASE,
                "is_custom": False,
                "is_active": True,
                "is_visible": True,
                "capabilities": ["text_generation", "chat", "reasoning"],
                "input_price": 1.0,  # 每百万tokens价格，根据实际调整
                "output_price": 3.0,
                "max_tokens": 4096
            }

            model, created = await service.create_model(**deepseek_reasoner_config)
            if created:
                logger.info(f"成功创建模型: deepseek-reasoner (ID: {model.id})")
            else:
                logger.info(f"模型已存在: deepseek-reasoner (ID: {model.id})")

            # 查询并显示模型详情，验证创建成功
            model_details = await service.get_model_by_name("deepseek-reasoner")
            logger.info(f"模型详情: {model_details.name}, 状态: {'激活' if model_details.is_active else '未激活'}")

        except Exception as e:
            logger.error(f"创建deepseek-reasoner模型时出错: {str(e)}")

        # 列出所有模型
        models = await service.list_models()
        logger.info(f"系统中的模型总数: {len(models)}")
        for idx, model in enumerate(models, 1):
            logger.info(f"{idx}. {model.name} ({model.model_name}) - {'激活' if model.is_active else '未激活'}")


if __name__ == "__main__":
    try:
        asyncio.run(init_default_models())
        logger.info("默认模型初始化完成")
    except Exception as e:
        logger.error(f"初始化过程中发生错误: {str(e)}")
        sys.exit(1)