"""
API Dependencies

FastAPI dependencies for authentication, authorization, and context.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from typing import Optional, List

from database.connection import get_db
from database.models import User, Role, UserRole, Organization
from app.auth.jwt import verify_token, TOKEN_TYPE_ACCESS
from app.auth.schemas import TokenData


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = verify_token(token, TOKEN_TYPE_ACCESS)
        
        user_id = payload.get("user_id")
        organization_id = payload.get("organization_id")
        email = payload.get("email")
        
        if user_id is None or organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization_id,
        User.is_active == True
    ).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_permission(required_permission: str):
    """
    Dependency factory to check if user has a specific permission.
    
    Args:
        required_permission: Permission slug to check (e.g., "channel:create")
        
    Returns:
        Dependency function that checks permission
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        # Check if user has OWNER or ADMIN role (full access)
        user_roles = db.query(UserRole).join(Role).filter(
            UserRole.user_id == current_user.id,
            UserRole.organization_id == current_user.organization_id
        ).all()
        
        # Collect all permissions from roles
        all_permissions = set()
        role_slugs = []
        
        for user_role in user_roles:
            role = user_role.role
            role_slugs.append(role.slug)
            
            # Check for built-in admin roles
            if role.slug in ["owner", "admin"]:
                return True
            
            # Add role permissions
            if role.permissions:
                all_permissions.update(role.permissions)
        
        # Check if required permission is granted
        if required_permission in all_permissions:
            return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_permission} required",
        )
    
    return permission_checker


def require_role(required_role: str):
    """
    Dependency factory to check if user has a specific role.
    
    Args:
        required_role: Role slug to check (e.g., "admin", "manager")
        
    Returns:
        Dependency function that checks role
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        # Query user roles
        user_roles = db.query(UserRole).join(Role).filter(
            UserRole.user_id == current_user.id,
            UserRole.organization_id == current_user.organization_id
        ).all()
        
        role_slugs = [ur.role.slug for ur in user_roles]
        
        # Check hierarchy: owner > admin > manager > member > viewer
        role_hierarchy = ["owner", "admin", "manager", "member", "viewer"]
        
        if required_role not in role_hierarchy:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid role: {required_role}",
            )
        
        # Check if user has the required role or higher
        user_max_level = -1
        required_level = role_hierarchy.index(required_role)
        
        for role_slug in role_slugs:
            if role_slug in role_hierarchy:
                user_level = role_hierarchy.index(role_slug)
                user_max_level = max(user_max_level, user_level)
        
        if user_max_level >= required_level:
            return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role denied: {required_role} or higher required",
        )
    
    return role_checker


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to check if user has admin privileges.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Authenticated user if they have admin role
        
    Raises:
        HTTPException: If user doesn't have admin privileges
    """
    user_roles = db.query(UserRole).join(Role).filter(
        UserRole.user_id == current_user.id,
        UserRole.organization_id == current_user.organization_id
    ).all()
    
    role_slugs = [ur.role.slug for ur in user_roles]
    
    if "owner" in role_slugs or "admin" in role_slugs:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges required",
    )


async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Organization:
    """
    Get the current user's organization object.
    
    This dependency extracts the organization context from the
    authenticated user for tenant isolation.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Organization object
    """
    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id,
        Organization.deleted_at == None
    ).first()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization not found or deleted",
        )
    
    return org


class TenantIsolationChecker:
    """
    Class-based dependency for tenant isolation checks.
    
    Use this to ensure resources belong to the user's organization.
    """
    
    def __init__(self, model_class, resource_id_param: str = "resource_id"):
        """
        Initialize with the model class to check.
        
        Args:
            model_class: SQLAlchemy model class with organization_id field
            resource_id_param: Name of the path/query parameter containing resource ID
        """
        self.model_class = model_class
        self.resource_id_param = resource_id_param
    
    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """
        Check that the requested resource belongs to user's organization.
        
        Args:
            request: FastAPI request object
            current_user: Authenticated user
            db: Database session
            
        Returns:
            The resource object if it belongs to user's organization
            
        Raises:
            HTTPException: If resource doesn't exist or belongs to different org
        """
        # Get resource ID from path or query params
        resource_id = request.path_params.get(self.resource_id_param) or \
                      request.query_params.get(self.resource_id_param)
        
        if resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing resource ID parameter: {self.resource_id_param}",
            )
        
        # Fetch resource and verify organization ownership
        resource = db.query(self.model_class).filter(
            self.model_class.id == resource_id,
            self.model_class.organization_id == current_user.organization_id
        ).first()
        
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found or access denied",
            )
        
        # Inject organization into request state for middleware
        request.state.organization_id = current_user.organization_id
        
        return resource
