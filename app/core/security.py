from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        subject: Subject of the token (typically user ID or username)
        expires_delta: Optional expiration time delta

    Returns:
        str: JWT access token
    """
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def get_encryption_key() -> bytes:
    """
    获取用于API密钥加密的密钥

    从应用配置中获取专用的API密钥加密密钥

    Returns:
        bytes: 加密密钥

    Raises:
        ValueError: 如果未配置API_KEY_ENCRYPTION_KEY
    """
    key = getattr(settings, 'API_KEY_ENCRYPTION_KEY', None)

    # 先检查key是否为None
    if key is None:
        raise ValueError(
            "未配置API_KEY_ENCRYPTION_KEY。请在环境变量或配置文件中设置此值。"
            "可以使用以下命令生成: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    return key if isinstance(key, bytes) else key.encode()


def encrypt_api_key(api_key: str) -> Optional[str]:
    """
    加密API密钥

    Args:
        api_key: 明文API密钥

    Returns:
        str: 加密后的API密钥，如果输入为None则返回None
    """
    if not api_key:
        return None

    try:
        # 创建加密器
        cipher_suite = Fernet(get_encryption_key())
        # 加密并返回base64编码的字符串
        encrypted_key = cipher_suite.encrypt(api_key.encode())
        return encrypted_key.decode()
    except Exception as e:
        # 记录错误但不暴露详细信息
        import logging
        logging.error(f"API密钥加密失败: {str(e)}")
        raise ValueError("API密钥加密失败")


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    解密API密钥

    Args:
        encrypted_key: 加密的API密钥

    Returns:
        str: 解密后的原始API密钥，如果输入为None则返回None
    """
    if not encrypted_key:
        return None

    try:
        # 创建加密器
        cipher_suite = Fernet(get_encryption_key())
        # 解密并返回原始字符串
        decrypted_key = cipher_suite.decrypt(encrypted_key.encode())
        return decrypted_key.decode()
    except Exception as e:
        # 记录错误但不暴露详细信息
        import logging
        logging.error(f"API密钥解密失败: {str(e)}")
        raise ValueError("API密钥解密失败，可能密钥已更改或数据已损坏")