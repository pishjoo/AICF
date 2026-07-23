"""
Platform Adapters - Base Classes and Implementations

Provides abstract base classes and concrete implementations for
integrating with external publishing platforms (YouTube, Vimeo, etc.)
with OAuth2 support, rate limiting, and failure isolation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from services.publishing import EncryptionService


logger = logging.getLogger(__name__)


class PlatformAdapterError(Exception):
    """Base exception for platform adapter errors."""
    
    def __init__(self, message: str, retryable: bool = False, platform_response: Optional[Dict] = None):
        super().__init__(message)
        self.retryable = retryable
        self.platform_response = platform_response


class RateLimitExceeded(PlatformAdapterError):
    """Raised when platform rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message, retryable=True)
        self.retry_after_seconds = retry_after_seconds


class AuthenticationError(PlatformAdapterError):
    """Raised when platform authentication fails."""
    
    def __init__(self, message: str, token_expired: bool = False):
        super().__init__(message, retryable=False)
        self.token_expired = token_expired


class PlatformAdapter(ABC):
    """
    Abstract base class for platform adapters.
    
    All platform integrations must implement this interface.
    Provides common functionality for OAuth2, rate limiting, and error handling.
    """
    
    PLATFORM_NAME: str = "base"
    
    def __init__(
        self,
        credential_id: int,
        organization_id: int,
        encryption_service: EncryptionService,
        rate_limit_service: 'PlatformRateLimitService'
    ):
        self.credential_id = credential_id
        self.organization_id = organization_id
        self.encryption_service = encryption_service
        self.rate_limit_service = rate_limit_service
        self._credential_cache: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(f"platform.{self.PLATFORM_NAME}")
    
    @abstractmethod
    def get_credentials(self) -> Dict[str, Any]:
        """Retrieve and decrypt platform credentials."""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the platform.
        
        Returns:
            True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a video to the platform.
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            metadata: Additional metadata (tags, category, etc.)
            
        Returns:
            Platform-specific response with video ID and URL
            
        Raises:
            PlatformAdapterError: If upload fails
        """
        pass
    
    @abstractmethod
    async def update_video(
        self,
        video_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update video metadata on the platform.
        
        Args:
            video_id: Platform's video ID
            metadata: Updated metadata
            
        Returns:
            Platform response
        """
        pass
    
    @abstractmethod
    async def delete_video(self, video_id: str) -> bool:
        """
        Delete a video from the platform.
        
        Args:
            video_id: Platform's video ID
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def get_analytics(
        self,
        video_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Fetch analytics data for a video.
        
        Args:
            video_id: Platform's video ID
            start_date: Start of analytics period
            end_date: End of analytics period
            
        Returns:
            Analytics data dictionary
        """
        pass
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits before making API calls."""
        allowed, wait_time = self.rate_limit_service.check_rate_limit(
            self.organization_id,
            self.PLATFORM_NAME
        )
        
        if not allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {self.PLATFORM_NAME}",
                retry_after_seconds=wait_time
            )
    
    def _record_api_call(self) -> None:
        """Record an API call for rate limiting."""
        self.rate_limit_service.record_request(
            self.organization_id,
            self.PLATFORM_NAME
        )
    
    async def _refresh_token_if_needed(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh OAuth token if expired.
        
        Subclasses should override to implement platform-specific token refresh.
        """
        return credentials
    
    def _isolate_failure(self, error: Exception, operation: str) -> None:
        """
        Log and isolate platform failures from workflow engine.
        
        This ensures platform failures don't crash the workflow engine.
        """
        self.logger.error(
            f"Platform {self.PLATFORM_NAME} failure during {operation}: {error}",
            exc_info=True
        )
        # Failure is isolated - just log it, don't propagate


class OAuth2PlatformAdapter(PlatformAdapter):
    """
    Base class for platforms using OAuth2 authentication.
    
    Provides common OAuth2 flow implementation including:
    - Authorization code flow
    - Token refresh
    - Token storage
    """
    
    AUTHORIZATION_URL: str = ""
    TOKEN_URL: str = ""
    REDIRECT_URI: str = ""
    SCOPES: List[str] = []
    
    def __init__(
        self,
        credential_id: int,
        organization_id: int,
        encryption_service: EncryptionService,
        rate_limit_service: 'PlatformRateLimitService',
        client_id: str,
        client_secret: str
    ):
        super().__init__(
            credential_id,
            organization_id,
            encryption_service,
            rate_limit_service
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth2 authorization URL.
        
        Args:
            state: CSRF protection state parameter
            
        Returns:
            Authorization URL for user redirect
        """
        from urllib.parse import urlencode
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(self.SCOPES),
            'state': state,
            'access_type': 'offline',  # For refresh tokens
            'prompt': 'consent'
        }
        
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            authorization_code: Code from OAuth callback
            
        Returns:
            Token response dictionary
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        import aiohttp
        
        await self._check_rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data={
                        'grant_type': 'authorization_code',
                        'code': authorization_code,
                        'redirect_uri': self.REDIRECT_URI,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret
                    }
                ) as response:
                    self._record_api_call()
                    
                    if response.status != 200:
                        error_data = await response.json()
                        raise AuthenticationError(
                            f"Token exchange failed: {error_data}"
                        )
                    
                    token_data = await response.json()
                    return self._process_token_response(token_data)
                    
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Token exchange request failed: {e}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous grant
            
        Returns:
            New token response dictionary
        """
        import aiohttp
        
        await self._check_rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': refresh_token,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret
                    }
                ) as response:
                    self._record_api_call()
                    
                    if response.status != 200:
                        error_data = await response.json()
                        raise AuthenticationError(
                            f"Token refresh failed: {error_data}",
                            token_expired=True
                        )
                    
                    token_data = await response.json()
                    return self._process_token_response(token_data)
                    
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Token refresh request failed: {e}")
    
    def _process_token_response(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and store token response.
        
        Args:
            token_data: Raw token response from platform
            
        Returns:
            Processed token data
        """
        self._access_token = token_data.get('access_token')
        
        expires_in = token_data.get('expires_in', 3600)
        self._token_expires_at = datetime.utcnow().replace(
            microsecond=0
        ) + timedelta(seconds=expires_in)
        
        return {
            'access_token': self._access_token,
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': self._token_expires_at.isoformat(),
            'token_type': token_data.get('token_type', 'Bearer')
        }
    
    async def _get_valid_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        credentials = self.get_credentials()
        
        # Check if token needs refresh
        expires_at = credentials.get('expires_at')
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            # Refresh 5 minutes before expiration
            if datetime.utcnow() > expires_dt - timedelta(minutes=5):
                refresh_token = credentials.get('refresh_token')
                if refresh_token:
                    new_tokens = await self.refresh_access_token(refresh_token)
                    # Update stored credentials
                    # (implementation depends on credential service)
                    credentials.update(new_tokens)
        
        return credentials.get('access_token')
    
    def get_credentials(self) -> Dict[str, Any]:
        """Retrieve decrypted credentials."""
        if self._credential_cache:
            return self._credential_cache
        
        from sqlalchemy.orm import Session
        from database.models import PublishingCredential
        
        # This would be called with proper session in real implementation
        # For now, placeholder - actual implementation in concrete classes
        return {}


# Import timedelta for token expiration
from datetime import timedelta
