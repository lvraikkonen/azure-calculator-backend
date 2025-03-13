from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get a user by ID
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get a user by username
    
    Args:
        db: Database session
        username: Username
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_user_by_ldap_guid(db: AsyncSession, ldap_guid: str) -> Optional[User]:
    """
    Get a user by LDAP GUID
    
    Args:
        db: Database session
        ldap_guid: LDAP GUID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await db.execute(select(User).where(User.ldap_guid == ldap_guid))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get a user by email
    
    Args:
        db: Database session
        email: Email address
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100
) -> List[User]:
    """
    Get multiple users with pagination
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[User]: List of users
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Create a new user
    
    Args:
        db: Database session
        user_in: User creation data
        
    Returns:
        User: Created user
    """
    # Create a new user with the hashed password
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active if user_in.is_active is not None else True,
        is_superuser=user_in.is_superuser if user_in.is_superuser is not None else False,
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


async def update_user(
    db: AsyncSession, 
    user_id: int, 
    user_in: UserUpdate
) -> Optional[User]:
    """
    Update a user
    
    Args:
        db: Database session
        user_id: User ID
        user_in: User update data
        
    Returns:
        Optional[User]: Updated user if found, None otherwise
    """
    # Get current user
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    # Prepare update data
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Update user
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
    )
    await db.commit()
    
    # Refresh user
    return await get_user_by_id(db, user_id)


async def authenticate_user(
    db: AsyncSession, 
    username: str, 
    password: str
) -> Optional[User]:
    """
    Authenticate a user
    
    Args:
        db: Database session
        username: Username
        password: Plain text password
        
    Returns:
        Optional[User]: User if authentication successful, None otherwise
    """
    user = await get_user_by_username(db, username)
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


async def is_active(user: User) -> bool:
    """
    Check if user is active
    
    Args:
        user: User to check
        
    Returns:
        bool: True if user is active, False otherwise
    """
    return user.is_active


async def is_superuser(user: User) -> bool:
    """
    Check if user is a superuser
    
    Args:
        user: User to check
        
    Returns:
        bool: True if user is a superuser, False otherwise
    """
    return user.is_superuser