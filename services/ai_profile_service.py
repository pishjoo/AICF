"""
AI Profile Service

Service layer for managing AI provider profiles.
Allows grouping multiple AI providers into reusable configurations.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.base import BaseService
from database.models import AIProfile, AIProvider, ProviderType

logger = logging.getLogger(__name__)


class AIProfileService(BaseService):
    """
    Service for managing AI profiles.
    
    Features:
    - Create/update/delete AI profiles
    - Assign providers to profile slots
    - Activate/deactivate profiles
    - Duplicate profiles
    - Get default profile
    - Tenant isolation
    """
    
    def __init__(self, db: Session):
        super().__init__(db, AIProfile)
    
    def create_profile(
        self,
        organization_id: int,
        name: str,
        description: Optional[str] = None,
        text_provider_id: Optional[int] = None,
        image_provider_id: Optional[int] = None,
        video_provider_id: Optional[int] = None,
        voice_provider_id: Optional[int] = None,
        research_provider_id: Optional[int] = None,
        configuration: Optional[Dict[str, Any]] = None,
        is_default: bool = False
    ) -> AIProfile:
        """
        Create a new AI profile.
        
        Args:
            organization_id: Organization owning the profile
            name: Profile name
            description: Profile description
            text_provider_id: ID of text provider
            image_provider_id: ID of image provider
            video_provider_id: ID of video provider
            voice_provider_id: ID of voice provider
            research_provider_id: ID of research provider
            configuration: Additional configuration
            is_default: Whether this is the default profile
            
        Returns:
            Created AIProfile instance
        """
        # If setting as default, unset other defaults
        if is_default:
            self._unset_default_profile(organization_id)
        
        profile = AIProfile(
            organization_id=organization_id,
            name=name,
            description=description,
            text_provider_id=text_provider_id,
            image_provider_id=image_provider_id,
            video_provider_id=video_provider_id,
            voice_provider_id=voice_provider_id,
            research_provider_id=research_provider_id,
            configuration=configuration or {},
            is_default=is_default,
            is_active=True
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Created AI profile '{name}' for org {organization_id}")
        return profile
    
    def update_profile(
        self,
        profile_id: int,
        organization_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        text_provider_id: Optional[int] = None,
        image_provider_id: Optional[int] = None,
        video_provider_id: Optional[int] = None,
        voice_provider_id: Optional[int] = None,
        research_provider_id: Optional[int] = None,
        configuration: Optional[Dict[str, Any]] = None,
        is_default: Optional[bool] = None
    ) -> Optional[AIProfile]:
        """
        Update an AI profile.
        
        Args:
            profile_id: Profile record ID
            organization_id: Organization ID for tenant isolation
            name: New name
            description: New description
            text_provider_id: New text provider ID
            image_provider_id: New image provider ID
            video_provider_id: New video provider ID
            voice_provider_id: New voice provider ID
            research_provider_id: New research provider ID
            configuration: New configuration
            is_default: New default status
            
        Returns:
            Updated AIProfile or None
        """
        profile = self.get(profile_id, organization_id)
        
        if not profile:
            return None
        
        if name is not None:
            profile.name = name
        
        if description is not None:
            profile.description = description
        
        if text_provider_id is not None:
            profile.text_provider_id = text_provider_id
        
        if image_provider_id is not None:
            profile.image_provider_id = image_provider_id
        
        if video_provider_id is not None:
            profile.video_provider_id = video_provider_id
        
        if voice_provider_id is not None:
            profile.voice_provider_id = voice_provider_id
        
        if research_provider_id is not None:
            profile.research_provider_id = research_provider_id
        
        if configuration is not None:
            profile.configuration = configuration
        
        if is_default is not None and is_default:
            self._unset_default_profile(organization_id)
            profile.is_default = True
        
        profile.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def activate_profile(self, profile_id: int, organization_id: int) -> Optional[AIProfile]:
        """
        Activate a profile (set as default).
        
        Args:
            profile_id: Profile record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Updated AIProfile or None
        """
        return self.update_profile(profile_id, organization_id, is_default=True)
    
    def duplicate_profile(
        self,
        profile_id: int,
        organization_id: int,
        new_name: str
    ) -> Optional[AIProfile]:
        """
        Duplicate an existing profile.
        
        Args:
            profile_id: Source profile ID
            organization_id: Organization ID for tenant isolation
            new_name: Name for the duplicated profile
            
        Returns:
            New AIProfile instance or None
        """
        source = self.get(profile_id, organization_id)
        
        if not source:
            return None
        
        return self.create_profile(
            organization_id=organization_id,
            name=new_name,
            description=f"Copy of {source.name}",
            text_provider_id=source.text_provider_id,
            image_provider_id=source.image_provider_id,
            video_provider_id=source.video_provider_id,
            voice_provider_id=source.voice_provider_id,
            research_provider_id=source.research_provider_id,
            configuration=source.configuration.copy() if source.configuration else None,
            is_default=False
        )
    
    def get_default_profile(self, organization_id: int) -> Optional[AIProfile]:
        """
        Get the default AI profile for an organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Default AIProfile or None if no default set
        """
        return self.db.query(AIProfile).filter(
            AIProfile.organization_id == organization_id,
            AIProfile.is_default == True,
            AIProfile.is_active == True
        ).first()
    
    def get_profile_with_providers(
        self,
        profile_id: int,
        organization_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get profile with linked provider details.
        
        Args:
            profile_id: Profile record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Dictionary with profile and provider info
        """
        profile = self.get(profile_id, organization_id)
        
        if not profile:
            return None
        
        result = {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "is_default": profile.is_default,
            "is_active": profile.is_active,
            "configuration": profile.configuration,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "providers": {}
        }
        
        # Load provider summaries
        if profile.text_provider:
            result["providers"]["text"] = {
                "id": profile.text_provider.id,
                "name": profile.text_provider.name,
                "provider_name": profile.text_provider.provider_name
            }
        
        if profile.image_provider:
            result["providers"]["image"] = {
                "id": profile.image_provider.id,
                "name": profile.image_provider.name,
                "provider_name": profile.image_provider.provider_name
            }
        
        if profile.video_provider:
            result["providers"]["video"] = {
                "id": profile.video_provider.id,
                "name": profile.video_provider.name,
                "provider_name": profile.video_provider.provider_name
            }
        
        if profile.voice_provider:
            result["providers"]["voice"] = {
                "id": profile.voice_provider.id,
                "name": profile.voice_provider.name,
                "provider_name": profile.voice_provider.provider_name
            }
        
        if profile.research_provider:
            result["providers"]["research"] = {
                "id": profile.research_provider.id,
                "name": profile.research_provider.name,
                "provider_name": profile.research_provider.provider_name
            }
        
        return result
    
    def list_profiles(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[AIProfile]:
        """
        List profiles for an organization.
        
        Args:
            organization_id: Organization ID
            skip: Pagination offset
            limit: Maximum results
            active_only: Only return active profiles
            
        Returns:
            List of AIProfile instances
        """
        query = self.db.query(AIProfile).filter(
            AIProfile.organization_id == organization_id
        )
        
        if active_only:
            query = query.filter(AIProfile.is_active == True)
        
        return query.order_by(AIProfile.is_default.desc(), AIProfile.created_at.desc()).offset(skip).limit(limit).all()
    
    def _unset_default_profile(self, organization_id: int) -> None:
        """Unset all default profiles for an organization."""
        self.db.query(AIProfile).filter(
            AIProfile.organization_id == organization_id,
            AIProfile.is_default == True
        ).update({"is_default": False})
        self.db.commit()
    
    def delete_profile(self, profile_id: int, organization_id: int) -> bool:
        """
        Delete a profile (soft delete by deactivating if it's in use).
        
        Args:
            profile_id: Profile record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            True if deleted/deactivated
        """
        profile = self.get(profile_id, organization_id)
        
        if not profile:
            return False
        
        # Check if this is the default profile
        if profile.is_default:
            # Don't allow deleting default profile without reassigning
            return False
        
        # Soft delete by deactivating
        profile.is_active = False
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
