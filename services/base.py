"""
Service Layer

Business logic services for AICF v2 API.
Following the pattern: Router -> Dependency -> Service -> Repository/Database -> Model
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Type, Any, Dict
from datetime import datetime


class BaseService:
    """
    Base service class with common CRUD operations.
    
    All services should inherit from this class.
    """
    
    def __init__(self, db: Session, model_class: Type):
        """
        Initialize service with database session and model class.
        
        Args:
            db: SQLAlchemy database session
            model_class: SQLAlchemy model class
        """
        self.db = db
        self.model_class = model_class
    
    def get(self, resource_id: int, organization_id: Optional[int] = None) -> Optional[Any]:
        """
        Get a single resource by ID.
        
        Args:
            resource_id: Resource ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Resource object or None
        """
        query = self.db.query(self.model_class).filter(
            self.model_class.id == resource_id
        )
        
        if organization_id is not None and hasattr(self.model_class, 'organization_id'):
            query = query.filter(self.model_class.organization_id == organization_id)
        
        return query.first()
    
    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        organization_id: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[Any]:
        """
        List resources with pagination and optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            organization_id: Optional organization ID for tenant isolation
            filters: Optional dictionary of filter criteria
            
        Returns:
            List of resource objects
        """
        query = self.db.query(self.model_class)
        
        if organization_id is not None and hasattr(self.model_class, 'organization_id'):
            query = query.filter(self.model_class.organization_id == organization_id)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: Optional[int] = None, filters: Optional[Dict] = None) -> int:
        """
        Count resources with optional filtering.
        
        Args:
            organization_id: Optional organization ID for tenant isolation
            filters: Optional dictionary of filter criteria
            
        Returns:
            Total count of resources
        """
        query = self.db.query(self.model_class)
        
        if organization_id is not None and hasattr(self.model_class, 'organization_id'):
            query = query.filter(self.model_class.organization_id == organization_id)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
        
        return query.count()
    
    def create(self, data: Dict[str, Any], organization_id: Optional[int] = None) -> Any:
        """
        Create a new resource.
        
        Args:
            data: Dictionary of field values
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Created resource object
        """
        if organization_id is not None and hasattr(self.model_class, 'organization_id'):
            data['organization_id'] = organization_id
        
        db_resource = self.model_class(**data)
        self.db.add(db_resource)
        self.db.commit()
        self.db.refresh(db_resource)
        return db_resource
    
    def update(self, resource_id: int, data: Dict[str, Any], organization_id: Optional[int] = None) -> Optional[Any]:
        """
        Update an existing resource.
        
        Args:
            resource_id: Resource ID
            data: Dictionary of field values to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated resource object or None
        """
        resource = self.get(resource_id, organization_id)
        
        if resource is None:
            return None
        
        for key, value in data.items():
            if hasattr(resource, key):
                setattr(resource, key, value)
        
        self.db.commit()
        self.db.refresh(resource)
        return resource
    
    def delete(self, resource_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Delete a resource.
        
        Args:
            resource_id: Resource ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deleted, False if not found
        """
        resource = self.get(resource_id, organization_id)
        
        if resource is None:
            return False
        
        self.db.delete(resource)
        self.db.commit()
        return True


def get_pagination_params(page: int = 1, limit: int = 20) -> tuple:
    """
    Calculate skip and limit for pagination.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
        
    Returns:
        Tuple of (skip, limit)
    """
    skip = (page - 1) * limit
    return skip, min(limit, 100)  # Cap at 100
