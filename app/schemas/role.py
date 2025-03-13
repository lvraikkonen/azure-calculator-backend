from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# 基础角色模式
class RoleBase(BaseModel):
    """角色基础数据模式"""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


# 创建角色时的数据模式
class RoleCreate(RoleBase):
    """创建角色请求模式"""
    pass


# 更新角色时的数据模式
class RoleUpdate(BaseModel):
    """更新角色请求模式"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


# 角色响应模式
class RoleResponse(RoleBase):
    """角色响应模式"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# 包含用户的角色响应模式
class RoleWithUsers(RoleResponse):
    """包含用户列表的角色响应模式"""
    users: List["UserMinimal"] = []
    
    class Config:
        from_attributes = True


# 最小用户信息（用于嵌套在角色响应中）
class UserMinimal(BaseModel):
    """最小用户信息模式（用于嵌套在角色响应中）"""
    id: int
    username: str
    
    class Config:
        from_attributes = True


# 设置循环引用
RoleWithUsers.model_rebuild()
