from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

class LDAPTestRequest(BaseModel):
    username: str
    password: str

class LDAPTestResponse(BaseModel):
    is_success: bool
    message: str

# Shared properties
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class LDAPUserCreate(BaseModel):
    """LDAP用户创建模型"""
    username: str = Field(..., min_length=3, max_length=64)
    ldap_guid: str = Field(..., min_length=36, max_length=36)
    groups: str = Field("viewer", description="逗号分隔的角色列表")

class SimplifiedLDAPUserCreate(BaseModel):
    """简化版LDAP用户创建模型"""
    username: str = Field(..., min_length=3, max_length=64)
    groups: str = Field("viewer", description="逗号分隔的角色列表")

class LDAPUserSearchRequest(BaseModel):
    """LDAP用户查询请求模型"""
    username: str

class LDAPUserSearchResponse(BaseModel):
    """LDAP用户查询响应模型"""
    username: str
    full_name: str  # 修改字段名
    email: str
    ldap_guid: str
    exists_in_local: bool

class LDAPUserCreateResponse(BaseModel):
    """LDAP用户创建响应模型"""
    username: str
    ldap_guid: str
    groups: str
    is_active: bool

    class Config:
        from_attributes = True

class LDAPUserCreate(BaseModel):
    """LDAP用户创建模型"""
    username: str = Field(..., min_length=3, max_length=64)
    displayname: str = Field(..., min_length=2, max_length=64)
    email: str = Field(..., min_length=3, max_length=100)
    ldap_guid: str = Field(..., min_length=36, max_length=36)
    groups: str = Field("viewer", description="逗号分隔的角色列表")

class LDAPUserCreateResponse(UserBase):
    """LDAP用户创建响应模型"""
    ldap_guid: str
    groups: str
    is_active: bool

    class Config:
        from_attributes = True


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=8)


# Database model response
class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Properties to return to admin
class UserAdminResponse(User):
    pass


# Properties to return to regular users (no admin status)
class UserResponse(User):
    # Remove superuser status from regular responses
    @field_validator('is_superuser', mode='before')
    def reset_is_superuser(cls, v, values):
        return False