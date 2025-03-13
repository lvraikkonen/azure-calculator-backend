# 1. 首先导入不依赖其他模块的基础模型
from app.schemas.token import Token, TokenPayload

# 2. 导入角色相关模型，因为它们不依赖用户模型
from app.schemas.role import Role, RoleCreate, RoleUpdate, RoleInDB

# 3. 导入用户相关模型，它们可能会依赖角色模型
from app.schemas.user import (
    User, UserCreate, UserUpdate, UserResponse, UserAdminResponse, UserInDBBase,
    LDAPUserCreate, LDAPUserCreateResponse, LDAPUserSearchRequest, LDAPUserSearchResponse,
    LDAPTestRequest, LDAPTestResponse, SimplifiedLDAPUserCreate, UserRoleResponse
)

# 4. 导入其他模型
try:
    # 可能不是所有项目都有这些模型，使用try-except处理可能的导入错误
    from app.schemas.chat import (
        MessageBase, MessageCreate, MessageResponse,
        ConversationBase, ConversationCreate, ConversationResponse, ConversationSummary,
        FeedbackCreate, FeedbackResponse, Recommendation
    )
except ImportError:
    pass

try:
    from app.schemas.product import Product, ProductCreate, ProductUpdate
except ImportError:
    pass