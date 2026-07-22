"""
Integration Tests for Phase 4: Production Infrastructure Foundation

Tests for:
- Job creation and queue execution
- Agent runtime
- Storage provider
- Database updates
"""

import pytest
import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import (
    Organization, User, ChannelProfile, Playlist, Episode,
    ContentJob, ContentJobStatus, AgentExecution, AgentExecutionStatus, Asset, AssetType
)
from app.jobs.queue import InMemoryJobQueue, JobMessage, TaskStatus
from app.jobs.worker import JobWorker, TaskDefinition
from app.jobs.tasks import WorkflowTask
from app.agents.runtime import AgentRuntime, RuntimeContext, AgentResult
from app.storage.providers import LocalStorageProvider, StorageProviderType


# Test fixtures
@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_organization(db_session):
    """Create a test organization."""
    org = Organization(
        name="Test Org",
        slug="test-org",
        subscription_plan="pro"
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session, test_organization):
    """Create a test user."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        organization_id=test_organization.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_channel(db_session, test_organization):
    """Create a test channel profile."""
    channel = ChannelProfile(
        name="Test Channel",
        niche="Education",
        target_audience="Students",
        organization_id=test_organization.id
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def test_playlist(db_session, test_channel):
    """Create a test playlist."""
    playlist = Playlist(
        title="Test Playlist",
        playlist_type="planned_playlist",
        channel_profile_id=test_channel.id,
        organization_id=test_channel.organization_id
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


@pytest.fixture
def test_episode(db_session, test_playlist, test_channel):
    """Create a test episode."""
    episode = Episode(
        title="Test Episode",
        description="A test episode for workflow testing",
        topic="Test Topic",
        playlist_id=test_playlist.id,
        channel_profile_id=test_channel.id,
        organization_id=test_channel.organization_id
    )
    db_session.add(episode)
    db_session.commit()
    db_session.refresh(episode)
    return episode


# =============================================================================
# Job Queue Tests
# =============================================================================

class TestJobQueue:
    """Tests for job queue functionality."""
    
    def test_job_message_creation(self):
        """Test creating a job message."""
        msg = JobMessage(
            task_type="workflow.create",
            payload={"episode_id": 1},
            priority=5
        )
        
        assert msg.job_id is not None
        assert msg.task_type == "workflow.create"
        assert msg.payload == {"episode_id": 1}
        assert msg.priority == 5
        assert msg.status == TaskStatus.PENDING
    
    def test_in_memory_queue_enqueue_dequeue(self):
        """Test enqueueing and dequeueing from in-memory queue."""
        queue = InMemoryJobQueue()
        
        msg = JobMessage(
            task_type="stage.execute",
            payload={"episode_id": 1, "stage_type": "idea"}
        )
        
        job_id = queue.enqueue(msg)
        
        assert job_id == msg.job_id
        assert queue.get_queue_size() == 1
        assert queue.get_status(job_id) == TaskStatus.QUEUED
        
        # Dequeue
        dequeued = queue.dequeue(timeout=0.1)
        
        assert dequeued is not None
        assert dequeued.job_id == job_id
        assert dequeued.status == TaskStatus.RUNNING
        assert queue.get_queue_size() == 0
    
    def test_in_memory_queue_priority_ordering(self):
        """Test that higher priority jobs are dequeued first."""
        queue = InMemoryJobQueue()
        
        # Add low priority job first
        low_msg = JobMessage(
            task_type="test",
            payload={},
            priority=1
        )
        queue.enqueue(low_msg)
        
        # Add high priority job second
        high_msg = JobMessage(
            task_type="test",
            payload={},
            priority=10
        )
        queue.enqueue(high_msg)
        
        # High priority should come out first
        first = queue.dequeue(timeout=0.1)
        assert first.job_id == high_msg.job_id
        
        second = queue.dequeue(timeout=0.1)
        assert second.job_id == low_msg.job_id
    
    def test_queue_status_update(self):
        """Test updating job status."""
        queue = InMemoryJobQueue()
        
        msg = JobMessage(task_type="test", payload={})
        job_id = queue.enqueue(msg)
        
        assert queue.get_status(job_id) == TaskStatus.QUEUED
        
        queue.update_status(job_id, TaskStatus.RUNNING)
        assert queue.get_status(job_id) == TaskStatus.RUNNING
        
        queue.update_status(job_id, TaskStatus.COMPLETED)
        assert queue.get_status(job_id) == TaskStatus.COMPLETED
    
    def test_queue_clear(self):
        """Test clearing all jobs from queue."""
        queue = InMemoryJobQueue()
        
        for i in range(5):
            msg = JobMessage(task_type="test", payload={"i": i})
            queue.enqueue(msg)
        
        assert queue.get_queue_size() == 5
        
        cleared = queue.clear()
        
        assert cleared == 5
        assert queue.get_queue_size() == 0


# =============================================================================
# Job Worker Tests
# =============================================================================

class TestJobWorker:
    """Tests for job worker functionality."""
    
    def test_worker_task_registration(self):
        """Test registering tasks with worker."""
        queue = InMemoryJobQueue()
        worker = JobWorker(queue=queue)
        
        def dummy_handler(payload):
            return {"result": "ok"}
        
        task_def = TaskDefinition(
            name="test.task",
            handler=dummy_handler
        )
        
        worker.register_task(task_def)
        
        assert "test.task" in worker.tasks
        assert worker.tasks["test.task"].name == "test.task"
    
    def test_worker_process_job_success(self):
        """Test processing a successful job."""
        queue = InMemoryJobQueue()
        worker = JobWorker(queue=queue)
        
        def success_handler(payload):
            from app.jobs.queue import TaskResult
            return TaskResult.success({"output": "success"})
        
        worker.register_task(TaskDefinition(
            name="test.success",
            handler=success_handler
        ))
        
        msg = JobMessage(
            task_type="test.success",
            payload={}
        )
        queue.enqueue(msg)
        
        dequeued = queue.dequeue(timeout=0.1)
        result = worker.process_job(dequeued)
        
        assert result is True  # Success
        assert worker.processed_count == 1
    
    def test_worker_process_job_failure(self):
        """Test processing a failed job."""
        queue = InMemoryJobQueue()
        worker = JobWorker(queue=queue)
        
        def failure_handler(payload):
            from app.jobs.queue import TaskResult
            return TaskResult.failure("Something went wrong")
        
        worker.register_task(TaskDefinition(
            name="test.failure",
            handler=failure_handler,
            max_retries=0  # No retries for this test
        ))
        
        msg = JobMessage(
            task_type="test.failure",
            payload={},
            max_retries=0
        )
        queue.enqueue(msg)
        
        dequeued = queue.dequeue(timeout=0.1)
        result = worker.process_job(dequeued)
        
        assert result is False  # Failed
        assert worker.failed_count == 1
    
    def test_worker_get_stats(self):
        """Test getting worker statistics."""
        queue = InMemoryJobQueue()
        worker = JobWorker(queue=queue)
        
        stats = worker.get_stats()
        
        assert "running" in stats
        assert "processed_count" in stats
        assert "failed_count" in stats
        assert "queue_size" in stats
        assert "registered_tasks" in stats


# =============================================================================
# Agent Runtime Tests
# =============================================================================

class TestAgentRuntime:
    """Tests for agent runtime functionality."""
    
    def test_runtime_context_creation(self, test_episode, test_channel):
        """Test creating a runtime context."""
        context = RuntimeContext(
            episode=test_episode,
            channel_profile=test_channel,
            organization_id=test_channel.organization_id,
            previous_outputs={"idea": {"topic": "test"}},
            settings={"custom_instructions": "Make it good"}
        )
        
        assert context.episode == test_episode
        assert context.channel_profile == test_channel
        assert context.organization_id == test_channel.organization_id
        assert "idea" in context.previous_outputs
        assert context.settings["custom_instructions"] == "Make it good"
    
    def test_agent_result_success(self):
        """Test creating a successful agent result."""
        result = AgentResult.success(
            output={"script": "Once upon a time..."},
            execution_time=2.5,
            token_usage=100,
            metadata={"agent": "script_agent"}
        )
        
        assert result.status == "success"
        assert result.output["script"] == "Once upon a time..."
        assert result.execution_time == 2.5
        assert result.token_usage == 100
        assert result.error is None
    
    def test_agent_result_failure(self):
        """Test creating a failed agent result."""
        result = AgentResult.failure(
            error="Input validation failed",
            execution_time=0.1,
            output={"partial": "data"}
        )
        
        assert result.status == "failed"
        assert result.error == "Input validation failed"
        assert result.execution_time == 0.1
    
    def test_agent_result_timeout(self):
        """Test creating a timeout agent result."""
        result = AgentResult.timeout(
            timeout_seconds=300.0,
            output={"partial": "data"}
        )
        
        assert result.status == "timeout"
        assert "timed out after 300.0s" in result.error
    
    def test_agent_result_to_dict(self):
        """Test converting agent result to dictionary."""
        result = AgentResult.success(
            output={"key": "value"},
            execution_time=1.0,
            token_usage=50
        )
        
        d = result.to_dict()
        
        assert d["status"] == "success"
        assert d["output"] == {"key": "value"}
        assert d["execution_time"] == 1.0
        assert d["token_usage"] == 50
        assert d["error"] is None


# =============================================================================
# Storage Provider Tests
# =============================================================================

class TestStorageProvider:
    """Tests for storage provider functionality."""
    
    def test_local_storage_upload(self):
        """Test uploading a file to local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            file_content = b"Hello, World!"
            file_obj = io.BytesIO(file_content)
            
            result = provider.upload(
                file=file_obj,
                key="test/org_1/file.txt",
                content_type="text/plain",
                metadata={"test": "true"}
            )
            
            assert result.success is True
            assert result.storage_key == "test/org_1/file.txt"
            assert result.provider == StorageProviderType.LOCAL
            assert result.metadata.file_size_bytes == len(file_content)
            assert result.metadata.checksum_md5 is not None
    
    def test_local_storage_download(self):
        """Test downloading a file from local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            # Upload first
            file_content = b"Download test content"
            file_obj = io.BytesIO(file_content)
            
            provider.upload(
                file=file_obj,
                key="test/download.txt",
                content_type="text/plain"
            )
            
            # Download
            downloaded = provider.download("test/download.txt")
            
            assert downloaded is not None
            assert downloaded.read() == file_content
    
    def test_local_storage_exists(self):
        """Test checking if a file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            # Upload a file
            file_obj = io.BytesIO(b"test")
            provider.upload(file=file_obj, key="exists.txt")
            
            assert provider.exists("exists.txt") is True
            assert provider.exists("not_exists.txt") is False
    
    def test_local_storage_delete(self):
        """Test deleting a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            # Upload then delete
            file_obj = io.BytesIO(b"to delete")
            provider.upload(file=file_obj, key="delete_me.txt")
            
            assert provider.exists("delete_me.txt") is True
            
            result = provider.delete("delete_me.txt")
            
            assert result is True
            assert provider.exists("delete_me.txt") is False
    
    def test_local_storage_get_url(self):
        """Test getting URL for a stored file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            file_obj = io.BytesIO(b"url test")
            provider.upload(file=file_obj, key="url_test.txt")
            
            url = provider.get_url("url_test.txt")
            
            assert url.startswith("file://")
            assert "url_test.txt" in url
    
    def test_local_storage_metadata_persistence(self):
        """Test that metadata is persisted with file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_path=tmpdir)
            
            file_obj = io.BytesIO(b"metadata test")
            result = provider.upload(
                file=file_obj,
                key="meta_test.txt",
                metadata={"custom": "value", "stage": "research"}
            )
            
            # Check metadata was saved
            assert result.metadata.custom_metadata["custom"] == "value"
            assert result.metadata.custom_metadata["stage"] == "research"
            
            # Verify metadata file exists
            meta_path = Path(tmpdir) / "meta_test.txt.meta"
            assert meta_path.exists()


# =============================================================================
# Database Integration Tests
# =============================================================================

class TestDatabaseUpdates:
    """Tests for database schema updates."""
    
    def test_agent_execution_new_fields(self, db_session, test_episode):
        """Test AgentExecution has new fields."""
        execution = AgentExecution(
            episode_id=test_episode.id,
            organization_id=test_episode.organization_id,
            agent_name="test_agent",
            agent_type="idea",
            status=AgentExecutionStatus.SUCCESS
        )
        
        # Set new fields
        execution.started_at = datetime.now(timezone.utc)
        execution.finished_at = datetime.now(timezone.utc)
        execution.execution_time = 2.5
        execution.token_usage = 100
        execution.cost_usd = 0.002
        
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)
        
        assert execution.started_at is not None
        assert execution.finished_at is not None
        assert execution.execution_time == 2.5
        assert execution.token_usage == 100
        assert execution.cost_usd == 0.002
    
    def test_asset_new_fields(self, db_session, test_episode):
        """Test Asset has new fields."""
        asset = Asset(
            episode_id=test_episode.id,
            organization_id=test_episode.organization_id,
            asset_type=AssetType.SCRIPT,
            filename="script.txt",
            storage_provider="local",
            storage_key=f"org_{test_episode.organization_id}/ep_{test_episode.id}/script.txt",
            storage_url="file:///tmp/script.txt",
            metadata={"stage": "script", "word_count": 500}
        )
        
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        
        assert asset.storage_key is not None
        assert asset.metadata == {"stage": "script", "word_count": 500}
    
    def test_content_job_status_enum(self):
        """Test ContentJobStatus enum values."""
        assert ContentJobStatus.PENDING.value == "pending"
        assert ContentJobStatus.RUNNING.value == "running"
        assert ContentJobStatus.COMPLETED.value == "completed"
        assert ContentJobStatus.FAILED.value == "failed"
        assert ContentJobStatus.RETRYING.value == "retrying"
    
    def test_agent_execution_status_enum(self):
        """Test AgentExecutionStatus enum values."""
        assert AgentExecutionStatus.PENDING.value == "pending"
        assert AgentExecutionStatus.RUNNING.value == "running"
        assert AgentExecutionStatus.SUCCESS.value == "success"
        assert AgentExecutionStatus.FAILED.value == "failed"
        assert AgentExecutionStatus.TIMEOUT.value == "timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
