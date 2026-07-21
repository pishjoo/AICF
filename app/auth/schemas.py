"""
Authentication Schemas

Pydantic models for authentication request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class UserRegister(BaseModel):
    """Schema for user registration request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., 
        min_length=8,
        max_length=128,
        description="User password (min 8 characters)"
    )
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    organization_id: int = Field(..., description="Organization ID to join")
    timezone: Optional[str] = Field(default="UTC", description="User timezone")
    language: Optional[str] = Field(default="en", description="User language preference")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password has minimum complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "organization_id": 1,
                "timezone": "America/New_York",
                "language": "en"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    
    refresh_token: str = Field(..., description="JWT refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserResponse(BaseModel):
    """Schema for user information response."""
    
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    organization_id: int = Field(..., description="Organization ID")
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(None, description="User language preference")
    roles: List[str] = Field(default_factory=list, description="User role slugs")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "is_active": True,
                "is_verified": True,
                "organization_id": 1,
                "timezone": "America/New_York",
                "language": "en",
                "roles": ["member"],
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-15T10:30:00Z"
            }
        }


class TokenData(BaseModel):
    """Internal schema for decoded token data."""
    
    user_id: int
    email: str
    organization_id: int
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    jti: str
