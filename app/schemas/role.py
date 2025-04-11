from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# 角色基础模型
class RoleBase(BaseModel):
    """角色基础数据模型"""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


# 创建角色的请求模型
class RoleCreate(RoleBase):
    """创建角色请求模型"""
    pass


# 更新角色的请求模型
class RoleUpdate(BaseModel):
    """更新角色请求模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


# 角色数据库模型
class RoleInDB(RoleBase):
    """数据库中的角色模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 角色响应模型
class Role(RoleInDB):
    """角色响应模型"""
    # 不包含用户引用以避免循环导入
    
    class Config:
        from_attributes = True