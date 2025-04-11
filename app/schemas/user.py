from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from app.schemas.role import Role
else:
    # 定义一个占位类用于类型标注
    class Role(BaseModel):
        id: int
        name: str


# LDAP认证相关模型
class LDAPTestRequest(BaseModel):
    """LDAP认证测试请求"""
    username: str
    password: str


class LDAPTestResponse(BaseModel):
    """LDAP认证测试响应"""
    is_success: bool
    message: str


# 用户基础模型
class UserBase(BaseModel):
    """用户基础数据模型"""
    username: str = Field(..., min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    groups: Optional[str] = None


# LDAP用户相关模型
class LDAPUserSearchRequest(BaseModel):
    """LDAP用户查询请求模型"""
    username: str


class LDAPUserSearchResponse(BaseModel):
    """LDAP用户查询响应模型"""
    username: str
    full_name: str
    email: str
    ldap_guid: str
    exists_in_local: bool


class LDAPUserCreate(BaseModel):
    """LDAP用户创建模型"""
    username: str = Field(..., min_length=3, max_length=64)
    displayname: str = Field(..., min_length=2, max_length=64)
    email: str = Field(..., min_length=3, max_length=100)
    ldap_guid: str = Field(..., min_length=36, max_length=36)
    groups: str = Field("viewer", description="逗号分隔的角色列表")


class SimplifiedLDAPUserCreate(BaseModel):
    """简化版LDAP用户创建模型"""
    username: str = Field(..., min_length=3, max_length=64)
    groups: str = Field("viewer", description="逗号分隔的角色列表")


class LDAPUserCreateResponse(UserBase):
    """LDAP用户创建响应模型"""
    ldap_guid: str
    groups: str
    is_active: bool

    class Config:
        from_attributes = True


# 创建和更新用户的模型
class UserCreate(UserBase):
    """创建用户请求模型"""
    password: str = Field(..., min_length=8)


class UserUpdate(UserBase):
    """更新用户请求模型"""
    username: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


# 数据库用户模型
class UserInDBBase(UserBase):
    """数据库中的用户基础模型"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    auth_source: str = "local"
    ldap_guid: Optional[str] = None

    class Config:
        from_attributes = True


# 标准用户响应模型
class User(UserInDBBase):
    """用户响应模型 - 包含基本信息"""
    # 在异步环境中不使用关系属性
    # roles: Optional[List["Role"]] = None
    
    class Config:
        from_attributes = True


# 管理员视图的用户响应
class UserAdminResponse(UserInDBBase):
    """管理员视图的用户响应模型 - 包含全部信息"""
    # 在异步环境中不使用关系属性
    # roles: Optional[List["Role"]] = None
    
    class Config:
        from_attributes = True


# 普通用户视图的用户响应
class UserResponse(UserInDBBase):
    """普通用户视图的用户响应模型 - 隐藏管理员状态"""
    # 在异步环境中不使用关系属性
    # roles: Optional[List["Role"]] = None
    
    # 隐藏超级用户状态
    @field_validator('is_superuser', mode='before')
    def reset_is_superuser(cls, v, values):
        return False
    
    class Config:
        from_attributes = True


# 包含密码哈希的用户模型（仅内部使用）
class UserWithPassword(UserInDBBase):
    """包含密码哈希的用户模型（仅内部使用）"""
    hashed_password: str


# 角色分配响应模型（可选，用于处理用户与角色的关系）
class UserRoleResponse(BaseModel):
    """用户角色分配响应"""
    user_id: UUID
    username: str
    role_id: int
    role_name: str
    
    class Config:
        from_attributes = True