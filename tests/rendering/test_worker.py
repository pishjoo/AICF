"""
Test Rendering Worker

Tests for the rendering worker system.
"""

import pytest
from unittest.mock import Mock, MagicMock
import time

from app.rendering.worker import RenderingWorker, RenderingTaskDefinition
from app.rendering.queue import (
    InMemoryRenderingQueue,
    RenderingQueueMessage,
    RenderingQueueStatus,
)


class TestRenderingTaskDefinition:
    """Test RenderingTaskDefinition."""
    
    def test_create_task_definition(self):
        """Test creating a task definition."""
        handler = lambda payload: {"success": True}
        
        task_def = RenderingTaskDefinition(
            name="test_transcode",
            handler=handler,
            max_retries=5,
            timeout=600.0
        )
        
        assert task_def.name == "test_transcode"
        assert task_def.max_retries == 5
        assert task_def.timeout == 600.0
        assert task_def.handler == handler


class TestRenderingWorker:
    """Test RenderingWorker functionality."""
    
    @pytest.fixture
    def queue(self):
        """Create a test queue."""
        return InMemoryRenderingQueue()
    
    @pytest.fixture
    def worker(self, queue):
        """Create a test worker."""
        return RenderingWorker(queue=queue)
    
    def test_register_task(self, worker):
        """Test registering a task handler."""
        handler = lambda payload: {"success": True}
        task_def = RenderingTaskDefinition(
            name="transcode_video",
            handler=handler
        )
        
        worker.register_task(task_def)
        
        assert "transcode_video" in worker.tasks
        assert worker.tasks["transcode_video"].handler == handler
    
    def test_process_successful_job(self, worker, queue):
        """Test processing a successful job."""
        # Register a successful handler
        def success_handler(payload):
            return {"success": True, "output": "result.mp4"}
        
        worker.register_task(RenderingTaskDefinition(
            name="test_task",
            handler=success_handler
        ))
        
        # Create and enqueue job
        msg = RenderingQueueMessage(
            job_id="success-job",
            task_type="test_task",
            payload={"input": "input.mp4"}
        )
        queue.enqueue(msg)
        
        # Dequeue and process
        dequeued = queue.dequeue(timeout=1.0)
        result = worker.process_job(dequeued)
        
        assert result is True  # Job completed successfully
        assert worker.processed_count == 1
        assert worker.failed_count == 0
        
        # Verify status updated
        status = queue.get_status(msg.message_id)
        assert status == RenderingQueueStatus.COMPLETED
    
    def test_process_failed_job_with_retry(self, worker, queue):
        """Test failed job retry logic."""
        # Register a failing handler
        def fail_handler(payload):
            raise Exception("Simulated failure")
        
        worker.register_task(RenderingTaskDefinition(
            name="failing_task",
            handler=fail_handler,
            max_retries=3
        ))
        
        # Create and enqueue job
        msg = RenderingQueueMessage(
            job_id="retry-job",
            task_type="failing_task",
            payload={},
            max_retries=3,
            retry_count=0
        )
        queue.enqueue(msg)
        
        # Dequeue and process (will fail)
        dequeued = queue.dequeue(timeout=1.0)
        result = worker.process_job(dequeued)
        
        # Should return False (not completed)
        assert result is False
        assert worker.failed_count == 0  # Not counted as permanent failure yet
        
        # Job should be requeued
        assert queue.get_queue_size() == 1
    
    def test_process_job_exceeds_max_retries(self, queue):
        """Test job that exceeds max retries becomes permanently failed."""
        worker = RenderingWorker(queue=queue)
        
        # Register a failing handler
        def fail_handler(payload):
            raise Exception("Always fails")
        
        worker.register_task(RenderingTaskDefinition(
            name="always_fails",
            handler=fail_handler,
            max_retries=2
        ))
        
        # Create job at retry limit
        msg = RenderingQueueMessage(
            job_id="max-retry-job",
            task_type="always_fails",
            payload={},
            max_retries=2,
            retry_count=2  # Already at max
        )
        queue.enqueue(msg)
        
        # Process
        dequeued = queue.dequeue(timeout=1.0)
        result = worker.process_job(dequeued)
        
        assert result is False
        assert worker.failed_count == 1
        
        # Status should be FAILED
        status = queue.get_status(msg.message_id)
        assert status == RenderingQueueStatus.FAILED
    
    def test_worker_run_loop(self, queue):
        """Test worker run loop processes multiple jobs."""
        worker = RenderingWorker(queue=queue)
        
        # Register handler
        def handler(payload):
            return {"success": True}
        
        worker.register_task(RenderingTaskDefinition(
            name="simple",
            handler=handler
        ))
        
        # Enqueue multiple jobs
        for i in range(3):
            msg = RenderingQueueMessage(
                job_id=f"job-{i}",
                task_type="simple",
                payload={}
            )
            queue.enqueue(msg)
        
        # Run worker for limited jobs
        worker.run(max_jobs=3, poll_interval=0.1)
        
        assert worker.processed_count == 3
        assert not worker.running  # Should have stopped
    
    def test_worker_stop(self, worker):
        """Test stopping worker gracefully."""
        worker.running = True
        worker.stop()
        
        assert worker.running is False
    
    def test_worker_stats(self, worker, queue):
        """Test getting worker statistics."""
        # Enqueue some jobs
        for i in range(5):
            msg = RenderingQueueMessage(job_id=f"stat-job-{i}", task_type="test")
            queue.enqueue(msg)
        
        stats = worker.get_stats()
        
        assert stats["running"] is False
        assert stats["processed_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["queue_size"] == 5
        assert stats["registered_tasks"] == []


class TestWorkerExceptionHandling:
    """Test worker exception handling."""
    
    def test_unknown_task_type(self):
        """Test handling of unknown task types."""
        queue = InMemoryRenderingQueue()
        worker = RenderingWorker(queue=queue)
        
        # Create job with unregistered task type
        msg = RenderingQueueMessage(
            job_id="unknown-task",
            task_type="nonexistent_task",
            payload={}
        )
        
        result = worker._execute_task(msg)
        
        assert result["success"] is False
        assert "Unknown rendering task type" in result["error"]
    
    def test_handler_exception_capture(self):
        """Test that handler exceptions are properly captured."""
        queue = InMemoryRenderingQueue()
        worker = RenderingWorker(queue=queue)
        
        def raising_handler(payload):
            raise ValueError("Test error message")
        
        worker.register_task(RenderingTaskDefinition(
            name="raises_error",
            handler=raising_handler
        ))
        
        msg = RenderingQueueMessage(
            job_id="exception-test",
            task_type="raises_error",
            payload={}
        )
        
        result = worker._execute_task(msg)
        
        assert result["success"] is False
        assert "Test error message" in result["error"]
        assert result["exception_type"] == "ValueError"


class TestTenantIsolationInWorker:
    """Test tenant isolation in worker processing."""
    
    def test_organization_context_in_payload(self):
        """Test that organization context can be passed in payload."""
        queue = InMemoryRenderingQueue()
        worker = RenderingWorker(queue=queue)
        
        org_id = 456
        
        def org_aware_handler(payload):
            # Handler can access organization from payload
            assert payload.get("organization_id") == org_id
            return {"success": True, "org": payload.get("organization_id")}
        
        worker.register_task(RenderingTaskDefinition(
            name="org_aware",
            handler=org_aware_handler
        ))
        
        msg = RenderingQueueMessage(
            job_id="org-job",
            task_type="org_aware",
            payload={"organization_id": org_id, "data": "test"}
        )
        
        result = worker._execute_task(msg)
        
        assert result["success"] is True
        assert result["org"] == org_id
