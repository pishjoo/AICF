"""
JWT Token Management

Handles creation, validation, and decoding of JWT tokens for authentication.
Supports access tokens and refresh tokens with different expiration times.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import uuid

from core.config import settings


# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    subject: str,
    organization_id: int,
    user_id: int,
    email: str,
    roles: list[str] = None,
    permissions: list[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user email or ID)
        organization_id: Organization ID for tenant isolation
        user_id: User ID
        email: User email
        roles: List of user role slugs
        permissions: List of user permissions
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TOKEN_TYPE_ACCESS,
        "organization_id": organization_id,
        "user_id": user_id,
        "email": email,
        "jti": str(uuid.uuid4()),  # Unique token ID for revocation
    }
    
    if roles:
        to_encode["roles"] = roles
    if permissions:
        to_encode["permissions"] = permissions
    
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    organization_id: int,
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiration and fewer claims.
    They are used to obtain new access tokens.
    
    Args:
        subject: Token subject (usually user email or ID)
        organization_id: Organization ID for tenant isolation
        user_id: User ID
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TOKEN_TYPE_REFRESH,
        "organization_id": organization_id,
        "user_id": user_id,
        "jti": str(uuid.uuid4()),
    }
    
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = TOKEN_TYPE_ACCESS) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        expected_type: Expected token type (access or refresh)
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify token type
        token_type = payload.get("type")
        if token_type != expected_type:
            raise JWTError(f"Invalid token type. Expected {expected_type}, got {token_type}")
        
        return payload
        
    except JWTError as e:
        raise JWTError(f"Token validation failed: {str(e)}")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without strict validation.
    Use only for debugging or when you need to inspect an expired token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload (may be expired)
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}
        )
    except JWTError as e:
        raise JWTError(f"Token decoding failed: {str(e)}")


def revoke_token(token: str) -> bool:
    """
    Revoke a token by adding its JTI to a blacklist.
    
    In production, this should store the JTI in Redis with TTL
    matching the token's remaining lifetime.
    
    For now, this is a placeholder for future implementation.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token was revoked successfully
    """
    # TODO: Implement token blacklist in Redis
    payload = decode_token(token)
    jti = payload.get("jti")
    
    # Placeholder: In production, add JTI to Redis blacklist
    # redis_client.setex(f"token_blacklist:{jti}", ttl_seconds, "revoked")
    
    return True
