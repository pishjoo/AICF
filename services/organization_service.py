"""
Organization Service

Business logic for Organization management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import Organization
from services.exceptions import NotFoundError, DuplicateError, ValidationError


class OrganizationService:
    """
    Service for managing organizations.
    
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
        name: str,
        slug: str,
        description: Optional[str] = None,
        subscription_plan: str = "free",
        max_teams: int = 5,
        max_users: int = 10,
        max_channels: int = 10,
        storage_limit_gb: float = 10.0,
        settings: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """
        Create a new organization.
        
        Args:
            name: Organization name
            slug: URL-friendly identifier (must be unique)
            description: Optional description
            subscription_plan: Subscription tier (free, pro, enterprise)
            max_teams: Maximum number of teams allowed
            max_users: Maximum number of users allowed
            max_channels: Maximum number of channels allowed
            storage_limit_gb: Storage limit in GB
            settings: JSON settings dictionary
            extra_data: Additional metadata
            
        Returns:
            Created Organization instance
            
        Raises:
            DuplicateError: If slug already exists
        """
        # Check for duplicate slug
        existing = self.db.query(Organization).filter(
            Organization.slug == slug
        ).first()
        
        if existing:
            raise DuplicateError(
                resource_type="organization",
                field="slug",
                message=f"An organization with slug '{slug}' already exists"
            )
        
        # Validate slug format
        if not slug or not slug.replace('-', '').replace('_', '').isalnum():
            raise ValidationError(
                message="Slug must contain only alphanumeric characters, hyphens, and underscores",
                field="slug"
            )
        
        organization = Organization(
            name=name,
            slug=slug,
            description=description,
            subscription_plan=subscription_plan,
            subscription_status="active",
            max_teams=max_teams,
            max_users=max_users,
            max_channels=max_channels,
            storage_limit_gb=storage_limit_gb,
            settings=settings or {},
            extra_data=extra_data or {}
        )
        
        self.db.add(organization)
        self.db.commit()
        self.db.refresh(organization)
        
        return organization
    
    def get(self, organization_id: int) -> Optional[Organization]:
        """
        Get an organization by ID.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization instance or None
        """
        return self.db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None)
        ).first()
    
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """
        Get an organization by slug.
        
        Args:
            slug: Organization slug
            
        Returns:
            Organization instance or None
        """
        return self.db.query(Organization).filter(
            Organization.slug == slug,
            Organization.deleted_at.is_(None)
        ).first()
    
    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Organization]:
        """
        List organizations with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of Organization instances
        """
        query = self.db.query(Organization).filter(
            Organization.deleted_at.is_(None)
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Organization, key):
                    query = query.filter(getattr(Organization, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count organizations.
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(Organization).filter(
            Organization.deleted_at.is_(None)
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Organization, key):
                    query = query.filter(getattr(Organization, key) == value)
        
        return query.count()
    
    def update(
        self,
        organization_id: int,
        data: Dict[str, Any]
    ) -> Optional[Organization]:
        """
        Update an organization.
        
        Args:
            organization_id: Organization ID
            data: Dictionary of fields to update
            
        Returns:
            Updated Organization instance or None
            
        Raises:
            NotFoundError: If organization not found
            DuplicateError: If updating slug to an existing one
        """
        organization = self.get(organization_id)
        
        if organization is None:
            raise NotFoundError(
                resource_type="organization",
                resource_id=organization_id
            )
        
        # Check for slug conflicts if slug is being updated
        if 'slug' in data and data['slug'] != organization.slug:
            existing = self.db.query(Organization).filter(
                Organization.slug == data['slug'],
                Organization.id != organization_id,
                Organization.deleted_at.is_(None)
            ).first()
            
            if existing:
                raise DuplicateError(
                    resource_type="organization",
                    field="slug",
                    message=f"An organization with slug '{data['slug']}' already exists"
                )
        
        # Update fields
        for key, value in data.items():
            if hasattr(organization, key) and key not in ['id', 'created_at', 'deleted_at']:
                setattr(organization, key, value)
        
        organization.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(organization)
        
        return organization
    
    def soft_delete(self, organization_id: int) -> bool:
        """
        Soft delete an organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If organization not found
        """
        organization = self.get(organization_id)
        
        if organization is None:
            raise NotFoundError(
                resource_type="organization",
                resource_id=organization_id
            )
        
        organization.deleted_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def restore(self, organization_id: int) -> Optional[Organization]:
        """
        Restore a soft-deleted organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Restored Organization instance or None
        """
        organization = self.db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.deleted_at.isnot(None)
        ).first()
        
        if organization is None:
            return None
        
        organization.deleted_at = None
        organization.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(organization)
        
        return organization
