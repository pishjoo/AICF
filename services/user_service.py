"""
User Service

Business logic for User management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import User, Organization
from services.exceptions import NotFoundError, DuplicateError, ValidationError, PermissionDeniedError


class UserService:
    """
    Service for managing users within organizations.
    
    All methods enforce tenant isolation and business rules.
    """
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(
        self,
        organization_id: int,
        email: str,
        full_name: str,
        password_hash: Optional[str] = None,
        external_auth_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: str = "UTC",
        language: str = "en",
        is_verified: bool = False,
        settings: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Create a new user within an organization.
        
        Args:
            organization_id: Organization ID (tenant isolation)
            email: User email (must be unique within organization)
            full_name: User's full name
            password_hash: Hashed password (None for OAuth users)
            external_auth_id: External auth provider ID
            avatar_url: Profile picture URL
            timezone: User timezone
            language: Language preference
            is_verified: Email verification status
            settings: JSON settings dictionary
            extra_data: Additional metadata
            
        Returns:
            Created User instance
            
        Raises:
            DuplicateError: If email already exists in organization
            NotFoundError: If organization not found
        """
        # Verify organization exists
        org = self.db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None)
        ).first()
        
        if org is None:
            raise NotFoundError(
                resource_type="organization",
                resource_id=organization_id
            )
        
        # Check for duplicate email within organization
        existing = self.db.query(User).filter(
            User.organization_id == organization_id,
            User.email == email
        ).first()
        
        if existing:
            raise DuplicateError(
                resource_type="user",
                field="email",
                message=f"A user with email '{email}' already exists in this organization"
            )
        
        # Validate email format
        if not email or '@' not in email:
            raise ValidationError(
                message="Invalid email format",
                field="email"
            )
        
        user = User(
            organization_id=organization_id,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            external_auth_id=external_auth_id,
            avatar_url=avatar_url,
            timezone=timezone,
            language=language,
            is_active=True,
            is_verified=is_verified,
            settings=settings or {},
            extra_data=extra_data or {}
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get(self, user_id: int, organization_id: Optional[int] = None) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            User instance or None
        """
        query = self.db.query(User).filter(User.id == user_id)
        
        if organization_id is not None:
            query = query.filter(User.organization_id == organization_id)
        
        return query.first()
    
    def get_by_email(
        self,
        email: str,
        organization_id: int
    ) -> Optional[User]:
        """
        Get a user by email within an organization.
        
        Args:
            email: User email
            organization_id: Organization ID
            
        Returns:
            User instance or None
        """
        return self.db.query(User).filter(
            User.organization_id == organization_id,
            User.email == email
        ).first()
    
    def list(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[User]:
        """
        List users within an organization with pagination.
        
        Args:
            organization_id: Organization ID (tenant isolation - required)
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of User instances
        """
        query = self.db.query(User).filter(
            User.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(User, key):
                    query = query.filter(getattr(User, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: int, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count users within an organization.
        
        Args:
            organization_id: Organization ID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(User).filter(
            User.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(User, key):
                    query = query.filter(getattr(User, key) == value)
        
        return query.count()
    
    def update(
        self,
        user_id: int,
        data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> Optional[User]:
        """
        Update a user.
        
        Args:
            user_id: User ID
            data: Dictionary of fields to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated User instance or None
            
        Raises:
            NotFoundError: If user not found
            DuplicateError: If updating email to an existing one
        """
        user = self.get(user_id, organization_id)
        
        if user is None:
            raise NotFoundError(
                resource_type="user",
                resource_id=user_id
            )
        
        # Check for email conflicts if email is being updated
        if 'email' in data and data['email'] != user.email:
            org_id = organization_id or user.organization_id
            existing = self.db.query(User).filter(
                User.organization_id == org_id,
                User.email == data['email'],
                User.id != user_id
            ).first()
            
            if existing:
                raise DuplicateError(
                    resource_type="user",
                    field="email",
                    message=f"A user with email '{data['email']}' already exists in this organization"
                )
        
        # Update fields (protect certain fields)
        protected_fields = ['id', 'organization_id', 'created_at']
        for key, value in data.items():
            if hasattr(user, key) and key not in protected_fields:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def deactivate(self, user_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deactivated
            
        Raises:
            NotFoundError: If user not found
        """
        user = self.get(user_id, organization_id)
        
        if user is None:
            raise NotFoundError(
                resource_type="user",
                resource_id=user_id
            )
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def activate(self, user_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Activate a user account.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if activated
            
        Raises:
            NotFoundError: If user not found
        """
        user = self.get(user_id, organization_id)
        
        if user is None:
            raise NotFoundError(
                resource_type="user",
                resource_id=user_id
            )
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            return False
        
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return True
