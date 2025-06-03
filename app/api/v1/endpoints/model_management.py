from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.model_management.model_configuration_service import ModelConfigurationService
from app.schemas.model_management.configuration import (
    ModelCreate, ModelUpdate, ModelResponse, ModelSummary,
    ModelListResponse
)

router = APIRouter()


def get_model_service(db: AsyncSession = Depends(get_db)) -> ModelConfigurationService:
    """获取模型配置服务实例"""
    return ModelConfigurationService(db)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    skip: int = 0,
    limit: int = 20,
    model_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_custom: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    获取模型列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的记录数限制
        model_type: 模型类型筛选
        is_active: 是否激活筛选
        is_custom: 是否自定义模型筛选
        current_user: 当前用户
        model_service: 模型配置服务
    
    Returns:
        模型列表响应
    """
    try:
        models = await model_service.list_models(
            skip=skip,
            limit=limit,
            model_type=model_type,
            is_active=is_active,
            is_custom=is_custom
        )
        
        # 转换为响应格式
        model_summaries = []
        for model in models:
            summary = ModelSummary(
                id=model.id,
                name=model.name,
                display_name=model.display_name,
                model_type=model.model_type,
                model_name=model.model_name,
                is_active=model.is_active,
                is_custom=model.is_custom,
                total_requests=0,  # TODO: 从统计服务获取
                input_price=model.input_price,
                output_price=model.output_price
            )
            model_summaries.append(summary)
        
        return ModelListResponse(
            models=model_summaries,
            total=len(model_summaries),
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    获取模型详情
    
    Args:
        model_id: 模型ID
        current_user: 当前用户
        model_service: 模型配置服务
    
    Returns:
        模型详情响应
    """
    try:
        model = await model_service.get_model_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )
        
        # 转换为响应格式
        return model_service._model_to_response(model)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型详情失败: {str(e)}"
        )


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    创建新模型
    
    Args:
        model_data: 模型创建数据
        current_user: 当前用户
        model_service: 模型配置服务
    
    Returns:
        创建的模型响应
    """
    try:
        # 检查用户权限（只有超级用户或admin角色可以创建模型）
        if not current_user.is_superuser and (not current_user.groups or "admin" not in current_user.groups.split(",")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以创建模型"
            )
        
        model_response, created = await model_service.create_model_from_schema(
            model_data, user_id=current_user.id
        )
        
        if not created:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模型名称已存在"
            )
        
        return model_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模型失败: {str(e)}"
        )


@router.put("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    更新模型配置

    Args:
        model_id: 模型ID
        model_data: 模型更新数据
        current_user: 当前用户
        model_service: 模型配置服务

    Returns:
        更新后的模型响应
    """
    try:
        # 检查用户权限（只有超级用户或admin角色可以更新模型）
        if not current_user.is_superuser and (not current_user.groups or "admin" not in current_user.groups.split(",")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以更新模型"
            )

        # 检查模型是否存在
        existing_model = await model_service.get_model_by_id(model_id)
        if not existing_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        # 更新模型
        updated_model = await model_service.update_model_from_schema(
            model_id, model_data, user_id=current_user.id
        )

        if not updated_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新模型失败"
            )

        return updated_model

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型失败: {str(e)}"
        )


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    删除模型

    Args:
        model_id: 模型ID
        current_user: 当前用户
        model_service: 模型配置服务

    Returns:
        删除结果
    """
    try:
        # 检查用户权限（只有超级用户或admin角色可以删除模型）
        if not current_user.is_superuser and (not current_user.groups or "admin" not in current_user.groups.split(",")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以删除模型"
            )

        # 检查模型是否存在
        existing_model = await model_service.get_model_by_id(model_id)
        if not existing_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        # 删除模型
        success = await model_service.delete_model(model_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="删除模型失败"
            )

        return {"message": "模型删除成功", "model_id": str(model_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型失败: {str(e)}"
        )


@router.post("/models/{model_id}/activate")
async def activate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    激活模型

    Args:
        model_id: 模型ID
        current_user: 当前用户
        model_service: 模型配置服务

    Returns:
        操作结果
    """
    try:
        # 检查用户权限（只有超级用户或admin角色可以激活模型）
        if not current_user.is_superuser and (not current_user.groups or "admin" not in current_user.groups.split(",")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以激活模型"
            )

        # 检查模型是否存在
        existing_model = await model_service.get_model_by_id(model_id)
        if not existing_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        # 激活模型
        success = await model_service.activate_model(model_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="激活模型失败"
            )

        return {"message": "模型激活成功", "model_id": str(model_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"激活模型失败: {str(e)}"
        )


@router.post("/models/{model_id}/deactivate")
async def deactivate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    model_service: ModelConfigurationService = Depends(get_model_service)
):
    """
    停用模型

    Args:
        model_id: 模型ID
        current_user: 当前用户
        model_service: 模型配置服务

    Returns:
        操作结果
    """
    try:
        # 检查用户权限（只有超级用户或admin角色可以停用模型）
        if not current_user.is_superuser and (not current_user.groups or "admin" not in current_user.groups.split(",")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以停用模型"
            )

        # 检查模型是否存在
        existing_model = await model_service.get_model_by_id(model_id)
        if not existing_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        # 停用模型
        success = await model_service.deactivate_model(model_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="停用模型失败"
            )

        return {"message": "模型停用成功", "model_id": str(model_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停用模型失败: {str(e)}"
        )
