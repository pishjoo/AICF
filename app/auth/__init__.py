"""
AICF Authentication Module

JWT-based authentication and authorization for multi-tenant SaaS.
"""

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
)
from app.auth.password import (
    hash_password,
    verify_password,
)
from app.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from app.auth.dependencies import (
    get_current_user,
    require_permission,
    get_current_organization,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_REFRESH",
    # Password
    "hash_password",
    "verify_password",
    # Schemas
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    # Dependencies
    "get_current_user",
    "require_permission",
    "get_current_organization",
]
