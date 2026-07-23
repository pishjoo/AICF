"""Tests for retry policy system."""

import pytest
from app.rendering.retry_policy import (
    RenderingRetryPolicy,
    RetryPolicy,
    FailureType,
    get_retry_policy,
)


class TestFailureClassification:
    """Test failure type classification."""
    
    def test_classify_timeout(self):
        """Test timeout failure classification."""
        policy = RenderingRetryPolicy()
        
        result = policy.classify_failure("Operation timed out after 30s")
        assert result == FailureType.TIMEOUT
        
        result = policy.classify_failure("Timeout expired")
        assert result == FailureType.TIMEOUT
    
    def test_classify_resource_error(self):
        """Test resource error classification."""
        policy = RenderingRetryPolicy()
        
        result = policy.classify_failure("Out of memory")
        assert result == FailureType.RESOURCE_ERROR
        
        result = policy.classify_failure("GPU memory exhausted")
        assert result == FailureType.RESOURCE_ERROR
    
    def test_classify_ffmpeg_error(self):
        """Test FFmpeg error classification."""
        policy = RenderingRetryPolicy()
        
        result = policy.classify_failure("FFmpeg codec not found")
        assert result == FailureType.FFMPEG_ERROR
        
        result = policy.classify_failure("Encoding failed: invalid stream")
        assert result == FailureType.FFMPEG_ERROR
    
    def test_classify_storage_error(self):
        """Test storage error classification."""
        policy = RenderingRetryPolicy()
        
        result = policy.classify_failure("S3 upload failed")
        assert result == FailureType.STORAGE_ERROR
        
        result = policy.classify_failure("Permission denied writing to storage")
        assert result == FailureType.STORAGE_ERROR
    
    def test_classify_invalid_asset(self):
        """Test invalid asset classification."""
        policy = RenderingRetryPolicy()
        
        result = policy.classify_failure("Invalid video format")
        assert result == FailureType.INVALID_ASSET
        
        result = policy.classify_failure("File not found")
        assert result == FailureType.INVALID_ASSET


class TestRetryDecision:
    """Test retry decision logic."""
    
    def test_should_retry_resource_error(self):
        """Test retry on resource errors."""
        policy = RenderingRetryPolicy()
        
        should_retry = policy.should_retry("job-123", FailureType.RESOURCE_ERROR)
        assert should_retry is True
    
    def test_should_not_retry_invalid_asset(self):
        """Test no retry on invalid assets."""
        policy = RenderingRetryPolicy()
        
        should_retry = policy.should_retry("job-123", FailureType.INVALID_ASSET)
        assert should_retry is False
    
    def test_max_retries_exceeded(self):
        """Test max retries limit."""
        policy_config = RetryPolicy(max_retries=2)
        policy = RenderingRetryPolicy(policy_config)
        
        # Simulate multiple failures
        policy.record_failure("job-123", "Error 1")
        policy.record_failure("job-123", "Error 2")
        
        should_retry = policy.should_retry("job-123", FailureType.RESOURCE_ERROR)
        assert should_retry is False


class TestExponentialBackoff:
    """Test exponential backoff calculation."""
    
    def test_delay_increases_with_attempts(self):
        """Test delay increases exponentially."""
        policy = RenderingRetryPolicy()
        
        _, state1 = policy.calculate_delay("job-123")
        delay1 = state1.next_retry_time - state1.last_attempt_time
        
        _, state2 = policy.calculate_delay("job-123")
        delay2 = state2.next_retry_time - state2.last_attempt_time
        
        assert delay2 > delay1
    
    def test_delay_respects_max(self):
        """Test delay respects maximum."""
        policy_config = RetryPolicy(
            base_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
            jitter=False
        )
        policy = RenderingRetryPolicy(policy_config)
        
        # Force many attempts
        for i in range(10):
            delay, _ = policy.calculate_delay("job-123")
        
        assert delay <= policy_config.max_delay_seconds


class TestSingleton:
    """Test singleton pattern."""
    
    def test_singleton_pattern(self):
        """Test retry policy singleton."""
        policy1 = get_retry_policy()
        policy2 = get_retry_policy()
        assert policy1 is policy2
