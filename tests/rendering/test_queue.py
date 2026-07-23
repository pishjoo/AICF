"""
Test Rendering Queue System

Tests for the rendering queue abstraction layer.
"""

import pytest
from datetime import datetime, timezone
import time

from app.rendering.queue import (
    RenderingQueueMessage,
    RenderingQueueStatus,
    InMemoryRenderingQueue,
    RedisRenderingQueue,
)


class TestRenderingQueueMessage:
    """Test RenderingQueueMessage dataclass."""
    
    def test_create_message(self):
        """Test creating a queue message."""
        msg = RenderingQueueMessage(
            job_id="test-job-123",
            task_type="transcode",
            payload={"input": "video.mp4", "output": "output.mp4"},
            priority=5,
        )
        
        assert msg.job_id == "test-job-123"
        assert msg.task_type == "transcode"
        assert msg.payload == {"input": "video.mp4", "output": "output.mp4"}
        assert msg.priority == 5
        assert msg.status == RenderingQueueStatus.PENDING
        assert msg.retry_count == 0
        assert msg.max_retries == 3
    
    def test_message_serialization(self):
        """Test message to_dict and from_dict."""
        msg = RenderingQueueMessage(
            job_id="test-job-456",
            task_type="render",
            payload={"clips": ["clip1.mp4", "clip2.mp4"]},
        )
        
        # Serialize
        data = msg.to_dict()
        assert data["job_id"] == "test-job-456"
        assert data["task_type"] == "render"
        assert "created_at" in data
        
        # Deserialize
        msg2 = RenderingQueueMessage.from_dict(data)
        assert msg2.job_id == msg.job_id
        assert msg2.task_type == msg.task_type
        assert msg2.payload == msg.payload
    
    def test_status_transitions(self):
        """Test message status state transitions."""
        msg = RenderingQueueMessage(job_id="test", task_type="test")
        
        # Initial state
        assert msg.status == RenderingQueueStatus.PENDING
        
        # Mark queued
        msg.mark_queued()
        assert msg.status == RenderingQueueStatus.QUEUED
        
        # Mark processing
        msg.mark_processing()
        assert msg.status == RenderingQueueStatus.PROCESSING
        assert msg.started_at is not None
        
        # Mark completed
        msg.mark_completed()
        assert msg.status == RenderingQueueStatus.COMPLETED
        assert msg.completed_at is not None
    
    def test_retry_logic(self):
        """Test retry count increment."""
        msg = RenderingQueueMessage(
            job_id="test",
            task_type="test",
            max_retries=3,
            retry_count=0
        )
        
        msg.mark_failed("Initial error")
        assert msg.status == RenderingQueueStatus.FAILED
        
        msg.mark_retrying()
        assert msg.status == RenderingQueueStatus.QUEUED
        assert msg.retry_count == 1
        assert msg.error_message is None


class TestInMemoryRenderingQueue:
    """Test InMemoryRenderingQueue implementation."""
    
    @pytest.fixture
    def queue(self):
        """Create an in-memory queue for testing."""
        return InMemoryRenderingQueue()
    
    def test_enqueue_dequeue(self, queue):
        """Test basic enqueue and dequeue operations."""
        msg = RenderingQueueMessage(
            job_id="job-1",
            task_type="transcode",
            payload={}
        )
        
        # Enqueue
        msg_id = queue.enqueue(msg)
        assert msg_id == msg.message_id
        assert queue.get_queue_size() == 1
        
        # Dequeue
        dequeued = queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.message_id == msg_id
        assert dequeued.status == RenderingQueueStatus.PROCESSING
        assert queue.get_queue_size() == 0
    
    def test_priority_ordering(self, queue):
        """Test that higher priority jobs are dequeued first."""
        # Add low priority job first
        low_msg = RenderingQueueMessage(
            job_id="low-priority",
            task_type="test",
            priority=1
        )
        queue.enqueue(low_msg)
        
        # Add high priority job second
        high_msg = RenderingQueueMessage(
            job_id="high-priority",
            task_type="test",
            priority=10
        )
        queue.enqueue(high_msg)
        
        # High priority should be dequeued first
        first = queue.dequeue(timeout=1.0)
        assert first.job_id == "high-priority"
        
        second = queue.dequeue(timeout=1.0)
        assert second.job_id == "low-priority"
    
    def test_peek(self, queue):
        """Test peek operation doesn't remove job."""
        msg = RenderingQueueMessage(job_id="peek-test", task_type="test")
        queue.enqueue(msg)
        
        # Peek multiple times
        peeked1 = queue.peek()
        peeked2 = queue.peek()
        
        assert peeked1.message_id == msg.message_id
        assert peeked2.message_id == msg.message_id
        assert queue.get_queue_size() == 1  # Size unchanged
    
    def test_status_tracking(self, queue):
        """Test status get and update."""
        msg = RenderingQueueMessage(job_id="status-test", task_type="test")
        queue.enqueue(msg)
        
        # Get initial status
        status = queue.get_status(msg.message_id)
        assert status == RenderingQueueStatus.QUEUED
        
        # Update status
        queue.update_status(msg.message_id, RenderingQueueStatus.PAUSED)
        new_status = queue.get_status(msg.message_id)
        assert new_status == RenderingQueueStatus.PAUSED
    
    def test_clear(self, queue):
        """Test clearing all jobs."""
        for i in range(5):
            msg = RenderingQueueMessage(job_id=f"job-{i}", task_type="test")
            queue.enqueue(msg)
        
        assert queue.get_queue_size() == 5
        
        cleared = queue.clear()
        assert cleared == 5
        assert queue.get_queue_size() == 0
    
    def test_requeue_failed(self, queue):
        """Test requeuing failed jobs."""
        # Create and fail a job
        msg = RenderingQueueMessage(
            job_id="fail-test",
            task_type="test",
            max_retries=3,
            retry_count=0
        )
        queue.enqueue(msg)
        dequeued = queue.dequeue(timeout=1.0)
        dequeued.mark_failed("Test error")
        queue.update_status(msg.message_id, RenderingQueueStatus.FAILED)
        
        # Requeue
        requeued = queue.requeue_failed(max_retries=3)
        assert requeued == 1
        
        # Verify status changed
        status = queue.get_status(msg.message_id)
        assert status == RenderingQueueStatus.QUEUED


class TestRedisRenderingQueue:
    """Test RedisRenderingQueue with fallback behavior."""
    
    def test_redis_fallback_to_memory(self):
        """Test that Redis queue falls back to memory when Redis unavailable."""
        # This should not raise, but fall back to in-memory
        queue = RedisRenderingQueue(
            redis_url="redis://nonexistent:6379/0",
            queue_name="test_rendering_jobs"
        )
        
        # Should have fallback enabled
        assert hasattr(queue, '_fallback')
        
        # Operations should work via fallback
        msg = RenderingQueueMessage(job_id="fallback-test", task_type="test")
        msg_id = queue.enqueue(msg)
        assert msg_id is not None
        
        dequeued = queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.job_id == "fallback-test"


class TestTenantIsolationInQueue:
    """Test tenant isolation in queue messages."""
    
    def test_organization_id_in_metadata(self):
        """Test that organization ID can be stored in message metadata."""
        msg = RenderingQueueMessage(
            job_id="org-test-job",
            task_type="transcode",
            payload={},
            metadata={"organization_id": 123}
        )
        
        assert msg.metadata["organization_id"] == 123
        
        # Verify it persists through serialization
        data = msg.to_dict()
        msg2 = RenderingQueueMessage.from_dict(data)
        assert msg2.metadata["organization_id"] == 123
