"""
Playlist Service

Business logic for Playlist management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import Playlist, ChannelProfile, PlaylistType
from services.exceptions import NotFoundError, ValidationError


class PlaylistService:
    """
    Service for managing playlists within organizations.
    
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
        playlist_type: PlaylistType,
        channel_profile_id: int,
        creator_id: Optional[int] = None,
        description: Optional[str] = None,
        source_urls: Optional[List[str]] = None,
        monitoring_keywords: Optional[List[str]] = None,
        auto_generate: bool = False,
        episode_roadmap: Optional[Dict[str, Any]] = None,
        total_planned_episodes: Optional[int] = None,
        production_template_id: Optional[int] = None,
        default_character: Optional[str] = None,
        default_style: Optional[str] = None,
        default_duration: Optional[str] = None,
        default_format: Optional[str] = None,
        is_active: bool = True,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Playlist:
        """
        Create a new playlist within an organization.
        
        Args:
            organization_id: Organization ID (tenant isolation)
            title: Playlist title
            playlist_type: Type (PLANNED_PLAYLIST or DYNAMIC_PLAYLIST)
            channel_profile_id: Associated channel profile ID
            creator_id: User ID of creator
            description: Playlist description
            source_urls: RSS feeds/websites for dynamic playlists
            monitoring_keywords: Keywords for topic discovery
            auto_generate: Enable auto-generation for dynamic playlists
            episode_roadmap: Pre-defined episode topics for planned playlists
            total_planned_episodes: Total planned episodes count
            production_template_id: Default production template
            default_character: Default character for episodes
            default_style: Default style for episodes
            default_duration: Default duration for episodes
            default_format: Default format for episodes
            is_active: Active status
            extra_data: Additional metadata
            
        Returns:
            Created Playlist instance
            
        Raises:
            NotFoundError: If channel profile not found
            ValidationError: If playlist type is invalid
        """
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
        
        # Validate playlist type
        if isinstance(playlist_type, str):
            try:
                playlist_type = PlaylistType(playlist_type)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid playlist type. Must be one of: {[t.value for t in PlaylistType]}",
                    field="playlist_type"
                )
        
        playlist = Playlist(
            organization_id=organization_id,
            title=title,
            description=description,
            playlist_type=playlist_type,
            channel_profile_id=channel_profile_id,
            creator_id=creator_id,
            source_urls=source_urls or [],
            monitoring_keywords=monitoring_keywords or [],
            auto_generate=auto_generate,
            episode_roadmap=episode_roadmap,
            total_planned_episodes=total_planned_episodes,
            production_template_id=production_template_id,
            default_character=default_character,
            default_style=default_style,
            default_duration=default_duration,
            default_format=default_format,
            is_active=is_active,
            extra_data=extra_data or {}
        )
        
        self.db.add(playlist)
        self.db.commit()
        self.db.refresh(playlist)
        
        return playlist
    
    def get(self, playlist_id: int, organization_id: Optional[int] = None) -> Optional[Playlist]:
        """
        Get a playlist by ID.
        
        Args:
            playlist_id: Playlist ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Playlist instance or None
        """
        query = self.db.query(Playlist).filter(Playlist.id == playlist_id)
        
        if organization_id is not None:
            query = query.filter(Playlist.organization_id == organization_id)
        
        return query.first()
    
    def list(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Playlist]:
        """
        List playlists within an organization with pagination.
        
        Args:
            organization_id: Organization ID (tenant isolation - required)
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of Playlist instances
        """
        query = self.db.query(Playlist).filter(
            Playlist.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Playlist, key):
                    query = query.filter(getattr(Playlist, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: int, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count playlists within an organization.
        
        Args:
            organization_id: Organization ID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(Playlist).filter(
            Playlist.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(Playlist, key):
                    query = query.filter(getattr(Playlist, key) == value)
        
        return query.count()
    
    def update(
        self,
        playlist_id: int,
        data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> Optional[Playlist]:
        """
        Update a playlist.
        
        Args:
            playlist_id: Playlist ID
            data: Dictionary of fields to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated Playlist instance or None
            
        Raises:
            NotFoundError: If playlist not found
        """
        playlist = self.get(playlist_id, organization_id)
        
        if playlist is None:
            raise NotFoundError(
                resource_type="playlist",
                resource_id=playlist_id
            )
        
        # Handle playlist_type conversion if provided as string
        if 'playlist_type' in data and isinstance(data['playlist_type'], str):
            try:
                data['playlist_type'] = PlaylistType(data['playlist_type'])
            except ValueError:
                raise ValidationError(
                    message=f"Invalid playlist type. Must be one of: {[t.value for t in PlaylistType]}",
                    field="playlist_type"
                )
        
        # Update fields (protect certain fields)
        protected_fields = ['id', 'organization_id', 'created_at']
        for key, value in data.items():
            if hasattr(playlist, key) and key not in protected_fields:
                setattr(playlist, key, value)
        
        playlist.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(playlist)
        
        return playlist
    
    def activate(self, playlist_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Activate a playlist.
        
        Args:
            playlist_id: Playlist ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if activated
            
        Raises:
            NotFoundError: If playlist not found
        """
        playlist = self.get(playlist_id, organization_id)
        
        if playlist is None:
            raise NotFoundError(
                resource_type="playlist",
                resource_id=playlist_id
            )
        
        playlist.is_active = True
        playlist.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def deactivate(self, playlist_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Deactivate a playlist.
        
        Args:
            playlist_id: Playlist ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deactivated
            
        Raises:
            NotFoundError: If playlist not found
        """
        playlist = self.get(playlist_id, organization_id)
        
        if playlist is None:
            raise NotFoundError(
                resource_type="playlist",
                resource_id=playlist_id
            )
        
        playlist.is_active = False
        playlist.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
