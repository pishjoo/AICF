"""
Authentication Routes

FastAPI routes for user authentication:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- GET /auth/me
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from database.connection import get_db
from database.models import User, Organization, Role, UserRole
from app.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from app.auth.jwt import create_access_token, create_refresh_token, verify_token, TOKEN_TYPE_REFRESH
from app.auth.password import hash_password, verify_password
from app.auth.dependencies import get_current_user
from app.auth.jwt import ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user in an organization.
    
    Creates a new user account and returns authentication tokens.
    The user is assigned the default 'member' role in the organization.
    """
    # Verify organization exists
    organization = db.query(Organization).filter(
        Organization.id == user_data.organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    
    # Check if email already exists in organization
    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.organization_id == user_data.organization_id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered in this organization",
        )
    
    # Get or create default 'member' role
    member_role = db.query(Role).filter(
        Role.organization_id == user_data.organization_id,
        Role.slug == "member"
    ).first()
    
    if not member_role:
        # Create default member role if it doesn't exist
        member_role = Role(
            organization_id=user_data.organization_id,
            name="Member",
            slug="member",
            description="Standard member with basic permissions",
            is_builtin=True,
            permissions=["channel:read", "episode:read", "playlist:read"]
        )
        db.add(member_role)
        db.flush()
    
    # Create new user
    new_user = User(
        organization_id=user_data.organization_id,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        timezone=user_data.timezone,
        language=user_data.language,
        is_active=True,
        is_verified=False,  # Email verification pending
    )
    
    db.add(new_user)
    db.flush()  # Get user ID
    
    # Assign member role to new user
    user_role_assignment = UserRole(
        organization_id=user_data.organization_id,
        user_id=new_user.id,
        role_id=member_role.id,
    )
    db.add(user_role_assignment)
    db.commit()
    db.refresh(new_user)
    
    # Generate tokens
    access_token = create_access_token(
        subject=new_user.email,
        organization_id=new_user.organization_id,
        user_id=new_user.id,
        email=new_user.email,
        roles=["member"],
    )
    
    refresh_token = create_refresh_token(
        subject=new_user.email,
        organization_id=new_user.organization_id,
        user_id=new_user.id,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return tokens.
    
    Validates email/password and returns access and refresh tokens.
    Updates last_login_at timestamp on successful login.
    """
    # Find user by email
    user = db.query(User).filter(
        User.email == credentials.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    # Get user roles
    user_roles = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user.id,
        UserRole.organization_id == user.organization_id
    ).all()
    
    role_slugs = [ur.role.slug for ur in user_roles]
    
    # Collect all permissions from roles
    all_permissions = set()
    for user_role in user_roles:
        if user_role.role.permissions:
            all_permissions.update(user_role.role.permissions)
    
    # Update last login
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Generate tokens
    access_token = create_access_token(
        subject=user.email,
        organization_id=user.organization_id,
        user_id=user.id,
        email=user.email,
        roles=role_slugs,
        permissions=list(all_permissions),
    )
    
    refresh_token = create_refresh_token(
        subject=user.email,
        organization_id=user.organization_id,
        user_id=user.id,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Validates the refresh token and issues a new access token.
    If the refresh token is close to expiration, also issues a new refresh token.
    """
    try:
        payload = verify_token(token_request.refresh_token, TOKEN_TYPE_REFRESH)
        
        user_id = payload.get("user_id")
        organization_id = payload.get("organization_id")
        email = payload.get("email")
        
        if not user_id or not organization_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists and is active
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization_id,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user roles
    user_roles = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user.id,
        UserRole.organization_id == user.organization_id
    ).all()
    
    role_slugs = [ur.role.slug for ur in user_roles]
    
    # Collect all permissions from roles
    all_permissions = set()
    for user_role in user_roles:
        if user_role.role.permissions:
            all_permissions.update(user_role.role.permissions)
    
    # Generate new access token
    new_access_token = create_access_token(
        subject=user.email,
        organization_id=user.organization_id,
        user_id=user.id,
        email=user.email,
        roles=role_slugs,
        permissions=list(all_permissions),
    )
    
    # Optionally rotate refresh token if close to expiration
    # For simplicity, we'll issue a new refresh token every time
    new_refresh_token = create_refresh_token(
        subject=user.email,
        organization_id=user.organization_id,
        user_id=user.id,
    )
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Returns the profile of the currently authenticated user.
    """
    # Get user roles
    user_roles = db.query(UserRole).join(Role).filter(
        UserRole.user_id == current_user.id,
        UserRole.organization_id == current_user.organization_id
    ).all()
    
    role_slugs = [ur.role.slug for ur in user_roles]
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        organization_id=current_user.organization_id,
        timezone=current_user.timezone,
        language=current_user.language,
        roles=role_slugs,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )
