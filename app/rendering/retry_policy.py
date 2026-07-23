"""
Advanced Retry System for Rendering Jobs

Implements exponential backoff, retry limits, and failure classification.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class FailureType(str, Enum):
    """Types of rendering failures."""
    RESOURCE_ERROR = "resource_error"
    FFMPEG_ERROR = "ffmpeg_error"
    STORAGE_ERROR = "storage_error"
    TIMEOUT = "timeout"
    INVALID_ASSET = "invalid_asset"
    UNKNOWN = "unknown"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    
    # Per-failure-type settings
    retry_on_resource_error: bool = True
    retry_on_ffmpeg_error: bool = True
    retry_on_storage_error: bool = True
    retry_on_timeout: bool = True
    retry_on_invalid_asset: bool = False  # Usually not retryable


@dataclass
class RetryState:
    """State tracking for a retry attempt."""
    
    job_id: str
    attempt_number: int = 0
    last_failure_type: Optional[FailureType] = None
    last_error_message: Optional[str] = None
    last_attempt_time: Optional[float] = None
    next_retry_time: Optional[float] = None
    total_delay_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "attempt_number": self.attempt_number,
            "last_failure_type": self.last_failure_type.value if self.last_failure_type else None,
            "last_error_message": self.last_error_message,
            "last_attempt_time": self.last_attempt_time,
            "next_retry_time": self.next_retry_time,
            "total_delay_seconds": self.total_delay_seconds
        }


class RenderingRetryPolicy:
    """
    Advanced retry system for rendering jobs.
    
    Features:
    - Exponential backoff
    - Retry limits
    - Failure classification
    - Jitter to prevent thundering herd
    """
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
        self.logger = logging.getLogger("rendering.retry")
        self._retry_states: Dict[str, RetryState] = {}
    
    def classify_failure(self, error_message: str, exception_type: Optional[str] = None) -> FailureType:
        """Classify a failure based on error message and exception type."""
        error_lower = (error_message or "").lower()
        exc_type = (exception_type or "").lower()
        
        # Check for timeout
        if "timeout" in error_lower or "timed out" in error_lower:
            return FailureType.TIMEOUT
        
        # Check for resource errors
        resource_indicators = ["memory", "disk", "gpu", "cpu", "resource", "quota"]
        if any(ind in error_lower for ind in resource_indicators):
            return FailureType.RESOURCE_ERROR
        
        # Check for storage errors
        storage_indicators = ["storage", "s3", "bucket", "upload", "download", "permission denied"]
        if any(ind in error_lower for ind in storage_indicators):
            return FailureType.STORAGE_ERROR
        
        # Check for FFmpeg errors
        ffmpeg_indicators = ["ffmpeg", "codec", "encoding", "decoding", "stream", "format"]
        if any(ind in error_lower for ind in ffmpeg_indicators):
            return FailureType.FFMPEG_ERROR
        
        # Check for invalid asset
        asset_indicators = ["invalid", "corrupt", "missing", "not found", "unsupported"]
        if any(ind in error_lower for ind in asset_indicators):
            return FailureType.INVALID_ASSET
        
        return FailureType.UNKNOWN
    
    def should_retry(self, job_id: str, failure_type: FailureType) -> bool:
        """Determine if a job should be retried based on failure type and attempts."""
        state = self._retry_states.get(job_id)
        
        if not state:
            return self._is_retryable_failure(failure_type)
        
        # Check max retries
        if state.attempt_number >= self.policy.max_retries:
            return False
        
        # Check if this failure type is retryable
        return self._is_retryable_failure(failure_type)
    
    def _is_retryable_failure(self, failure_type: FailureType) -> bool:
        """Check if a failure type is retryable."""
        retry_map = {
            FailureType.RESOURCE_ERROR: self.policy.retry_on_resource_error,
            FailureType.FFMPEG_ERROR: self.policy.retry_on_ffmpeg_error,
            FailureType.STORAGE_ERROR: self.policy.retry_on_storage_error,
            FailureType.TIMEOUT: self.policy.retry_on_timeout,
            FailureType.INVALID_ASSET: self.policy.retry_on_invalid_asset,
            FailureType.UNKNOWN: True,
        }
        return retry_map.get(failure_type, False)
    
    def calculate_delay(self, job_id: str) -> Tuple[float, RetryState]:
        """
        Calculate delay before next retry using exponential backoff.
        
        Returns:
            Tuple of (delay_seconds, retry_state)
        """
        now = time.time()
        
        # Get or create retry state
        if job_id not in self._retry_states:
            state = RetryState(job_id=job_id)
            self._retry_states[job_id] = state
        else:
            state = self._retry_states[job_id]
        
        # Increment attempt counter
        state.attempt_number += 1
        state.last_attempt_time = now
        
        # Calculate exponential backoff
        delay = min(
            self.policy.base_delay_seconds * (self.policy.exponential_base ** (state.attempt_number - 1)),
            self.policy.max_delay_seconds
        )
        
        # Add jitter if enabled
        if self.policy.jitter:
            jitter_range = delay * self.policy.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        state.next_retry_time = now + delay
        state.total_delay_seconds += delay
        
        self.logger.info(
            f"Job {job_id}: Attempt {state.attempt_number}, "
            f"delay {delay:.2f}s, next retry at {state.next_retry_time}"
        )
        
        return delay, state
    
    def record_failure(
        self,
        job_id: str,
        error_message: str,
        exception_type: Optional[str] = None
    ) -> Tuple[bool, float, FailureType]:
        """
        Record a failure and determine retry strategy.
        
        Returns:
            Tuple of (should_retry, delay_seconds, failure_type)
        """
        failure_type = self.classify_failure(error_message, exception_type)
        
        should_retry = self.should_retry(job_id, failure_type)
        
        if should_retry:
            delay, _ = self.calculate_delay(job_id)
        else:
            delay = 0.0
        
        # Update state with failure info
        if job_id in self._retry_states:
            state = self._retry_states[job_id]
            state.last_failure_type = failure_type
            state.last_error_message = error_message
        
        self.logger.info(
            f"Job {job_id}: Failure type={failure_type.value}, "
            f"retry={should_retry}, delay={delay:.2f}s"
        )
        
        return should_retry, delay, failure_type
    
    def reset_retry_state(self, job_id: str) -> None:
        """Reset retry state after successful completion."""
        if job_id in self._retry_states:
            del self._retry_states[job_id]
            self.logger.debug(f"Reset retry state for job {job_id}")
    
    def get_retry_state(self, job_id: str) -> Optional[RetryState]:
        """Get current retry state for a job."""
        return self._retry_states.get(job_id)
    
    def cleanup_old_states(self, max_age_hours: int = 24) -> int:
        """Clean up old retry states."""
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned = 0
        
        jobs_to_remove = []
        for job_id, state in self._retry_states.items():
            if state.last_attempt_time and (now - state.last_attempt_time) > max_age_seconds:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._retry_states[job_id]
            cleaned += 1
        
        return cleaned


# Singleton instance
_default_retry_policy: Optional[RenderingRetryPolicy] = None


def get_retry_policy() -> RenderingRetryPolicy:
    """Get or create the default retry policy."""
    global _default_retry_policy
    if _default_retry_policy is None:
        _default_retry_policy = RenderingRetryPolicy()
    return _default_retry_policy
