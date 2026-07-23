"""
Publishing Service - Platform Integration Layer

Handles publishing content to external platforms (YouTube, Vimeo, etc.)
with support for OAuth2, rate limiting, retries, and webhook callbacks.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Type
from datetime import datetime, timedelta
import logging

from services.base import BaseService
from database.models import (
    PublishingCredential, PublishingState, PlatformWebhook,
    PlatformRateLimit, AnalyticsJob, Organization
)


logger = logging.getLogger(__name__)


class PublishingCredentialService(BaseService):
    """
    Service for managing publishing credentials with encrypted storage.
    
    Handles secure storage and retrieval of OAuth tokens, API keys,
    and other platform authentication credentials.
    """
    
    def __init__(self, db: Session, encryption_service: 'EncryptionService'):
        super().__init__(db, PublishingCredential)
        self.encryption_service = encryption_service
    
    def store_credential(
        self,
        organization_id: int,
        platform: str,
        credential_type: str,
        credential_data: Dict[str, Any],
        account_name: Optional[str] = None
    ) -> PublishingCredential:
        """
        Store encrypted credentials for a platform.
        
        Args:
            organization_id: Organization owning the credential
            platform: Platform identifier (e.g., 'youtube', 'vimeo')
            credential_type: Type of credential (e.g., 'oauth2', 'api_key')
            credential_data: Credential data to encrypt and store
            account_name: Optional account name/identifier
            
        Returns:
            Created PublishingCredential record
        """
        # Encrypt sensitive fields
        encrypted_data = self.encryption_service.encrypt_dict(credential_data)
        
        credential = PublishingCredential(
            organization_id=organization_id,
            platform=platform,
            credential_type=credential_type,
            account_name=account_name,
            encrypted_data=encrypted_data,
            is_active=True
        )
        
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        logger.info(f"Stored credential for {platform} (org={organization_id})")
        return credential
    
    def get_credential(
        self,
        credential_id: int,
        organization_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt credentials.
        
        Args:
            credential_id: Credential record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Decrypted credential data or None
        """
        credential = self.get(credential_id, organization_id)
        
        if not credential or not credential.is_active:
            return None
        
        # Decrypt the data
        return self.encryption_service.decrypt_dict(credential.encrypted_data)
    
    def get_credentials_for_platform(
        self,
        organization_id: int,
        platform: str
    ) -> List[Dict[str, Any]]:
        """
        Get all active credentials for a platform.
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            
        Returns:
            List of decrypted credential dictionaries
        """
        credentials = self.db.query(PublishingCredential).filter(
            PublishingCredential.organization_id == organization_id,
            PublishingCredential.platform == platform,
            PublishingCredential.is_active == True
        ).all()
        
        return [
            {
                'id': cred.id,
                'account_name': cred.account_name,
                'data': self.encryption_service.decrypt_dict(cred.encrypted_data)
            }
            for cred in credentials
        ]
    
    def update_credential(
        self,
        credential_id: int,
        organization_id: int,
        credential_data: Dict[str, Any]
    ) -> bool:
        """
        Update credential data.
        
        Args:
            credential_id: Credential record ID
            organization_id: Organization ID for tenant isolation
            credential_data: New credential data to encrypt
            
        Returns:
            True if updated, False if not found
        """
        credential = self.get(credential_id, organization_id)
        
        if not credential:
            return False
        
        credential.encrypted_data = self.encryption_service.encrypt_dict(credential_data)
        credential.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def revoke_credential(self, credential_id: int, organization_id: int) -> bool:
        """
        Soft-delete a credential by marking it inactive.
        
        Args:
            credential_id: Credential record ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            True if revoked, False if not found
        """
        credential = self.get(credential_id, organization_id)
        
        if not credential:
            return False
        
        credential.is_active = False
        credential.revoked_at = datetime.utcnow()
        
        self.db.commit()
        return True


class PublishingStateService(BaseService):
    """
    Service for managing persistent publishing states.
    
    Tracks the state of publishing operations across platforms,
    supporting recovery from failures and state machine transitions.
    """
    
    def __init__(self, db: Session):
        super().__init__(db, PublishingState)
    
    def create_state(
        self,
        organization_id: int,
        episode_id: int,
        platform: str,
        credential_id: int,
        state: str = "pending",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PublishingState:
        """
        Create a new publishing state record.
        
        Args:
            organization_id: Organization ID
            episode_id: Episode being published
            platform: Target platform
            credential_id: Credential used for publishing
            state: Initial state
            metadata: Optional state metadata
            
        Returns:
            Created PublishingState record
        """
        publishing_state = PublishingState(
            organization_id=organization_id,
            episode_id=episode_id,
            platform=platform,
            credential_id=credential_id,
            state=state,
            metadata=metadata or {},
            retry_count=0
        )
        
        self.db.add(publishing_state)
        self.db.commit()
        self.db.refresh(publishing_state)
        
        logger.info(f"Created publishing state for episode {episode_id} on {platform}")
        return publishing_state
    
    def transition_state(
        self,
        state_id: int,
        organization_id: int,
        new_state: str,
        error_message: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> Optional[PublishingState]:
        """
        Transition a publishing state to a new state.
        
        Args:
            state_id: State record ID
            organization_id: Organization ID for tenant isolation
            new_state: New state value
            error_message: Optional error message if transitioning to failed state
            metadata_update: Optional metadata updates
            
        Returns:
            Updated PublishingState or None
        """
        state = self.get(state_id, organization_id)
        
        if not state:
            return None
        
        previous_state = state.state
        state.state = new_state
        state.previous_state = previous_state
        state.transitioned_at = datetime.utcnow()
        
        if error_message:
            state.last_error = error_message
        
        if metadata_update:
            current_metadata = state.state_metadata or {}
            current_metadata.update(metadata_update)
            state.state_metadata = current_metadata
        
        # Increment retry count if this is a retry
        if new_state == "retrying":
            state.retry_count = (state.retry_count or 0) + 1
        
        self.db.commit()
        self.db.refresh(state)
        
        logger.info(
            f"Transitioned state {state_id}: {previous_state} -> {new_state}"
        )
        
        return state
    
    def get_states_for_episode(
        self,
        episode_id: int,
        organization_id: int
    ) -> List[PublishingState]:
        """
        Get all publishing states for an episode.
        
        Args:
            episode_id: Episode ID
            organization_id: Organization ID for tenant isolation
            
        Returns:
            List of PublishingState records
        """
        return self.db.query(PublishingState).filter(
            PublishingState.episode_id == episode_id,
            PublishingState.organization_id == organization_id
        ).order_by(PublishingState.created_at.desc()).all()
    
    def get_pending_states(self, organization_id: int) -> List[PublishingState]:
        """Get all pending publishing states."""
        return self.db.query(PublishingState).filter(
            PublishingState.organization_id == organization_id,
            PublishingState.state.in_(["pending", "retrying"])
        ).all()
    
    def get_failed_states(
        self,
        organization_id: int,
        max_retries: int = 3
    ) -> List[PublishingState]:
        """Get failed states that haven't exceeded max retries."""
        return self.db.query(PublishingState).filter(
            PublishingState.organization_id == organization_id,
            PublishingState.state == "failed",
            (PublishingState.retry_count < max_retries) | (PublishingState.retry_count == None)
        ).all()


class PlatformWebhookService(BaseService):
    """
    Service for managing platform webhook configurations.
    
    Handles registration, verification, and processing of webhooks
    from external platforms for publish callbacks.
    """
    
    def __init__(self, db: Session):
        super().__init__(db, PlatformWebhook)
    
    def register_webhook(
        self,
        organization_id: int,
        platform: str,
        endpoint_url: str,
        secret: str,
        events: List[str],
        credential_id: Optional[int] = None
    ) -> PlatformWebhook:
        """
        Register a new webhook endpoint.
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            endpoint_url: URL to receive webhook callbacks
            secret: Webhook signing secret
            events: List of event types to subscribe to
            credential_id: Optional associated credential
            
        Returns:
            Created PlatformWebhook record
        """
        webhook = PlatformWebhook(
            organization_id=organization_id,
            platform=platform,
            endpoint_url=endpoint_url,
            secret_hash=self._hash_secret(secret),
            events=events,
            credential_id=credential_id,
            is_verified=False,
            is_active=True
        )
        
        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        
        logger.info(f"Registered webhook for {platform} at {endpoint_url}")
        return webhook
    
    def verify_webhook_signature(
        self,
        webhook_id: int,
        organization_id: int,
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify webhook signature using stored secret.
        
        Args:
            webhook_id: Webhook record ID
            organization_id: Organization ID for tenant isolation
            payload: Raw request body
            signature: Signature from request header
            
        Returns:
            True if signature is valid
        """
        import hashlib
        import hmac
        
        webhook = self.get(webhook_id, organization_id)
        
        if not webhook or not webhook.is_active:
            return False
        
        # Compute expected signature
        expected_sig = hmac.new(
            webhook.secret_hash.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)
    
    def mark_webhook_verified(self, webhook_id: int, organization_id: int) -> bool:
        """Mark webhook as verified after platform confirmation."""
        webhook = self.get(webhook_id, organization_id)
        
        if not webhook:
            return False
        
        webhook.is_verified = True
        webhook.verified_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def record_webhook_delivery(
        self,
        webhook_id: int,
        organization_id: int,
        success: bool,
        response_code: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Record webhook delivery attempt."""
        webhook = self.get(webhook_id, organization_id)
        
        if not webhook:
            return
        
        webhook.last_delivery_at = datetime.utcnow()
        webhook.last_delivery_success = success
        webhook.last_response_code = response_code
        
        if error_message:
            webhook.last_error = error_message
        
        if success:
            webhook.consecutive_failures = 0
        else:
            webhook.consecutive_failures = (webhook.consecutive_failures or 0) + 1
        
        # Deactivate after too many failures
        if webhook.consecutive_failures >= 5:
            webhook.is_active = False
            logger.warning(f"Deactivated webhook {webhook_id} after consecutive failures")
        
        self.db.commit()
    
    def _hash_secret(self, secret: str) -> str:
        """Hash webhook secret for storage."""
        import hashlib
        return hashlib.sha256(secret.encode('utf-8')).hexdigest()


class PlatformRateLimitService(BaseService):
    """
    Service for tracking and enforcing platform API rate limits.
    
    Implements per-platform rate limiting to avoid API throttling.
    """
    
    def __init__(self, db: Session):
        super().__init__(db, PlatformRateLimit)
    
    def get_rate_limit_config(
        self,
        organization_id: int,
        platform: str
    ) -> Optional[PlatformRateLimit]:
        """Get rate limit configuration for a platform."""
        return self.db.query(PlatformRateLimit).filter(
            PlatformRateLimit.organization_id == organization_id,
            PlatformRateLimit.platform == platform
        ).first()
    
    def create_or_update_rate_limit(
        self,
        organization_id: int,
        platform: str,
        requests_per_minute: int,
        requests_per_hour: Optional[int] = None,
        requests_per_day: Optional[int] = None
    ) -> PlatformRateLimit:
        """
        Create or update rate limit configuration.
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            requests_per_minute: Max requests per minute
            requests_per_hour: Optional max requests per hour
            requests_per_day: Optional max requests per day
            
        Returns:
            PlatformRateLimit record
        """
        existing = self.get_rate_limit_config(organization_id, platform)
        
        if existing:
            existing.requests_per_minute = requests_per_minute
            existing.requests_per_hour = requests_per_hour
            existing.requests_per_day = requests_per_day
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        rate_limit = PlatformRateLimit(
            organization_id=organization_id,
            platform=platform,
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day
        )
        
        self.db.add(rate_limit)
        self.db.commit()
        self.db.refresh(rate_limit)
        
        return rate_limit
    
    def check_rate_limit(
        self,
        organization_id: int,
        platform: str
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit.
        
        Args:
            organization_id: Organization ID
            platform: Platform identifier
            
        Returns:
            Tuple of (allowed: bool, wait_seconds: Optional[float])
        """
        config = self.get_rate_limit_config(organization_id, platform)
        
        if not config:
            # No limit configured, allow request
            return True, None
        
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count recent requests
        recent_requests = self.db.query(PlatformRateLimit).filter(
            PlatformRateLimit.organization_id == organization_id,
            PlatformRateLimit.platform == platform
        ).all()
        
        # This is a simplified check - in production you'd use Redis
        # For now, just track last request time
        if config.last_request_at:
            time_since_last = (now - config.last_request_at).total_seconds()
            
            if time_since_last < 60 / config.requests_per_minute:
                wait_time = (60 / config.requests_per_minute) - time_since_last
                return False, wait_time
        
        # Update last request time
        config.last_request_at = now
        config.request_count_today = (config.request_count_today or 0) + 1
        config.request_count_this_hour = (config.request_count_this_hour or 0) + 1
        config.request_count_this_minute = (config.request_count_this_minute or 0) + 1
        
        # Reset counters if needed
        if config.last_reset_date != now.date():
            config.request_count_today = 1
            config.request_count_this_hour = 1
            config.request_count_this_minute = 1
            config.last_reset_date = now.date()
        
        self.db.commit()
        
        return True, None
    
    def record_request(self, organization_id: int, platform: str) -> None:
        """Record an API request for rate limiting."""
        config = self.get_rate_limit_config(organization_id, platform)
        
        if config:
            config.last_request_at = datetime.utcnow()
            config.request_count_today = (config.request_count_today or 0) + 1
            config.request_count_this_hour = (config.request_count_this_hour or 0) + 1
            config.request_count_this_minute = (config.request_count_this_minute or 0) + 1
            self.db.commit()


class AnalyticsJobService(BaseService):
    """
    Service for scheduling and managing analytics collection jobs.
    
    Supports scheduled background jobs for collecting platform analytics.
    """
    
    def __init__(self, db: Session):
        super().__init__(db, AnalyticsJob)
    
    def schedule_job(
        self,
        organization_id: int,
        job_type: str,
        platform: Optional[str] = None,
        episode_id: Optional[int] = None,
        scheduled_at: Optional[datetime] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AnalyticsJob:
        """
        Schedule an analytics collection job.
        
        Args:
            organization_id: Organization ID
            job_type: Type of analytics job
            platform: Optional platform filter
            episode_id: Optional specific episode
            scheduled_at: When to run the job
            priority: Job priority (higher = more urgent)
            metadata: Additional job metadata
            
        Returns:
            Created AnalyticsJob record
        """
        job = AnalyticsJob(
            organization_id=organization_id,
            job_type=job_type,
            platform=platform,
            episode_id=episode_id,
            scheduled_at=scheduled_at or datetime.utcnow(),
            priority=priority,
            status="pending",
            metadata=metadata or {}
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Scheduled analytics job: {job_type} for org {organization_id}")
        return job
    
    def get_pending_jobs(
        self,
        organization_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AnalyticsJob]:
        """Get pending jobs ready for execution."""
        query = self.db.query(AnalyticsJob).filter(
            AnalyticsJob.status == "pending",
            AnalyticsJob.scheduled_at <= datetime.utcnow()
        )
        
        if organization_id:
            query = query.filter(AnalyticsJob.organization_id == organization_id)
        
        return query.order_by(
            AnalyticsJob.priority.desc(),
            AnalyticsJob.scheduled_at.asc()
        ).limit(limit).all()
    
    def start_job(self, job_id: int, organization_id: int) -> Optional[AnalyticsJob]:
        """Mark job as running."""
        job = self.get(job_id, organization_id)
        
        if not job:
            return None
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def complete_job(
        self,
        job_id: int,
        organization_id: int,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[AnalyticsJob]:
        """Mark job as completed or failed."""
        job = self.get(job_id, organization_id)
        
        if not job:
            return None
        
        job.completed_at = datetime.utcnow()
        
        if error_message:
            job.status = "failed"
            job.error_message = error_message
        else:
            job.status = "completed"
            job.result = result
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def retry_job(self, job_id: int, organization_id: int) -> bool:
        """Reset a failed job for retry."""
        job = self.get(job_id, organization_id)
        
        if not job or job.status != "failed":
            return False
        
        job.status = "pending"
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.retry_count = (job.retry_count or 0) + 1
        job.scheduled_at = datetime.utcnow()
        
        self.db.commit()
        return True


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Uses Fernet symmetric encryption for credential storage.
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        from cryptography.fernet import Fernet
        
        if encryption_key is None:
            # In production, load from environment variable
            import os
            encryption_key = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key())
        
        self.cipher = Fernet(encryption_key)
        self.logger = logging.getLogger(__name__)
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary and return base64-encoded string."""
        import json
        data_bytes = json.dumps(data).encode('utf-8')
        encrypted = self.cipher.encrypt(data_bytes)
        return encrypted.decode('utf-8')
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt a base64-encoded string and return dictionary."""
        import json
        data_bytes = encrypted_data.encode('utf-8')
        decrypted = self.cipher.decrypt(data_bytes)
        return json.loads(decrypted.decode('utf-8'))
    
    def encrypt_string(self, value: str) -> str:
        """Encrypt a string."""
        encrypted = self.cipher.encrypt(value.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def decrypt_string(self, encrypted_value: str) -> str:
        """Decrypt a string."""
        decrypted = self.cipher.decrypt(encrypted_value.encode('utf-8'))
        return decrypted.decode('utf-8')
