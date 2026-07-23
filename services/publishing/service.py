"""
Publishing Service - Main orchestrator for platform publishing.

Integrates with retry policies, rate limiting, and provides failure isolation
from the workflow engine.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Type
from datetime import datetime, timedelta
import logging
import asyncio

from database.models import PublishingState, Episode, Organization, PlatformWebhook
from services.publishing import (
    PublishingCredentialService,
    PublishingStateService,
    PlatformWebhookService,
    PlatformRateLimitService,
    AnalyticsJobService,
    EncryptionService
)
from services.publishing.platforms.base import (
    PlatformAdapter,
    PlatformAdapterError,
    RateLimitExceeded,
    AuthenticationError
)


logger = logging.getLogger(__name__)


class PublishingService:
    """
    Main publishing service orchestrating platform integrations.
    
    Features:
    - Encrypted credential management
    - OAuth2 flow support
    - Rate limiting per platform
    - Retry integration with existing retry abstraction
    - Failure isolation from workflow engine
    - Persistent state tracking
    - Webhook callback handling
    - Analytics collection scheduling
    - Organization data isolation
    """
    
    def __init__(
        self,
        db: Session,
        encryption_service: Optional[EncryptionService] = None,
        platform_adapters: Optional[Dict[str, Type[PlatformAdapter]]] = None
    ):
        self.db = db
        self.encryption_service = encryption_service or EncryptionService()
        self.platform_adapters = platform_adapters or {}
        
        # Initialize sub-services
        self.credential_service = PublishingCredentialService(db, self.encryption_service)
        self.state_service = PublishingStateService(db)
        self.webhook_service = PlatformWebhookService(db)
        self.rate_limit_service = PlatformRateLimitService(db)
        self.analytics_service = AnalyticsJobService(db)
        
        self.logger = logging.getLogger("publishing")
    
    def register_platform_adapter(
        self,
        platform: str,
        adapter_class: Type[PlatformAdapter]
    ) -> None:
        """Register a platform adapter class."""
        self.platform_adapters[platform] = adapter_class
        self.logger.info(f"Registered platform adapter: {platform}")
    
    def _get_platform_adapter(
        self,
        platform: str,
        credential_id: int,
        organization_id: int
    ) -> PlatformAdapter:
        """Get instantiated platform adapter."""
        if platform not in self.platform_adapters:
            raise ValueError(f"No adapter registered for platform: {platform}")
        
        adapter_class = self.platform_adapters[platform]
        
        return adapter_class(
            credential_id=credential_id,
            organization_id=organization_id,
            encryption_service=self.encryption_service,
            rate_limit_service=self.rate_limit_service
        )
    
    async def publish_episode(
        self,
        episode_id: int,
        organization_id: int,
        platform: str,
        credential_id: int,
        video_path: str,
        metadata: Dict[str, Any],
        use_retry: bool = True
    ) -> PublishingState:
        """
        Publish an episode to a platform.
        
        Args:
            episode_id: Episode to publish
            organization_id: Organization ID for tenant isolation
            platform: Target platform name
            credential_id: Credential to use for authentication
            video_path: Path to video file
            metadata: Video metadata (title, description, etc.)
            use_retry: Whether to use retry policy
            
        Returns:
            PublishingState record
            
        Raises:
            PlatformAdapterError: If publishing fails (isolated from workflow)
        """
        # Create publishing state
        state = self.state_service.create_state(
            organization_id=organization_id,
            episode_id=episode_id,
            platform=platform,
            credential_id=credential_id,
            state="pending",
            metadata={"video_path": video_path, **metadata}
        )
        
        try:
            # Get platform adapter
            adapter = self._get_platform_adapter(
                platform, credential_id, organization_id
            )
            
            # Authenticate
            await adapter.authenticate()
            
            # Upload video
            self.state_service.transition_state(
                state.id, organization_id, "uploading"
            )
            
            upload_result = await adapter.upload_video(
                video_path=video_path,
                title=metadata.get('title', ''),
                description=metadata.get('description', ''),
                metadata=metadata
            )
            
            # Update state with result
            self.state_service.transition_state(
                state.id,
                organization_id,
                "published",
                metadata_update={
                    "external_id": upload_result.get('id'),
                    "external_url": upload_result.get('url'),
                    "upload_response": upload_result
                }
            )
            
            state.external_id = upload_result.get('id')
            state.external_url = upload_result.get('url')
            state.published_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(state)
            
            self.logger.info(
                f"Published episode {episode_id} to {platform}: {state.external_url}"
            )
            
            return state
            
        except RateLimitExceeded as e:
            # Handle rate limiting with retry
            return await self._handle_rate_limit(
                state, organization_id, e, use_retry
            )
            
        except AuthenticationError as e:
            # Authentication errors are not retryable
            self.state_service.transition_state(
                state.id,
                organization_id,
                "failed",
                error_message=f"Authentication failed: {e}",
                metadata_update={"token_expired": e.token_expired}
            )
            self._isolate_failure(e, "publish", episode_id, organization_id)
            raise
            
        except PlatformAdapterError as e:
            # Platform-specific errors
            if use_retry and e.retryable:
                return await self._handle_retryable_failure(
                    state, organization_id, e, episode_id
                )
            else:
                self.state_service.transition_state(
                    state.id,
                    organization_id,
                    "failed",
                    error_message=str(e)
                )
                self._isolate_failure(e, "publish", episode_id, organization_id)
                raise
    
    async def _handle_rate_limit(
        self,
        state: PublishingState,
        organization_id: int,
        error: RateLimitExceeded,
        use_retry: bool
    ) -> PublishingState:
        """Handle rate limit exceeded with delayed retry."""
        wait_time = error.retry_after_seconds or 60.0
        
        self.state_service.transition_state(
            state.id,
            organization_id,
            "retrying",
            error_message=f"Rate limited, waiting {wait_time}s",
            metadata_update={"retry_after": wait_time}
        )
        
        if use_retry:
            # Schedule retry after wait time
            self.logger.info(
                f"Rate limited for {state.platform}, scheduling retry in {wait_time}s"
            )
            # In production, this would use a task queue like Celery
            # For now, just update state for background processor
            pass
        
        return state
    
    async def _handle_retryable_failure(
        self,
        state: PublishingState,
        organization_id: int,
        error: PlatformAdapterError,
        episode_id: int
    ) -> PublishingState:
        """Handle retryable failure using existing retry abstraction."""
        from app.rendering.retry_policy import get_retry_policy
        
        retry_policy = get_retry_policy()
        should_retry, delay, failure_type = retry_policy.record_failure(
            job_id=f"publish_{state.id}",
            error_message=str(error)
        )
        
        if should_retry:
            self.state_service.transition_state(
                state.id,
                organization_id,
                "retrying",
                error_message=str(error),
                metadata_update={
                    "retry_delay": delay,
                    "next_retry_at": (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
                }
            )
            
            self.logger.info(
                f"Publish {state.id} will retry in {delay}s (attempt {retry_policy.get_retry_state(f'publish_{state.id}').attempt_number})"
            )
        else:
            self.state_service.transition_state(
                state.id,
                organization_id,
                "failed",
                error_message=f"Max retries exceeded: {error}"
            )
            self._isolate_failure(error, "publish", episode_id, organization_id)
        
        return state
    
    def _isolate_failure(
        self,
        error: Exception,
        operation: str,
        episode_id: int,
        organization_id: int
    ) -> None:
        """
        Isolate platform failures from workflow engine.
        
        Logs the error but doesn't propagate it to crash the workflow.
        """
        self.logger.error(
            f"Platform failure during {operation} for episode {episode_id} "
            f"(org {organization_id}): {error}",
            exc_info=True
        )
        # Failure is isolated - workflow engine continues
    
    def schedule_analytics_collection(
        self,
        organization_id: int,
        platform: Optional[str] = None,
        episode_id: Optional[int] = None,
        scheduled_at: Optional[datetime] = None,
        priority: int = 0
    ) -> Any:
        """
        Schedule analytics collection job.
        
        Args:
            organization_id: Organization ID
            platform: Optional platform filter
            episode_id: Optional specific episode
            scheduled_at: When to run the job
            priority: Job priority
            
        Returns:
            Scheduled AnalyticsJob
        """
        return self.analytics_service.schedule_job(
            organization_id=organization_id,
            job_type="video_analytics",
            platform=platform,
            episode_id=episode_id,
            scheduled_at=scheduled_at,
            priority=priority,
            metadata={"auto_scheduled": False}
        )
    
    def collect_analytics_for_job(self, job_id: int, organization_id: int) -> None:
        """
        Execute analytics collection for a scheduled job.
        
        This would be called by a background worker.
        """
        job = self.analytics_service.start_job(job_id, organization_id)
        
        if not job:
            self.logger.error(f"Analytics job {job_id} not found")
            return
        
        try:
            # Get states for this episode or platform
            if job.episode_id:
                states = self.state_service.get_states_for_episode(
                    job.episode_id, organization_id
                )
            else:
                # Get all published states for platform
                states = self.db.query(PublishingState).filter(
                    PublishingState.organization_id == organization_id,
                    PublishingState.state == "published"
                )
                if job.platform:
                    states = states.filter(PublishingState.platform == job.platform)
                states = states.all()
            
            results = []
            
            for state in states:
                if state.external_id:
                    adapter = self._get_platform_adapter(
                        state.platform, state.credential_id, organization_id
                    )
                    
                    try:
                        analytics = asyncio.run(adapter.get_analytics(
                            state.external_id,
                            datetime.utcnow() - timedelta(days=30),
                            datetime.utcnow()
                        ))
                        results.append({
                            "episode_id": state.episode_id,
                            "platform": state.platform,
                            "external_id": state.external_id,
                            "analytics": analytics
                        })
                    except Exception as e:
                        self.logger.error(
                            f"Failed to collect analytics for {state.external_id}: {e}"
                        )
            
            self.analytics_service.complete_job(
                job_id, organization_id, result={"collected": len(results)}
            )
            
        except Exception as e:
            self.analytics_service.complete_job(
                job_id, organization_id, error_message=str(e)
            )
            self._isolate_failure(e, "analytics_collection", job.episode_id or 0, organization_id)
    
    def process_webhook_callback(
        self,
        organization_id: int,
        platform: str,
        payload: Dict[str, Any],
        signature: str,
        webhook_id: Optional[int] = None
    ) -> bool:
        """
        Process incoming webhook from platform.
        
        Args:
            organization_id: Organization ID
            platform: Platform name
            payload: Webhook payload
            signature: Request signature for verification
            webhook_id: Optional specific webhook ID
            
        Returns:
            True if processed successfully
        """
        # Find matching webhook
        query = self.db.query(PlatformWebhook).filter(
            PlatformWebhook.organization_id == organization_id,
            PlatformWebhook.platform == platform,
            PlatformWebhook.is_active == True
        )
        
        if webhook_id:
            query = query.filter(PlatformWebhook.id == webhook_id)
        
        webhook = query.first()
        
        if not webhook:
            self.logger.warning(f"No active webhook found for {platform}")
            return False
        
        # Verify signature
        if not self.webhook_service.verify_webhook_signature(
            webhook.id, organization_id, str(payload).encode(), signature
        ):
            self.logger.warning(f"Invalid webhook signature for {platform}")
            return False
        
        # Process event based on type
        event_type = payload.get('event', payload.get('type'))
        
        try:
            if event_type in ['video.published', 'upload.finalized']:
                self._handle_publish_complete(webhook, payload)
            elif event_type in ['video.failed', 'upload.failed']:
                self._handle_publish_failure(webhook, payload)
            elif event_type in ['analytics.updated']:
                self._handle_analytics_update(webhook, payload)
            else:
                self.logger.info(f"Unhandled webhook event: {event_type}")
            
            self.webhook_service.record_webhook_delivery(
                webhook.id, organization_id, success=True
            )
            return True
            
        except Exception as e:
            self.webhook_service.record_webhook_delivery(
                webhook.id, organization_id, success=False, error_message=str(e)
            )
            self._isolate_failure(e, "webhook_processing", 0, organization_id)
            return False
    
    def _handle_publish_complete(
        self,
        webhook: PlatformWebhook,
        payload: Dict[str, Any]
    ) -> None:
        """Handle publish completion webhook."""
        external_id = payload.get('video_id', payload.get('id'))
        
        if external_id:
            state = self.db.query(PublishingState).filter(
                PublishingState.external_id == external_id,
                PublishingState.platform == webhook.platform
            ).first()
            
            if state:
                self.state_service.transition_state(
                    state.id,
                    state.organization_id,
                    "published",
                    metadata_update={"webhook_confirmed": True}
                )
                self.logger.info(f"Confirmed publish for {external_id}")
    
    def _handle_publish_failure(
        self,
        webhook: PlatformWebhook,
        payload: Dict[str, Any]
    ) -> None:
        """Handle publish failure webhook."""
        external_id = payload.get('video_id', payload.get('id'))
        error_message = payload.get('error', 'Unknown error')
        
        if external_id:
            state = self.db.query(PublishingState).filter(
                PublishingState.external_id == external_id,
                PublishingState.platform == webhook.platform
            ).first()
            
            if state:
                self.state_service.transition_state(
                    state.id,
                    state.organization_id,
                    "failed",
                    error_message=f"Platform reported: {error_message}"
                )
                self.logger.warning(f"Publish failed for {external_id}: {error_message}")
    
    def _handle_analytics_update(
        self,
        webhook: PlatformWebhook,
        payload: Dict[str, Any]
    ) -> None:
        """Handle analytics update webhook by scheduling collection job."""
        # Schedule immediate analytics collection
        self.analytics_service.schedule_job(
            organization_id=webhook.organization_id,
            job_type="video_analytics",
            platform=webhook.platform,
            priority=1,  # Higher priority for webhook-triggered
            metadata={"triggered_by": "webhook", "payload": payload}
        )
    
    def get_publishing_status(
        self,
        episode_id: int,
        organization_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get publishing status across all platforms for an episode.
        
        Args:
            episode_id: Episode ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            List of status dictionaries per platform
        """
        states = self.state_service.get_states_for_episode(
            episode_id, organization_id
        )
        
        return [
            {
                "platform": state.platform,
                "state": state.state,
                "external_id": state.external_id,
                "external_url": state.external_url,
                "last_error": state.last_error,
                "retry_count": state.retry_count,
                "published_at": state.published_at.isoformat() if state.published_at else None,
                "created_at": state.created_at.isoformat()
            }
            for state in states
        ]
