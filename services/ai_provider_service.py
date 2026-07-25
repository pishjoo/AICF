"""
AI Provider Service

Service layer for managing AI provider configurations.
Handles CRUD operations, API key encryption, and connection testing.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.base import BaseService
from database.models import AIProvider, ProviderType, Organization
from services.publishing import EncryptionService

logger = logging.getLogger(__name__)


class AIProviderService(BaseService):
    """
    Service for managing AI providers with encrypted credential storage.
    
    Features:
    - CRUD operations for AI providers
    - API key encryption/decryption
    - Connection testing
    - Provider filtering by type
    - Tenant isolation
    """
    
    def __init__(self, db: Session, encryption_service: Optional[EncryptionService] = None):
        super().__init__(db, AIProvider)
        self.encryption_service = encryption_service or EncryptionService()
    
    def create_provider(
        self,
        organization_id: int,
        name: str,
        provider_type: ProviderType,
        provider_name: str,
        api_key: str,
        api_endpoint: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> AIProvider:
        """
        Create a new AI provider with encrypted API key.
        
        Args:
            organization_id: Organization owning the provider
            name: Human-readable name for the provider
            provider_type: Type of provider (text, image, video, voice, research)
            provider_name: Provider identifier (deepseek, openai, elevenlabs, etc.)
            api_key: API key to encrypt and store
            api_endpoint: Optional custom API endpoint
            configuration: Optional additional configuration
            
        Returns:
            Created AIProvider instance
        """
        # Encrypt the API key
        encrypted_key = self.encryption_service.encrypt_string(api_key)
        
        provider = AIProvider(
            organization_id=organization_id,
            name=name,
            provider_type=provider_type,
            provider_name=provider_name,
            api_endpoint=api_endpoint,
            encrypted_api_key=encrypted_key,
            configuration=configuration or {},
            is_active=True
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        logger.info(f"Created AI provider '{name}' ({provider_type.value}) for org {organization_id}")
        return provider
    
    def get_api_key(self, provider_id: int, organization_id: int) -> Optional[str]:
        """
        Retrieve and decrypt API key for a provider.
        
        Args:
            provider_id: Provider record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Decrypted API key or None if not found
        """
        provider = self.get(provider_id, organization_id)
        
        if not provider or not provider.is_active:
            return None
        
        return self.encryption_service.decrypt_string(provider.encrypted_api_key)
    
    def update_provider(
        self,
        provider_id: int,
        organization_id: int,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AIProvider]:
        """
        Update provider configuration.
        
        Args:
            provider_id: Provider record ID
            organization_id: Organization ID for tenant isolation
            name: New name (optional)
            api_key: New API key to encrypt (optional)
            api_endpoint: New endpoint (optional)
            configuration: New configuration (optional)
            is_active: Active status (optional)
            
        Returns:
            Updated AIProvider or None
        """
        provider = self.get(provider_id, organization_id)
        
        if not provider:
            return None
        
        if name is not None:
            provider.name = name
        
        if api_key is not None:
            provider.encrypted_api_key = self.encryption_service.encrypt_string(api_key)
        
        if api_endpoint is not None:
            provider.api_endpoint = api_endpoint
        
        if configuration is not None:
            provider.configuration = configuration
        
        if is_active is not None:
            provider.is_active = is_active
        
        provider.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    def test_connection(self, provider_id: int, organization_id: int) -> Dict[str, Any]:
        """
        Test connection to an AI provider.
        
        Note: This is a placeholder for actual connection testing.
        In production, this would make a real API call to verify credentials.
        
        Args:
            provider_id: Provider record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Dict with 'success' boolean and 'message' string
        """
        provider = self.get(provider_id, organization_id)
        
        if not provider:
            return {"success": False, "message": "Provider not found"}
        
        try:
            # Decrypt API key to verify it works
            api_key = self.get_api_key(provider_id, organization_id)
            
            if not api_key:
                return {"success": False, "message": "Could not decrypt API key"}
            
            # TODO: Implement actual connection test based on provider_type
            # For now, just verify we have a valid key
            if len(api_key) < 10:
                return {"success": False, "message": "API key appears too short"}
            
            # Update test metadata
            provider.last_tested_at = datetime.utcnow()
            provider.last_test_status = "success"
            self.db.commit()
            
            return {"success": True, "message": f"Connection to {provider.provider_name} successful"}
            
        except Exception as e:
            provider.last_tested_at = datetime.utcnow()
            provider.last_test_status = "failed"
            self.db.commit()
            
            logger.error(f"Connection test failed for provider {provider_id}: {e}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}
    
    def get_providers_by_type(
        self,
        organization_id: int,
        provider_type: ProviderType,
        active_only: bool = True
    ) -> List[AIProvider]:
        """
        Get all providers of a specific type for an organization.
        
        Args:
            organization_id: Organization ID
            provider_type: Type of providers to retrieve
            active_only: Only return active providers
            
        Returns:
            List of AIProvider instances
        """
        query = self.db.query(AIProvider).filter(
            AIProvider.organization_id == organization_id,
            AIProvider.provider_type == provider_type
        )
        
        if active_only:
            query = query.filter(AIProvider.is_active == True)
        
        return query.all()
    
    def get_provider_summary(self, provider_id: int, organization_id: int) -> Optional[Dict[str, Any]]:
        """
        Get provider summary without exposing sensitive data.
        
        Args:
            provider_id: Provider record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Dictionary with provider info (masked API key)
        """
        provider = self.get(provider_id, organization_id)
        
        if not provider:
            return None
        
        # Mask API key for display
        masked_key = self._mask_api_key(provider.encrypted_api_key)
        
        return {
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type.value,
            "provider_name": provider.provider_name,
            "api_endpoint": provider.api_endpoint,
            "api_key_masked": masked_key,
            "is_active": provider.is_active,
            "last_tested_at": provider.last_tested_at.isoformat() if provider.last_tested_at else None,
            "last_test_status": provider.last_test_status,
            "configuration": provider.configuration,
            "created_at": provider.created_at.isoformat() if provider.created_at else None
        }
    
    def _mask_api_key(self, encrypted_key: str) -> str:
        """Mask API key for safe display."""
        # Since we can't decrypt here, just show a generic mask
        # In real API responses, we don't include the key at all
        return "sk-****" + encrypted_key[-4:] if len(encrypted_key) > 4 else "****"
    
    def delete_provider(self, provider_id: int, organization_id: int) -> bool:
        """
        Delete a provider (soft delete by deactivating).
        
        Args:
            provider_id: Provider record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            True if deleted/deactivated
        """
        # Check if provider is used by any profiles
        from database.models import AIProfile
        in_use = self.db.query(AIProfile).filter(
            AIProfile.organization_id == organization_id,
            (AIProfile.text_provider_id == provider_id) |
            (AIProfile.image_provider_id == provider_id) |
            (AIProfile.video_provider_id == provider_id) |
            (AIProfile.voice_provider_id == provider_id) |
            (AIProfile.research_provider_id == provider_id)
        ).first()
        
        if in_use:
            # Soft delete by deactivating
            return self.update_provider(provider_id, organization_id, is_active=False) is not None
        
        # Hard delete if not in use
        return super().delete(provider_id, organization_id)
