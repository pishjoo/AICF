"""
Channel Service

Business logic for ChannelProfile management.
Handles CRUD operations with tenant isolation enforcement.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import ChannelProfile, Organization
from services.exceptions import NotFoundError, DuplicateError, ValidationError


class ChannelService:
    """
    Service for managing channel profiles within organizations.
    
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
        name: str,
        platform: str,
        description: Optional[str] = None,
        team_id: Optional[int] = None,
        audience_definition: Optional[str] = None,
        age_range_min: Optional[int] = None,
        age_range_max: Optional[int] = None,
        gender_focus: Optional[str] = None,
        interests: Optional[List[str]] = None,
        content_style: Optional[str] = None,
        tone: Optional[str] = None,
        language: str = "English",
        visual_identity: Optional[Dict[str, Any]] = None,
        image_dimensions: Optional[str] = None,
        video_format: Optional[str] = None,
        aspect_ratio: str = "16:9",
        voice_type: Optional[str] = None,
        character_avatar: Optional[Dict[str, Any]] = None,
        branding_rules: Optional[Dict[str, Any]] = None,
        forbidden_elements: Optional[List[str]] = None,
        recurring_characters: Optional[List[str]] = None,
        hashtag_strategy: Optional[List[str]] = None,
        seo_rules: Optional[Dict[str, Any]] = None,
        storytelling_rules: Optional[str] = None,
        music_style: Optional[str] = None,
        is_active: bool = True,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> ChannelProfile:
        """
        Create a new channel profile within an organization.
        
        Args:
            organization_id: Organization ID (tenant isolation)
            name: Channel name
            platform: Target platform (youtube, instagram, tiktok, etc.)
            description: Channel description
            team_id: Optional team ID
            audience_definition: Target audience description
            age_range_min: Minimum age of target audience
            age_range_max: Maximum age of target audience
            gender_focus: Gender focus (male, female, all, non-binary)
            interests: List of interest keywords
            content_style: Content style (educational, entertainment, etc.)
            tone: Tone (professional, casual, humorous, etc.)
            language: Primary language
            visual_identity: Visual identity settings (colors, fonts, logo)
            image_dimensions: Image dimensions (e.g., "1920x1080")
            video_format: Video format (mp4, mov, etc.)
            aspect_ratio: Aspect ratio (default "16:9")
            voice_type: Voice type for audio generation
            character_avatar: Character descriptions
            branding_rules: Branding guidelines
            forbidden_elements: Elements to avoid
            recurring_characters: Recurring characters list
            hashtag_strategy: Default hashtags
            seo_rules: SEO guidelines
            storytelling_rules: Storytelling guidelines
            music_style: Music style preference
            is_active: Active status
            extra_data: Additional metadata
            
        Returns:
            Created ChannelProfile instance
            
        Raises:
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
        
        channel = ChannelProfile(
            organization_id=organization_id,
            name=name,
            description=description,
            platform=platform,
            team_id=team_id,
            audience_definition=audience_definition,
            age_range_min=age_range_min,
            age_range_max=age_range_max,
            gender_focus=gender_focus,
            interests=interests or [],
            content_style=content_style,
            tone=tone,
            language=language,
            visual_identity=visual_identity,
            image_dimensions=image_dimensions,
            video_format=video_format,
            aspect_ratio=aspect_ratio,
            voice_type=voice_type,
            character_avatar=character_avatar,
            branding_rules=branding_rules,
            forbidden_elements=forbidden_elements or [],
            recurring_characters=recurring_characters or [],
            hashtag_strategy=hashtag_strategy or [],
            seo_rules=seo_rules,
            storytelling_rules=storytelling_rules,
            music_style=music_style,
            is_active=is_active,
            extra_data=extra_data or {}
        )
        
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        
        return channel
    
    def get(self, channel_id: int, organization_id: Optional[int] = None) -> Optional[ChannelProfile]:
        """
        Get a channel profile by ID.
        
        Args:
            channel_id: Channel profile ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            ChannelProfile instance or None
        """
        query = self.db.query(ChannelProfile).filter(ChannelProfile.id == channel_id)
        
        if organization_id is not None:
            query = query.filter(ChannelProfile.organization_id == organization_id)
        
        return query.first()
    
    def list(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ChannelProfile]:
        """
        List channel profiles within an organization with pagination.
        
        Args:
            organization_id: Organization ID (tenant isolation - required)
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter criteria
            
        Returns:
            List of ChannelProfile instances
        """
        query = self.db.query(ChannelProfile).filter(
            ChannelProfile.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(ChannelProfile, key):
                    query = query.filter(getattr(ChannelProfile, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, organization_id: int, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count channel profiles within an organization.
        
        Args:
            organization_id: Organization ID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        query = self.db.query(ChannelProfile).filter(
            ChannelProfile.organization_id == organization_id
        )
        
        if filters:
            for key, value in filters.items():
                if hasattr(ChannelProfile, key):
                    query = query.filter(getattr(ChannelProfile, key) == value)
        
        return query.count()
    
    def update(
        self,
        channel_id: int,
        data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> Optional[ChannelProfile]:
        """
        Update a channel profile.
        
        Args:
            channel_id: Channel profile ID
            data: Dictionary of fields to update
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            Updated ChannelProfile instance or None
            
        Raises:
            NotFoundError: If channel profile not found
        """
        channel = self.get(channel_id, organization_id)
        
        if channel is None:
            raise NotFoundError(
                resource_type="channel_profile",
                resource_id=channel_id
            )
        
        # Update fields (protect certain fields)
        protected_fields = ['id', 'organization_id', 'created_at']
        for key, value in data.items():
            if hasattr(channel, key) and key not in protected_fields:
                setattr(channel, key, value)
        
        channel.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(channel)
        
        return channel
    
    def delete(self, channel_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Delete a channel profile.
        
        Args:
            channel_id: Channel profile ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If channel profile not found
        """
        channel = self.get(channel_id, organization_id)
        
        if channel is None:
            raise NotFoundError(
                resource_type="channel_profile",
                resource_id=channel_id
            )
        
        self.db.delete(channel)
        self.db.commit()
        
        return True
    
    def activate(self, channel_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Activate a channel profile.
        
        Args:
            channel_id: Channel profile ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if activated
            
        Raises:
            NotFoundError: If channel profile not found
        """
        channel = self.get(channel_id, organization_id)
        
        if channel is None:
            raise NotFoundError(
                resource_type="channel_profile",
                resource_id=channel_id
            )
        
        channel.is_active = True
        channel.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
    
    def deactivate(self, channel_id: int, organization_id: Optional[int] = None) -> bool:
        """
        Deactivate a channel profile.
        
        Args:
            channel_id: Channel profile ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            True if deactivated
            
        Raises:
            NotFoundError: If channel profile not found
        """
        channel = self.get(channel_id, organization_id)
        
        if channel is None:
            raise NotFoundError(
                resource_type="channel_profile",
                resource_id=channel_id
            )
        
        channel.is_active = False
        channel.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True
