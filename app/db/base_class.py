from typing import Any

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models
    
    Features:
    - Automatically generates table names from class names
    - Provides a common base for all models
    """
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically based on class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()