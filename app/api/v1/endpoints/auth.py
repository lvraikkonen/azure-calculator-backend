from datetime import datetime, timedelta
from typing import Annotated, Any

import ldap3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.token import Token
from app.schemas.user import User, UserCreate
from app.services.user import UserService

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)]
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Supports both local and LDAP authentication.
    """
    # First check if user exists
    user = await user_service.get_user_by_username(form_data.username)
    if not user:
        logger.warning(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not registered",
        )

    # Handle LDAP user
    if user.auth_source == 'ldap':
        if not settings.LDAP_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LDAP authentication is not enabled",
            )

        try:
            # Construct UPN for LDAP authentication
            username = f"{form_data.username}@{settings.LDAP_DOMAIN}"
            
            # Attempt LDAP bind
            with ldap3.Connection(
                server=ldap3.Server(settings.LDAP_SERVER),
                user=username,
                password=form_data.password,
                auto_bind=True
            ) as conn:
                logger.info(f"LDAP authentication successful for user: {form_data.username}")
        except Exception as e:
            logger.error(f"LDAP authentication failed for user {form_data.username}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LDAP authentication failed",
            )
    else:
        # Handle local user
        user = await user_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Check if user is active
    if not user_service.is_active(user):
        logger.warning(f"Inactive user attempted login: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    # Update last login time
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(last_login=datetime.utcnow())
    )
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=User)
async def register_user(
    user_in: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)]
) -> Any:
    """
    Register a new user.
    """
    # Check if username already exists
    user = await user_service.get_user_by_username(user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Check if email already exists (if provided)
    if user_in.email:
        user = await user_service.get_user_by_email(user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    
    # Remove superuser privileges from registration
    # Only allow superuser creation through admin interfaces
    user_data = user_in.model_dump()
    user_data["is_superuser"] = False
    user_create = UserCreate(**user_data)
    
    # Create user
    new_user = await user_service.create_user(user_create)
    logger.info(f"New user registered: {new_user.username}")
    
    return new_user


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.post("/logout")
async def logout(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> Any:
    """
    Logout current user.
    Note: Since we're using stateless JWT tokens, logout is handled client-side
    by removing the token. This endpoint serves as a confirmation and logging point.
    """
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}
