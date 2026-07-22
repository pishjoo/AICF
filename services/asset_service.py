"""
Asset Service

Business logic for Asset management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import Asset, Episode, AssetType
from services.exceptions import NotFoundError, ValidationError


class AssetService:
    """
    Service for managing assets within organizations.
    
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
        filename: str,
        asset_type: AssetType,
        episode_id: Optional[int] = None,
        original_filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        storage_provider: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        storage_path: Optional[str] = None,
        storage_url: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        dimensions: Optional[str] = None,
        processing_status: str = "pending",
        processing_metadata: Optional[Dict[str, Any]] = None,
        thumbnail_url: Optional[str] = None,
        preview_url: Optional[str] = None,
        alt_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Asset:
        """
        Create a new asset within an organization.
        
        Args:
            organization_id: Organization ID (tenant isolation)
            filename: Asset filename
            asset_type: Type of asset (image, video, audio, etc.)
            episode_id: Associated episode ID
            original_filename: Original uploaded filename
            mime_type: MIME type of the file
            storage_provider: Storage provider (s3, gcs, local)
            storage_bucket: Storage bucket name
            storage_path: Path in storage
            storage_url: Public or signed URL
            file_size_bytes: File size in bytes
            duration_seconds: Duration for audio/video
            dimensions: Dimensions (Width x Height)
            processing_status: Processing status
            processing_metadata: Processing metadata
            thumbnail_url: Thumbnail URL
            preview_url: Preview URL
            alt_text: Alternative text
            tags: Tags list
            extra_data: Additional metadata
            
        Returns:
            Created Asset instance
            
        Raises:
            NotFoundError: If episode not found (when episode_id provided)
            ValidationError: If asset type is invalid
        """
        # Verify episode exists and belongs to organization if provided
        if episode_id is not None:
            episode = self.db.query(Episode).filter(
                Episode.id == episode_id,
                Episode.organization_id == organization_id
            ).first()
            
            if episode is None:
                raise NotFoundError(
                    resource_type="episode",
                    resource_id=episode_id
                )
        
        # Validate asset type
        if isinstance(asset_type, str):
            try:
                asset_type = AssetType(asset_type)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid asset type. Must be one of: {[t.value for t in AssetType]}",
                    field="asset_type"
                )
        
        asset = Asset(
            organization_id=organization_id,
            filename=filename,
            original_filename=original_filename,
            asset_type=asset_type,
            mime_type=mime_type,
            episode_id=episode_id,
            storage_provider=storage_provider,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            storage_url=storage_url,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
            dimensions=dimensions,
            processing_status=processing_status,
            processing_metadata=processing_metadata,
            thumbnail_url=thumbnail_url,
            preview_url=preview_url,
            alt_text=alt_text,
            tags=tags or [],
            extra_data=extra_data or {}
        )
        
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        
        return asset
    
    def get(self, asset_id: int, organization_id: Optional[int] = None) -> Optional[Asset]:
        """
        Get an asset by ID.
        
        Args:
            asset_id: Asset ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Asset instance or None
        """
        query = self.db.query(Asset).filter(Asset.id == asset_id)
        
        if organization_id is not None:
            query = query.filter(Asset.organization_id == organization_id)
        
        return query.first()
    
    def list(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Asset]:
        """
        List assets within an organization with pagination.
        
        Args:
            organization_id: Organization ID (tenant isolation - required)
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of Asset instances
        """
        query = self.db.query(Asset).filter(
            Asset.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Asset, key):
                    query = query.filter(getattr(Asset, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: int, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count assets within an organization.
        
        Args:
            organization_id: Organization ID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(Asset).filter(
            Asset.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Asset, key):
                    query = query.filter(getattr(Asset, key) == value)
        
        return query.count()
    
    def delete(self, asset_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Delete an asset.
        
        Args:
            asset_id: Asset ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If asset not found
        """
        asset = self.get(asset_id, organization_id)
        
        if asset is None:
            raise NotFoundError(
                resource_type="asset",
                resource_id=asset_id
            )
        
        self.db.delete(asset)
        self.db.commit()
        
        return True
    
    def update_processing_status(
        self,
        asset_id: int,
        processing_status: str,
        processing_metadata: Optional[Dict[str, Any]] = None,
        organization_id: Optional[int] = None
    ) -> Optional[Asset]:
        """
        Update asset processing status.
        
        Args:
            asset_id: Asset ID
            processing_status: New processing status
            processing_metadata: Processing metadata
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Asset instance or None
            
        Raises:
            NotFoundError: If asset not found
        """
        asset = self.get(asset_id, organization_id)
        
        if asset is None:
            raise NotFoundError(
                resource_type="asset",
                resource_id=asset_id
            )
        
        asset.processing_status = processing_status
        if processing_metadata:
            asset.processing_metadata = processing_metadata
        asset.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(asset)
        
        return asset
    
    def update(
        self,
        asset_id: int,
        data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> Optional[Asset]:
        """
        Update an asset.
        
        Args:
            asset_id: Asset ID
            data: Dictionary of fields to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Asset instance or None
            
        Raises:
            NotFoundError: If asset not found
        """
        asset = self.get(asset_id, organization_id)
        
        if asset is None:
            raise NotFoundError(
                resource_type="asset",
                resource_id=asset_id
            )
        
        # Handle asset_type conversion if provided as string
        if 'asset_type' in data and isinstance(data['asset_type'], str):
            try:
                data['asset_type'] = AssetType(data['asset_type'])
            except ValueError:
                raise ValidationError(
                    message=f"Invalid asset type. Must be one of: {[t.value for t in AssetType]}",
                    field="asset_type"
                )
        
        # Update fields (protect certain fields)
        protected_fields = ['id', 'organization_id', 'created_at']
        for key, value in data.items():
            if hasattr(asset, key) and key not in protected_fields:
                setattr(asset, key, value)
        
        asset.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(asset)
        
        return asset
