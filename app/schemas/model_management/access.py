from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# 用户访问权限基础Schema
class UserAccessBase(BaseModel):
    """用户访问权限基础Schema"""
    user_id: UUID = Field(..., description="用户ID")
    model_id: UUID = Field(..., description="模型ID")
    access_level: str = Field("read", description="访问级别: read, write, admin")

    @classmethod
    @field_validator('access_level')
    def validate_access_level(cls, v):
        allowed_levels = ['read', 'write', 'admin']
        if v not in allowed_levels:
            raise ValueError(f"access_level必须是以下之一: {', '.join(allowed_levels)}")
        return v


# 创建用户访问权限请求
class UserAccessCreate(UserAccessBase):
    """创建用户访问权限请求Schema"""
    has_access: bool = Field(True, description="是否有访问权限")
    daily_quota: Optional[int] = Field(None, ge=0, description="每日请求限制")
    token_quota: Optional[int] = Field(None, ge=0, description="每日token限制")
    custom_settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户自定义模型设置")


# 更新用户访问权限请求
class UserAccessUpdate(BaseModel):
    """更新用户访问权限请求Schema"""
    access_level: Optional[str] = Field(None, description="访问级别: read, write, admin")
    has_access: Optional[bool] = Field(None, description="是否有访问权限")
    daily_quota: Optional[int] = Field(None, ge=0, description="每日请求限制")
    token_quota: Optional[int] = Field(None, ge=0, description="每日token限制")
    custom_settings: Optional[Dict[str, Any]] = Field(None, description="用户自定义模型设置")

    @classmethod
    @field_validator('access_level')
    def validate_access_level(cls, v):
        if v is not None:
            allowed_levels = ['read', 'write', 'admin']
            if v not in allowed_levels:
                raise ValueError(f"access_level必须是以下之一: {', '.join(allowed_levels)}")
        return v


# 用户访问权限响应
class UserAccessResponse(UserAccessBase):
    """用户访问权限响应Schema"""
    id: UUID = Field(..., description="访问权限ID")
    has_access: bool = Field(..., description="是否有访问权限")
    daily_quota: Optional[int] = Field(None, description="每日请求限制")
    token_quota: Optional[int] = Field(None, description="每日token限制")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="用户自定义模型设置")

    # 用户和模型信息
    username: Optional[str] = Field(None, description="用户名")
    model_name: Optional[str] = Field(None, description="模型名称")

    # 元数据
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    granted_by: Optional[UUID] = Field(None, description="授权人ID")
    granted_by_name: Optional[str] = Field(None, description="授权人名称")

    class Config:
        from_attributes = True


# 用户访问权限列表响应
class UserAccessListResponse(BaseModel):
    """用户访问权限列表响应Schema"""
    total: int = Field(..., description="总记录数")
    items: List[UserAccessResponse] = Field(..., description="访问权限列表")


# 用户配额更新请求
class UserQuotaUpdate(BaseModel):
    """用户配额更新请求Schema"""
    user_id: UUID = Field(..., description="用户ID")
    model_id: UUID = Field(..., description="模型ID")
    daily_quota: Optional[int] = Field(None, ge=0, description="每日请求限制")
    token_quota: Optional[int] = Field(None, ge=0, description="每日token限制")


# 批量访问权限请求
class BatchAccessRequest(BaseModel):
    """批量访问权限请求Schema"""
    user_ids: List[UUID] = Field(..., description="用户ID列表")
    model_ids: List[UUID] = Field(..., description="模型ID列表")
    access_level: str = Field("read", description="访问级别: read, write, admin")
    has_access: bool = Field(True, description="是否有访问权限")
    daily_quota: Optional[int] = Field(None, ge=0, description="每日请求限制")
    token_quota: Optional[int] = Field(None, ge=0, description="每日token限制")

    @classmethod
    @field_validator('access_level')
    def validate_access_level(cls, v):
        allowed_levels = ['read', 'write', 'admin']
        if v not in allowed_levels:
            raise ValueError(f"access_level必须是以下之一: {', '.join(allowed_levels)}")
        return v
