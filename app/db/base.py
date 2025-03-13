# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base
from app.models.user import User
from app.models.role import Role
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.feedback import Feedback
from app.models.product import Product