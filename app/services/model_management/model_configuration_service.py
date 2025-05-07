import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.model_configuration import ModelConfiguration
from app.models.model_price_history import ModelPriceHistory
from app.models.model_audit_log import ModelAuditLog
from app.services.llm.base import ModelType

from app.schemas.model_management.configuration import (
    ModelCreate, ModelUpdate, ModelResponse, ModelSummary,
    ModelListResponse, ModelTestRequest, ModelTestResponse
)

settings = get_settings()
logger = get_logger(__name__)


class ModelConfigurationService:
    """模型配置服务 - 处理模型配置的CRUD操作和状态管理"""

    def __init__(self, db: AsyncSession):
        """
        初始化模型配置服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_model_by_id(self, model_id: uuid.UUID) -> Optional[ModelConfiguration]:
        """
        通过ID获取模型配置

        Args:
            model_id: 模型ID

        Returns:
            找到的模型配置或None
        """
        result = await self.db.execute(
            select(ModelConfiguration).where(ModelConfiguration.id == model_id)
        )
        return result.scalar_one_or_none()

    async def get_model_response_by_id(self, model_id: uuid.UUID) -> Optional[ModelResponse]:
        """
        通过ID获取模型配置并转换为响应schema

        Args:
            model_id: 模型ID

        Returns:
            找到的模型响应或None
        """
        model = await self.get_model_by_id(model_id)
        if not model:
            return None

        return self._model_to_response(model)

    async def get_model_by_name(self, name: str) -> Optional[ModelConfiguration]:
        """
        通过名称获取模型配置

        Args:
            name: 模型名称

        Returns:
            找到的模型配置或None
        """
        result = await self.db.execute(
            select(ModelConfiguration).where(ModelConfiguration.name == name)
        )
        return result.scalar_one_or_none()

    async def list_models(
            self,
            model_type: Optional[str] = None,
            is_active: Optional[bool] = None,
            is_visible: Optional[bool] = None,
            is_custom: Optional[bool] = None,
            search_term: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelConfiguration]:
        """
        获取模型配置列表，支持多种筛选条件

        Args:
            model_type: 可选的模型类型筛选
            is_active: 可选的激活状态筛选
            is_visible: 可选的可见性筛选
            is_custom: 可选的自定义模型筛选
            search_term: 可选的搜索词(匹配名称或描述)
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            模型配置列表
        """
        query = select(ModelConfiguration)

        # 应用筛选条件
        if model_type:
            query = query.where(ModelConfiguration.model_type == model_type)
        if is_active is not None:
            query = query.where(ModelConfiguration.is_active == is_active)
        if is_visible is not None:
            query = query.where(ModelConfiguration.is_visible == is_visible)
        if is_custom is not None:
            query = query.where(ModelConfiguration.is_custom == is_custom)
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.where(
                or_(
                    ModelConfiguration.name.ilike(search_pattern),
                    ModelConfiguration.display_name.ilike(search_pattern),
                    ModelConfiguration.description.ilike(search_pattern)
                )
            )

        # 分页
        query = query.offset(skip).limit(limit)

        # 执行查询
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_models_with_schema(
            self,
            model_type: Optional[str] = None,
            is_active: Optional[bool] = None,
            is_visible: Optional[bool] = None,
            is_custom: Optional[bool] = None,
            search_term: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> ModelListResponse:
        """
        获取模型配置列表，返回符合schema的响应

        Args:
            model_type: 可选的模型类型筛选
            is_active: 可选的激活状态筛选
            is_visible: 可选的可见性筛选
            is_custom: 可选的自定义模型筛选
            search_term: 可选的搜索词(匹配名称或描述)
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            ModelListResponse: 包含模型总数和列表的响应
        """
        # 获取符合条件的总记录数
        count_query = select(
            func.count()
        ).select_from(ModelConfiguration)

        # 应用相同的筛选条件
        if model_type:
            count_query = count_query.where(ModelConfiguration.model_type == model_type)
        if is_active is not None:
            count_query = count_query.where(ModelConfiguration.is_active == is_active)
        if is_visible is not None:
            count_query = count_query.where(ModelConfiguration.is_visible == is_visible)
        if is_custom is not None:
            count_query = count_query.where(ModelConfiguration.is_custom == is_custom)
        if search_term:
            search_pattern = f"%{search_term}%"
            count_query = count_query.where(
                or_(
                    ModelConfiguration.name.ilike(search_pattern),
                    ModelConfiguration.display_name.ilike(search_pattern),
                    ModelConfiguration.description.ilike(search_pattern)
                )
            )

        # 执行count查询
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()

        # 获取模型列表
        models = await self.list_models(
            model_type=model_type,
            is_active=is_active,
            is_visible=is_visible,
            is_custom=is_custom,
            search_term=search_term,
            skip=skip,
            limit=limit
        )

        # 转换为ModelSummary列表
        model_summaries = [ModelSummary.from_orm(model) for model in models]

        # 创建并返回ModelListResponse
        return ModelListResponse(
            total=total_count,
            models=model_summaries
        )

    async def create_model(
            self,
            name: str,
            display_name: str,
            model_type: str,
            model_name: str,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            description: Optional[str] = None,
            parameters: Dict[str, Any] = None,
            input_price: float = 0.0,
            output_price: float = 0.0,
            is_custom: bool = False,
            is_active: bool = True,
            is_visible: bool = True,
            capabilities: List[str] = None,
            max_tokens: Optional[int] = None,
            rate_limit: Optional[int] = None,
            user_rate_limit: Optional[int] = None,
            user_id: Optional[uuid.UUID] = None
    ) -> Tuple[ModelConfiguration, bool]:
        """
        创建新的模型配置

        Args:
            name: 模型唯一名称
            display_name: 模型显示名称
            model_type: 模型类型(openai, deepseek等)
            model_name: 具体模型名称
            api_key: API密钥(可选)
            base_url: API基础URL(可选)
            description: 模型描述(可选)
            parameters: 附加参数(可选)
            input_price: 输入token价格
            output_price: 输出token价格
            is_custom: 是否自定义模型
            is_active: 是否激活
            is_visible: 是否在UI可见
            capabilities: 能力列表(可选)
            max_tokens: 最大tokens限制(可选)
            rate_limit: 速率限制(可选)
            user_rate_limit: 用户速率限制(可选)
            user_id: 创建者ID(可选)

        Returns:
            元组(model, created): 创建的模型及是否新创建

        Raises:
            ValueError: 如果模型名称已存在
        """
        # 检查模型名称是否已存在
        existing_model = await self.get_model_by_name(name)
        if existing_model:
            logger.warning(f"模型名称'{name}'已存在，返回现有模型")
            return existing_model, False

        # 加密API密钥
        encrypted_api_key = None
        if api_key:
            encrypted_api_key = encrypt_api_key(api_key)
            logger.info("已加密API密钥")

        # 创建新模型
        model = ModelConfiguration(
            name=name,
            display_name=display_name,
            description=description,
            model_type=model_type,
            model_name=model_name,
            api_key=encrypted_api_key,
            base_url=base_url,
            parameters=parameters or {},
            input_price=input_price,
            output_price=output_price,
            currency="USD",  # 默认使用美元
            is_active=is_active,
            is_custom=is_custom,
            is_visible=is_visible,
            capabilities=capabilities or [],
            max_tokens=max_tokens,
            rate_limit=rate_limit,
            user_rate_limit=user_rate_limit,
            created_by=user_id,
            updated_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(model)

        try:
            # 先提交模型，确保有Model ID
            await self.db.commit()
            await self.db.refresh(model)

            # 确保模型ID已生成
            if not model.id:
                await self.db.rollback()
                logger.error("创建模型后未能获取模型ID")
                raise ValueError("创建模型配置失败: 无法获取模型ID")

            # 记录价格历史
            price_history = ModelPriceHistory(
                model_id=model.id,
                input_price=input_price,
                output_price=output_price,
                currency="USD",
                effective_date=datetime.utcnow(),
                changed_by=user_id
            )
            self.db.add(price_history)

            # 记录审计日志
            audit_log = ModelAuditLog(
                model_id=model.id,
                action="create",
                changes_summary=f"创建模型配置: {name}",
                changes_detail={
                    "name": name,
                    "model_type": model_type,
                    "model_name": model_name,
                    "is_active": is_active,
                    "input_price": input_price,
                    "output_price": output_price
                },
                performed_by=user_id,
                action_date=datetime.utcnow()
            )
            self.db.add(audit_log)

            # 提交价格历史和审计日志
            await self.db.commit()
            logger.info(f"成功创建模型配置: {name}")
            return model, True

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"创建模型配置失败: {str(e)}")
            raise ValueError(f"创建模型配置失败: {str(e)}")

    async def create_model_from_schema(
            self,
            model_data: ModelCreate,
            user_id: Optional[uuid.UUID] = None
    ) -> Tuple[ModelResponse, bool]:
        """
        使用Schema创建新的模型配置

        Args:
            model_data: ModelCreate schema对象
            user_id: 创建者ID(可选)

        Returns:
            元组(model_response, created): 创建的模型响应及是否新创建

        Raises:
            ValueError: 如果模型名称已存在或创建失败
        """
        # 从schema中提取数据
        model, created = await self.create_model(
            name=model_data.name,
            display_name=model_data.display_name,
            model_type=model_data.model_type,
            model_name=model_data.model_name,
            api_key=model_data.api_key,
            base_url=model_data.base_url,
            description=model_data.description,
            parameters=model_data.parameters,
            input_price=model_data.input_price,
            output_price=model_data.output_price,
            is_custom=model_data.is_custom,
            is_active=model_data.is_active,
            is_visible=model_data.is_visible,
            capabilities=model_data.capabilities,
            max_tokens=model_data.max_tokens,
            rate_limit=model_data.rate_limit,
            user_rate_limit=model_data.user_rate_limit,
            user_id=user_id
        )

        # 转换为响应schema
        return self._model_to_response(model), created

    async def update_model(
            self,
            model_id: uuid.UUID,
            update_data: Dict[str, Any],
            user_id: Optional[uuid.UUID] = None
    ) -> Optional[ModelConfiguration]:
        """
        更新模型配置

        Args:
            model_id: 模型ID
            update_data: 要更新的字段和值
            user_id: 执行更新的用户ID(可选)

        Returns:
            更新后的模型配置，如果未找到则返回None

        Raises:
            ValueError: 如果更新操作无效
        """
        # 获取现有模型
        model = await self.get_model_by_id(model_id)
        if not model:
            logger.warning(f"未找到要更新的模型: {model_id}")
            return None

        # 记录原始值用于审计
        original_values = {}
        changes = {}

        # 检查并处理API密钥加密
        if 'api_key' in update_data:
            # 记录变更（不记录实际值，只标记有变更）
            original_values['api_key'] = "******"
            changes['api_key'] = "******"

            # 如果提供了非空API密钥，则加密
            if update_data['api_key']:
                encrypted_key = encrypt_api_key(update_data['api_key'])
                update_data['api_key'] = encrypted_key
            else:
                # 如果提供了空值，表示用户想要清除API密钥
                update_data['api_key'] = None

        # 检查并更新价格，如果价格有变化，记录价格历史
        price_changed = False
        new_input_price = update_data.get('input_price')
        new_output_price = update_data.get('output_price')

        if new_input_price is not None and new_input_price != model.input_price:
            original_values['input_price'] = model.input_price
            changes['input_price'] = new_input_price
            price_changed = True

        if new_output_price is not None and new_output_price != model.output_price:
            original_values['output_price'] = model.output_price
            changes['output_price'] = new_output_price
            price_changed = True

        # 记录其他变更
        allowed_fields = [
            'display_name', 'description', 'api_key', 'base_url',
            'parameters', 'is_active', 'is_visible', 'capabilities',
            'max_tokens', 'rate_limit', 'user_rate_limit'
        ]

        for field in allowed_fields:
            if field in update_data and getattr(model, field) != update_data[field]:
                original_values[field] = getattr(model, field)
                changes[field] = update_data[field]
                setattr(model, field, update_data[field])

        if 'api_key' in update_data:
            model.api_key = update_data['api_key']  # 已加密的值

        if 'input_price' in update_data:
            model.input_price = update_data['input_price']

        if 'output_price' in update_data:
            model.output_price = update_data['output_price']

        # 如果没有变更，直接返回
        if not changes:
            logger.info(f"模型 {model_id} 没有需要更新的字段")
            return model

        # 更新修改时间和用户
        model.updated_at = datetime.utcnow()
        if user_id:
            model.updated_by = user_id

        # 如果价格变更，记录价格历史
        if price_changed:
            price_history = ModelPriceHistory(
                model_id=model_id,
                input_price=model.input_price,
                output_price=model.output_price,
                currency=model.currency,
                effective_date=datetime.utcnow(),
                changed_by=user_id
            )
            self.db.add(price_history)

        # 记录审计日志
        changes_summary = f"更新模型 {model.name}: " + ", ".join([f"{k}={v}" for k, v in changes.items()])
        audit_log = ModelAuditLog(
            model_id=model_id,
            action="update",
            changes_summary=changes_summary[:500],  # 限制长度
            changes_detail={
                "before": original_values,
                "after": changes
            },
            performed_by=user_id,
            action_date=datetime.utcnow()
        )
        self.db.add(audit_log)

        try:
            await self.db.commit()
            await self.db.refresh(model)
            logger.info(f"成功更新模型: {model.name}")
            return model
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"更新模型失败: {str(e)}")
            raise ValueError(f"更新模型失败: {str(e)}")

    async def update_model_from_schema(
            self,
            model_id: uuid.UUID,
            model_data: ModelUpdate,
            user_id: Optional[uuid.UUID] = None
    ) -> Optional[ModelResponse]:
        """
        使用Schema更新模型配置

        Args:
            model_id: 模型ID
            model_data: ModelUpdate schema对象
            user_id: 执行更新的用户ID(可选)

        Returns:
            更新后的模型响应，如果未找到则返回None

        Raises:
            ValueError: 如果更新操作无效
        """
        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in model_data.dict().items() if v is not None}

        # 更新模型
        model = await self.update_model(model_id, update_data, user_id)
        if not model:
            return None

        # 转换为响应schema
        return self._model_to_response(model)

    async def delete_model(self, model_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> bool:
        """
        删除模型配置

        Args:
            model_id: 模型ID
            user_id: 执行删除的用户ID(可选)

        Returns:
            删除是否成功
        """
        model = await self.get_model_by_id(model_id)
        if not model:
            logger.warning(f"未找到要删除的模型: {model_id}")
            return False

        model_name = model.name  # 保存用于记录

        # 创建审计日志
        audit_log = ModelAuditLog(
            model_id=model_id,
            action="delete",
            changes_summary=f"删除模型: {model_name}",
            changes_detail={"deleted_model": model_name},
            performed_by=user_id,
            action_date=datetime.utcnow()
        )
        self.db.add(audit_log)

        # 删除模型
        await self.db.delete(model)

        try:
            await self.db.commit()
            logger.info(f"成功删除模型: {model_name}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除模型失败: {str(e)}")
            return False

    async def activate_model(self, model_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> bool:
        """
        激活模型

        Args:
            model_id: 模型ID
            user_id: 执行操作的用户ID(可选)

        Returns:
            操作是否成功
        """
        return await self._update_model_status(model_id, True, user_id)

    async def deactivate_model(self, model_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> bool:
        """
        停用模型

        Args:
            model_id: 模型ID
            user_id: 执行操作的用户ID(可选)

        Returns:
            操作是否成功
        """
        return await self._update_model_status(model_id, False, user_id)

    async def _update_model_status(self, model_id: uuid.UUID, is_active: bool,
                                   user_id: Optional[uuid.UUID] = None) -> bool:
        """
        更新模型状态

        Args:
            model_id: 模型ID
            is_active: 是否激活
            user_id: 执行操作的用户ID(可选)

        Returns:
            操作是否成功
        """
        model = await self.get_model_by_id(model_id)
        if not model:
            logger.warning(f"未找到要更新状态的模型: {model_id}")
            return False

        # 如果状态相同，无需更新
        if model.is_active == is_active:
            logger.info(f"模型 {model.name} 已经是{'激活' if is_active else '停用'}状态")
            return True

        # 更新状态
        model.is_active = is_active
        model.updated_at = datetime.utcnow()
        if user_id:
            model.updated_by = user_id

        # 记录审计日志
        action = "activate" if is_active else "deactivate"
        status_text = "激活" if is_active else "停用"
        audit_log = ModelAuditLog(
            model_id=model_id,
            action=action,
            changes_summary=f"{status_text}模型: {model.name}",
            changes_detail={"is_active": is_active},
            performed_by=user_id,
            action_date=datetime.utcnow()
        )
        self.db.add(audit_log)

        try:
            await self.db.commit()
            logger.info(f"成功{status_text}模型: {model.name}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"{status_text}模型失败: {str(e)}")
            return False

    async def test_model_connection(
            self,
            test_request: ModelTestRequest,
            llm_factory
    ) -> ModelTestResponse:
        """
        使用Schema测试模型API连接

        Args:
            test_request: ModelTestRequest schema对象
            llm_factory: LLM工厂实例，用于创建模型连接

        Returns:
            ModelTestResponse: 测试结果响应

        Raises:
            ValueError: 如果模型未找到
        """
        model = await self.get_model_by_id(test_request.model_id)
        if not model:
            raise ValueError(f"未找到模型: {test_request.model_id}")

        try:
            # 记录开始时间
            start_time = datetime.utcnow()

            # 解密API密钥
            decrypted_api_key = None
            if model.api_key:
                try:
                    decrypted_api_key = decrypt_api_key(model.api_key)
                except ValueError as e:
                    logger.error(f"API密钥解密失败: {str(e)}")
                    return ModelTestResponse(
                        success=False,
                        message="API密钥解密失败，请检查密钥配置",
                        error="API密钥解密失败"
                    )

            # 通过LLM工厂创建服务实例
            model_type_enum = ModelType(model.model_type)
            llm_service = await llm_factory.create_service(
                model_type=model_type_enum,
                model_name=model.model_name,
                config={
                    "api_key": decrypted_api_key,
                    "base_url": model.base_url
                }
            )

            # 执行测试查询
            test_message = test_request.test_message or "Hello, this is a connection test. Please respond with 'Connection successful'."
            test_response = await llm_service.chat(
                test_message,
                [], [], {}
            )

            # 计算耗时
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000  # 毫秒

            return ModelTestResponse(
                success=True,
                response_time=response_time,
                message="连接测试成功",
                response=test_response.get("content", "")
            )
        except Exception as e:
            logger.error(f"模型连接测试失败: {str(e)}")
            return ModelTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
                error=str(e)
            )

    def _model_to_response(self, model: ModelConfiguration) -> ModelResponse:
        """
        将模型ORM对象转换为响应schema

        Args:
            model: ModelConfiguration ORM对象

        Returns:
            ModelResponse: 模型响应schema
        """
        # 掩码处理API密钥
        api_key_masked = None
        if model.api_key:
            if len(model.api_key) <= 8:
                api_key_masked = "****"
            else:
                api_key_masked = model.api_key[:4] + "****" + model.api_key[-4:]

        # 构建响应对象
        return ModelResponse(
            id=model.id,
            name=model.name,
            display_name=model.display_name,
            description=model.description,
            model_type=model.model_type,
            model_name=model.model_name,
            api_key_masked=api_key_masked,
            base_url=model.base_url,
            input_price=model.input_price,
            output_price=model.output_price,
            currency=model.currency,
            is_active=model.is_active,
            is_custom=model.is_custom,
            is_visible=model.is_visible,
            capabilities=model.capabilities or [],
            max_tokens=model.max_tokens,
            created_at=model.created_at,
            updated_at=model.updated_at,
            total_requests=model.total_requests,
            avg_response_time=model.avg_response_time,
            last_used_at=model.last_used_at
        )