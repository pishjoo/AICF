"""
Episode Service

Business logic for Episode management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import Episode, Playlist, ChannelProfile, EpisodeStatus
from services.exceptions import NotFoundError, ValidationError


class EpisodeService:
    """
    Service for managing episodes within organizations.
    
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
        title: str,
        playlist_id: int,
        channel_profile_id: int,
        creator_id: Optional[int] = None,
        description: Optional[str] = None,
        status: EpisodeStatus = EpisodeStatus.PLANNED,
        topic: Optional[str] = None,
        research_data: Optional[Dict[str, Any]] = None,
        script: Optional[str] = None,
        storyboard: Optional[List[Any]] = None,
        production_template_id: Optional[int] = None,
        seo_data: Optional[Dict[str, Any]] = None,
        scheduled_for: Optional[datetime] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Episode:
        """
        Create a new episode within an organization.
        
        Args:
            organization_id: Organization ID (tenant isolation)
            title: Episode title
            playlist_id: Associated playlist ID
            channel_profile_id: Associated channel profile ID
            creator_id: User ID of creator
            description: Episode description
            status: Initial status (default: PLANNED)
            topic: Episode topic
            research_data: Research data dictionary
            script: Episode script
            storyboard: Storyboard data
            production_template_id: Production template ID
            seo_data: SEO metadata
            scheduled_for: Scheduled publish time
            extra_data: Additional metadata
            
        Returns:
            Created Episode instance
            
        Raises:
            NotFoundError: If playlist or channel profile not found
            ValidationError: If status is invalid
        """
        # Verify playlist exists and belongs to organization
        playlist = self.db.query(Playlist).filter(
            Playlist.id == playlist_id,
            Playlist.organization_id == organization_id
        ).first()
        
        if playlist is None:
            raise NotFoundError(
                resource_type="playlist",
                resource_id=playlist_id
            )
        
        # Verify channel profile exists and belongs to organization
        channel = self.db.query(ChannelProfile).filter(
            ChannelProfile.id == channel_profile_id,
            ChannelProfile.organization_id == organization_id
        ).first()
        
        if channel is None:
            raise NotFoundError(
                resource_type="channel_profile",
                resource_id=channel_profile_id
            )
        
        # Validate status
        if isinstance(status, str):
            try:
                status = EpisodeStatus(status)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid episode status. Must be one of: {[s.value for s in EpisodeStatus]}",
                    field="status"
                )
        
        episode = Episode(
            organization_id=organization_id,
            title=title,
            description=description,
            status=status,
            playlist_id=playlist_id,
            channel_profile_id=channel_profile_id,
            creator_id=creator_id,
            topic=topic,
            research_data=research_data or {},
            script=script,
            storyboard=storyboard or [],
            production_template_id=production_template_id,
            assets=[],
            seo_data=seo_data or {},
            scheduled_for=scheduled_for,
            extra_data=extra_data or {}
        )
        
        self.db.add(episode)
        self.db.commit()
        self.db.refresh(episode)
        
        return episode
    
    def get(self, episode_id: int, organization_id: Optional[int] = None) -> Optional[Episode]:
        """
        Get an episode by ID.
        
        Args:
            episode_id: Episode ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Episode instance or None
        """
        query = self.db.query(Episode).filter(Episode.id == episode_id)
        
        if organization_id is not None:
            query = query.filter(Episode.organization_id == organization_id)
        
        return query.first()
    
    def list(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Episode]:
        """
        List episodes within an organization with pagination.
        
        Args:
            organization_id: Organization ID (tenant isolation - required)
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of Episode instances
        """
        query = self.db.query(Episode).filter(
            Episode.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Episode, key):
                    query = query.filter(getattr(Episode, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: int, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count episodes within an organization.
        
        Args:
            organization_id: Organization ID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(Episode).filter(
            Episode.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Episode, key):
                    query = query.filter(getattr(Episode, key) == value)
        
        return query.count()
    
    def update_status(
        self,
        episode_id: int,
        status: EpisodeStatus,
        organization_id: Optional[int] = None,
        review_notes: Optional[str] = None,
        approved_by: Optional[int] = None
    ) -> Optional[Episode]:
        """
        Update an episode's status.
        
        Args:
            episode_id: Episode ID
            status: New status
            organization_id: Optional organization ID for tenant isolation
            review_notes: Optional review notes
            approved_by: User ID of approver (for APPROVED status)
            
        Returns:
            Updated Episode instance or None
            
        Raises:
            NotFoundError: If episode not found
            ValidationError: If status is invalid
        """
        episode = self.get(episode_id, organization_id)
        
        if episode is None:
            raise NotFoundError(
                resource_type="episode",
                resource_id=episode_id
            )
        
        # Validate status
        if isinstance(status, str):
            try:
                status = EpisodeStatus(status)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid episode status. Must be one of: {[s.value for s in EpisodeStatus]}",
                    field="status"
                )
        
        episode.status = status
        episode.updated_at = datetime.utcnow()
        
        # Handle approval workflow
        if status == EpisodeStatus.APPROVED:
            episode.approved_by = approved_by
            episode.approved_at = datetime.utcnow()
        
        if review_notes:
            episode.review_notes = review_notes
        
        self.db.commit()
        self.db.refresh(episode)
        
        return episode
    
    def update(
        self,
        episode_id: int,
        data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> Optional[Episode]:
        """
        Update an episode.
        
        Args:
            episode_id: Episode ID
            data: Dictionary of fields to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Episode instance or None
            
        Raises:
            NotFoundError: If episode not found
        """
        episode = self.get(episode_id, organization_id)
        
        if episode is None:
            raise NotFoundError(
                resource_type="episode",
                resource_id=episode_id
            )
        
        # Handle status conversion if provided as string
        if 'status' in data and isinstance(data['status'], str):
            try:
                data['status'] = EpisodeStatus(data['status'])
            except ValueError:
                raise ValidationError(
                    message=f"Invalid episode status. Must be one of: {[s.value for s in EpisodeStatus]}",
                    field="status"
                )
        
        # Update fields (protect certain fields)
        protected_fields = ['id', 'organization_id', 'created_at']
        for key, value in data.items():
            if hasattr(episode, key) and key not in protected_fields:
                setattr(episode, key, value)
        
        episode.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(episode)
        
        return episode
    
    def approve(
        self,
        episode_id: int,
        approved_by: int,
        organization_id: Optional[int] = None
    ) -> Optional[Episode]:
        """
        Approve an episode for publication.
        
        Args:
            episode_id: Episode ID
            approved_by: User ID of approver
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Episode instance or None
            
        Raises:
            NotFoundError: If episode not found
        """
        return self.update_status(
            episode_id=episode_id,
            status=EpisodeStatus.APPROVED,
            organization_id=organization_id,
            approved_by=approved_by
        )
    
    def publish(
        self,
        episode_id: int,
        published_url: str,
        publish_metadata: Optional[Dict[str, Any]] = None,
        organization_id: Optional[int] = None
    ) -> Optional[Episode]:
        """
        Mark an episode as published.
        
        Args:
            episode_id: Episode ID
            published_url: URL where episode is published
            publish_metadata: Platform-specific publish data
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Episode instance or None
            
        Raises:
            NotFoundError: If episode not found
        """
        episode = self.get(episode_id, organization_id)
        
        if episode is None:
            raise NotFoundError(
                resource_type="episode",
                resource_id=episode_id
            )
        
        episode.status = EpisodeStatus.PUBLISHED
        episode.published_url = published_url
        episode.publish_metadata = publish_metadata or {}
        episode.published_at = datetime.utcnow()
        episode.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(episode)
        
        return episode
