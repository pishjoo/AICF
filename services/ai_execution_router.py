"""
AI Execution Router

Runtime router for AI provider selection.
Workflows request operations (e.g., "generate_script") and the router
determines which provider to use based on the active AI profile.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Type
from datetime import datetime
import logging

from database.models import AIProfile, AIProvider, ProviderType, AIUsageRecord, ContentJob
from services.ai_provider_service import AIProviderService
from services.publishing import EncryptionService

logger = logging.getLogger(__name__)


class AIExecutionRouter:
    """
    Runtime router for AI provider selection.
    
    Purpose: Decouple workflow code from specific AI providers.
    
    Usage:
        # Workflow requests operation
        router = AIExecutionRouter(db, organization_id)
        
        # Get appropriate provider for operation
        text_provider = router.get_provider(ProviderType.TEXT)
        result = text_provider.generate(prompt)
        
        # Track usage
        router.record_usage(
            provider=text_provider,
            operation_type="text_generation",
            tokens_used=1000,
            cost_usd=0.002
        )
    """
    
    def __init__(
        self,
        db: Session,
        organization_id: int,
        profile_id: Optional[int] = None,
        encryption_service: Optional[EncryptionService] = None
    ):
        """
        Initialize the AI execution router.
        
        Args:
            db: Database session
            organization_id: Organization ID for tenant isolation
            profile_id: Optional specific profile to use (uses default if not provided)
            encryption_service: Optional encryption service
        """
        self.db = db
        self.organization_id = organization_id
        self.profile_id = profile_id
        self.encryption_service = encryption_service or EncryptionService()
        self._profile: Optional[AIProfile] = None
    
    def _get_profile(self) -> Optional[AIProfile]:
        """Get the current AI profile (cached)."""
        if self._profile is None:
            if self.profile_id:
                self._profile = self.db.query(AIProfile).filter(
                    AIProfile.id == self.profile_id,
                    AIProfile.organization_id == self.organization_id,
                    AIProfile.is_active == True
                ).first()
            else:
                # Use default profile
                self._profile = self.db.query(AIProfile).filter(
                    AIProfile.organization_id == self.organization_id,
                    AIProfile.is_default == True,
                    AIProfile.is_active == True
                ).first()
        
        return self._profile
    
    def get_provider(self, provider_type: ProviderType) -> Optional['ProviderWrapper']:
        """
        Get a provider wrapper for the specified type.
        
        Args:
            provider_type: Type of provider needed
            
        Returns:
            ProviderWrapper instance or None
        """
        profile = self._get_profile()
        
        if not profile:
            logger.warning(f"No AI profile found for organization {self.organization_id}")
            return None
        
        # Get provider ID based on type
        provider_id = None
        if provider_type == ProviderType.TEXT:
            provider_id = profile.text_provider_id
        elif provider_type == ProviderType.IMAGE:
            provider_id = profile.image_provider_id
        elif provider_type == ProviderType.VIDEO:
            provider_id = profile.video_provider_id
        elif provider_type == ProviderType.VOICE:
            provider_id = profile.voice_provider_id
        elif provider_type == ProviderType.RESEARCH:
            provider_id = profile.research_provider_id
        
        if not provider_id:
            logger.warning(f"No {provider_type.value} provider configured in profile '{profile.name}'")
            return None
        
        # Get provider
        provider = self.db.query(AIProvider).filter(
            AIProvider.id == provider_id,
            AIProvider.organization_id == self.organization_id,
            AIProvider.is_active == True
        ).first()
        
        if not provider:
            logger.warning(f"Provider {provider_id} not found or inactive")
            return None
        
        return ProviderWrapper(provider, self.encryption_service, self)
    
    def get_text_provider(self) -> Optional['ProviderWrapper']:
        """Get text generation provider."""
        return self.get_provider(ProviderType.TEXT)
    
    def get_image_provider(self) -> Optional['ProviderWrapper']:
        """Get image generation provider."""
        return self.get_provider(ProviderType.IMAGE)
    
    def get_video_provider(self) -> Optional['ProviderWrapper']:
        """Get video generation provider."""
        return self.get_provider(ProviderType.VIDEO)
    
    def get_voice_provider(self) -> Optional['ProviderWrapper']:
        """Get voice/speech provider."""
        return self.get_provider(ProviderType.VOICE)
    
    def get_research_provider(self) -> Optional['ProviderWrapper']:
        """Get research provider."""
        return self.get_provider(ProviderType.RESEARCH)
    
    def record_usage(
        self,
        provider: AIProvider,
        operation_type: str,
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        execution_time_ms: int = 0,
        model_name: Optional[str] = None,
        job_id: Optional[int] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> AIUsageRecord:
        """
        Record AI usage for tracking and cost analysis.
        
        Args:
            provider: AIProvider that was used
            operation_type: Type of operation performed
            tokens_used: Total tokens used
            input_tokens: Input tokens
            output_tokens: Output tokens
            cost_usd: Cost in USD
            execution_time_ms: Execution time in milliseconds
            model_name: Model name/version
            job_id: Related ContentJob ID
            request_metadata: Request context
            response_metadata: Response metadata
            
        Returns:
            Created AIUsageRecord
        """
        profile = self._get_profile()
        
        record = AIUsageRecord(
            organization_id=self.organization_id,
            profile_id=profile.id if profile else None,
            provider_id=provider.id,
            operation_type=operation_type,
            model_name=model_name,
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            execution_time_ms=execution_time_ms,
            job_id=job_id,
            request_metadata=request_metadata or {},
            response_metadata=response_metadata or {}
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        logger.debug(
            f"Recorded AI usage: {operation_type} - {tokens_used} tokens, ${cost_usd}"
        )
        
        return record
    
    def get_usage_summary(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage summary for the current profile.
        
        Args:
            days: Number of days to summarize
            
        Returns:
            Dictionary with usage statistics
        """
        from datetime import timedelta
        
        profile = self._get_profile()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AIUsageRecord).filter(
            AIUsageRecord.organization_id == self.organization_id,
            AIUsageRecord.created_at >= cutoff_date
        )
        
        if profile:
            query = query.filter(AIUsageRecord.profile_id == profile.id)
        
        records = query.all()
        
        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.tokens_used for r in records)
        
        # Group by provider
        by_provider = {}
        for record in records:
            provider_name = f"Provider-{record.provider_id}"
            if record.provider:
                provider_name = record.provider.provider_name
            
            if provider_name not in by_provider:
                by_provider[provider_name] = {
                    "cost_usd": 0,
                    "tokens_used": 0,
                    "operations": 0
                }
            
            by_provider[provider_name]["cost_usd"] += record.cost_usd
            by_provider[provider_name]["tokens_used"] += record.tokens_used
            by_provider[provider_name]["operations"] += 1
        
        # Group by operation type
        by_operation = {}
        for record in records:
            op_type = record.operation_type
            if op_type not in by_operation:
                by_operation[op_type] = {
                    "cost_usd": 0,
                    "tokens_used": 0,
                    "count": 0
                }
            
            by_operation[op_type]["cost_usd"] += record.cost_usd
            by_operation[op_type]["tokens_used"] += record.tokens_used
            by_operation[op_type]["count"] += 1
        
        return {
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "total_operations": len(records),
            "period_days": days,
            "by_provider": by_provider,
            "by_operation": by_operation
        }


class ProviderWrapper:
    """
    Wrapper for AIProvider that provides execution methods.
    
    This is a placeholder for actual provider implementations.
    In production, this would delegate to specific provider clients.
    """
    
    def __init__(
        self,
        provider: AIProvider,
        encryption_service: EncryptionService,
        router: AIExecutionRouter
    ):
        self.provider = provider
        self.encryption_service = encryption_service
        self.router = router
    
    @property
    def api_key(self) -> Optional[str]:
        """Get decrypted API key."""
        return self.encryption_service.decrypt_string(self.provider.encrypted_api_key)
    
    @property
    def endpoint(self) -> Optional[str]:
        """Get API endpoint."""
        return self.provider.api_endpoint
    
    @property
    def configuration(self) -> Dict[str, Any]:
        """Get provider configuration."""
        return self.provider.configuration or {}
    
    def execute(
        self,
        operation_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an operation with this provider.
        
        This is a placeholder. In production, this would call
        the actual provider API based on provider_type.
        
        Args:
            operation_type: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Operation result
        """
        logger.info(
            f"Executing {operation_type} with {self.provider.provider_name}"
        )
        
        # Placeholder implementation
        # In production, route to appropriate provider SDK
        return {
            "success": True,
            "provider": self.provider.provider_name,
            "operation": operation_type,
            "message": "Provider execution placeholder"
        }
    
    def record_execution(
        self,
        operation_type: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        execution_time_ms: int = 0,
        **kwargs
    ) -> AIUsageRecord:
        """
        Record execution metrics.
        
        Args:
            operation_type: Type of operation
            tokens_used: Tokens consumed
            cost_usd: Cost in USD
            execution_time_ms: Execution time
            **kwargs: Additional metadata
            
        Returns:
            Created AIUsageRecord
        """
        return self.router.record_usage(
            provider=self.provider,
            operation_type=operation_type,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            execution_time_ms=execution_time_ms,
            model_name=self.configuration.get("model"),
            request_metadata=kwargs
        )
