"""Tests for checkpoint recovery system."""

import pytest
import time
from app.rendering.checkpoints import (
    RenderCheckpointManager,
    CheckpointStage,
    get_checkpoint_manager,
)


class TestCheckpointManager:
    """Test checkpoint manager functionality."""
    
    def test_create_job_state(self):
        """Test creating checkpoint state for a job."""
        manager = RenderCheckpointManager()
        state = manager.create_job_state("job-123", "org-456")
        
        assert state.job_id == "job-123"
        assert state.organization_id == "org-456"
        assert state.started_at is not None
        assert state.checkpoints == []
    
    def test_record_checkpoint(self):
        """Test recording checkpoints."""
        manager = RenderCheckpointManager()
        manager.create_job_state("job-123", "org-456")
        
        checkpoint = manager.record_checkpoint(
            "job-123",
            CheckpointStage.TIMELINE_COMPLETED,
            status="completed",
            metadata={"scenes": 5}
        )
        
        assert checkpoint is not None
        assert checkpoint.stage == CheckpointStage.TIMELINE_COMPLETED
        assert checkpoint.status == "completed"
    
    def test_get_last_successful_checkpoint(self):
        """Test retrieving last successful checkpoint."""
        manager = RenderCheckpointManager()
        manager.create_job_state("job-123", "org-456")
        
        manager.record_checkpoint("job-123", CheckpointStage.TIMELINE_COMPLETED, status="completed")
        manager.record_checkpoint("job-123", CheckpointStage.ASSETS_VALIDATED, status="completed")
        manager.record_checkpoint("job-123", CheckpointStage.COMPOSITION_COMPLETED, status="failed")
        
        last = manager.get_last_successful_checkpoint("job-123")
        assert last is not None
        assert last.stage == CheckpointStage.ASSETS_VALIDATED
    
    def test_can_resume_from_checkpoint(self):
        """Test resume capability detection."""
        manager = RenderCheckpointManager()
        manager.create_job_state("job-123", "org-456")
        
        # Initially cannot resume (no checkpoints)
        assert not manager.can_resume_from_checkpoint("job-123")
        
        # After completing timeline, can resume
        manager.record_checkpoint("job-123", CheckpointStage.TIMELINE_COMPLETED, status="completed")
        assert manager.can_resume_from_checkpoint("job-123")
    
    def test_get_resume_stage(self):
        """Test getting next stage to resume from."""
        manager = RenderCheckpointManager()
        manager.create_job_state("job-123", "org-456")
        
        manager.record_checkpoint("job-123", CheckpointStage.TIMELINE_COMPLETED, status="completed")
        
        resume_stage = manager.get_resume_stage("job-123")
        assert resume_stage == CheckpointStage.ASSETS_VALIDATED
    
    def test_progress_percentage(self):
        """Test progress calculation."""
        manager = RenderCheckpointManager()
        manager.create_job_state("job-123", "org-456")
        
        # No progress initially
        assert manager.get_progress_percentage("job-123") == 0.0
        
        # Complete some stages
        manager.record_checkpoint("job-123", CheckpointStage.TIMELINE_COMPLETED, status="completed")
        progress = manager.get_progress_percentage("job-123")
        assert progress > 0.0
        assert progress < 100.0
    
    def test_singleton_pattern(self):
        """Test checkpoint manager singleton."""
        manager1 = get_checkpoint_manager()
        manager2 = get_checkpoint_manager()
        assert manager1 is manager2
