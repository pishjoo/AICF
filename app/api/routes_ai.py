"""
AI Provider API Routes

REST API endpoints for AI provider and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from database.connection import get_db
from database.models import ProviderType
from services.ai_provider_service import AIProviderService
from services.ai_profile_service import AIProfileService
from services.ai_execution_router import AIExecutionRouter
from services.publishing import EncryptionService
from app.api.schemas import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Providers"])


# =============================================================================
# Schemas
# =============================================================================

class AIProviderCreate(BaseModel):
    name: str
    provider_type: ProviderType
    provider_name: str
    api_key: str
    api_endpoint: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class AIProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AIProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    provider_name: str
    api_endpoint: Optional[str]
    is_active: bool
    last_tested_at: Optional[str]
    last_test_status: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class AIProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    text_provider_id: Optional[int] = None
    image_provider_id: Optional[int] = None
    video_provider_id: Optional[int] = None
    voice_provider_id: Optional[int] = None
    research_provider_id: Optional[int] = None
    configuration: Optional[Dict[str, Any]] = None
    is_default: bool = False


class AIProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    text_provider_id: Optional[int] = None
    image_provider_id: Optional[int] = None
    video_provider_id: Optional[int] = None
    voice_provider_id: Optional[int] = None
    research_provider_id: Optional[int] = None
    configuration: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class AIProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    is_active: bool
    text_provider_id: Optional[int]
    image_provider_id: Optional[int]
    video_provider_id: Optional[int]
    voice_provider_id: Optional[int]
    research_provider_id: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class UsageSummaryResponse(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_operations: int
    period_days: int
    by_provider: Dict[str, Any]
    by_operation: Dict[str, Any]


# =============================================================================
# Helper Functions
# =============================================================================

def get_organization_id(x_organization_id: Optional[str] = Header(None)) -> int:
    """Extract organization ID from header or use default."""
    if x_organization_id:
        return int(x_organization_id)
    # Default to 1 for single-user mode
    return 1


def get_encryption_service() -> EncryptionService:
    """Get encryption service instance."""
    return EncryptionService()


# =============================================================================
# AI Provider Endpoints
# =============================================================================

@router.get("/providers", response_model=List[AIProviderResponse])
def list_providers(
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id),
    provider_type: Optional[ProviderType] = None,
    active_only: bool = True
):
    """List all AI providers for the organization."""
    service = AIProviderService(db)
    
    if provider_type:
        providers = service.get_providers_by_type(organization_id, provider_type, active_only)
    else:
        # Get all providers
        providers = service.list(organization_id=organization_id)
        if active_only:
            providers = [p for p in providers if p.is_active]
    
    return providers


@router.post("/providers", response_model=AIProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(
    provider_data: AIProviderCreate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Create a new AI provider with encrypted API key."""
    service = AIProviderService(db)
    
    try:
        provider = service.create_provider(
            organization_id=organization_id,
            name=provider_data.name,
            provider_type=provider_data.provider_type,
            provider_name=provider_data.provider_name,
            api_key=provider_data.api_key,
            api_endpoint=provider_data.api_endpoint,
            configuration=provider_data.configuration
        )
        return provider
    except Exception as e:
        logger.error(f"Failed to create provider: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers/{provider_id}", response_model=AIProviderResponse)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Get a specific AI provider."""
    service = AIProviderService(db)
    provider = service.get(provider_id, organization_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return provider


@router.put("/providers/{provider_id}", response_model=AIProviderResponse)
def update_provider(
    provider_id: int,
    provider_update: AIProviderUpdate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Update an AI provider configuration."""
    service = AIProviderService(db)
    
    update_data = provider_update.model_dump(exclude_unset=True)
    provider = service.update_provider(provider_id, organization_id, **update_data)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Delete or deactivate an AI provider."""
    service = AIProviderService(db)
    
    if not service.delete_provider(provider_id, organization_id):
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/providers/{provider_id}/test", response_model=TestConnectionResponse)
def test_provider_connection(
    provider_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Test connection to an AI provider."""
    service = AIProviderService(db)
    result = service.test_connection(provider_id, organization_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


# =============================================================================
# AI Profile Endpoints
# =============================================================================

@router.get("/profiles", response_model=List[AIProfileResponse])
def list_profiles(
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id),
    active_only: bool = False
):
    """List all AI profiles for the organization."""
    service = AIProfileService(db)
    return service.list_profiles(organization_id, active_only=active_only)


@router.post("/profiles", response_model=AIProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: AIProfileCreate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Create a new AI profile."""
    service = AIProfileService(db)
    
    try:
        profile = service.create_profile(
            organization_id=organization_id,
            name=profile_data.name,
            description=profile_data.description,
            text_provider_id=profile_data.text_provider_id,
            image_provider_id=profile_data.image_provider_id,
            video_provider_id=profile_data.video_provider_id,
            voice_provider_id=profile_data.voice_provider_id,
            research_provider_id=profile_data.research_provider_id,
            configuration=profile_data.configuration,
            is_default=profile_data.is_default
        )
        return profile
    except Exception as e:
        logger.error(f"Failed to create profile: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profiles/{profile_id}", response_model=AIProfileResponse)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Get a specific AI profile."""
    service = AIProfileService(db)
    profile = service.get(profile_id, organization_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.get("/profiles/{profile_id}/details")
def get_profile_details(
    profile_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Get profile details with linked provider information."""
    service = AIProfileService(db)
    details = service.get_profile_with_providers(profile_id, organization_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return details


@router.put("/profiles/{profile_id}", response_model=AIProfileResponse)
def update_profile(
    profile_id: int,
    profile_update: AIProfileUpdate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Update an AI profile."""
    service = AIProfileService(db)
    
    update_data = profile_update.model_dump(exclude_unset=True)
    profile = service.update_profile(profile_id, organization_id, **update_data)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.post("/profiles/{profile_id}/activate", response_model=AIProfileResponse)
def activate_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Activate a profile (set as default)."""
    service = AIProfileService(db)
    profile = service.activate_profile(profile_id, organization_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.post("/profiles/{profile_id}/duplicate", response_model=AIProfileResponse, status_code=status.HTTP_201_CREATED)
def duplicate_profile(
    profile_id: int,
    new_name: str,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Duplicate an existing profile."""
    service = AIProfileService(db)
    profile = service.duplicate_profile(profile_id, organization_id, new_name)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Delete or deactivate an AI profile."""
    service = AIProfileService(db)
    
    if not service.delete_profile(profile_id, organization_id):
        raise HTTPException(status_code=404, detail="Profile not found or cannot be deleted")


# =============================================================================
# AI Usage Endpoints
# =============================================================================

@router.get("/usage/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    days: int = 30,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_organization_id)
):
    """Get AI usage summary for the current profile."""
    router_service = AIExecutionRouter(db, organization_id)
    summary = router_service.get_usage_summary(days)
    return summary
