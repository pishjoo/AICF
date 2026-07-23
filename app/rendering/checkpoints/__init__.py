"""
Rendering Checkpoint System

Checkpoint management for resuming failed rendering jobs.
Supports checkpoint stages and recovery from last successful checkpoint.
"""

import logging
import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class CheckpointStage(str, Enum):
    """Rendering checkpoint stages."""
    
    TIMELINE_COMPLETED = "timeline_completed"
    ASSETS_VALIDATED = "assets_validated"
    COMPOSITION_COMPLETED = "composition_completed"
    AUDIO_COMPLETED = "audio_completed"
    SUBTITLES_COMPLETED = "subtitles_completed"
    FFMPEG_STARTED = "ffmpeg_started"
    RENDER_COMPLETED = "render_completed"
    THUMBNAIL_GENERATED = "thumbnail_generated"
    OUTPUT_STORED = "output_stored"
    QUALITY_EVALUATED = "quality_evaluated"


@dataclass
class RenderCheckpoint:
    """Represents a single checkpoint in the rendering process."""
    
    job_id: str
    stage: CheckpointStage
    created_at: float
    completed_at: Optional[float] = None
    status: str = "pending"  # pending, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)  # File paths produced
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "stage": self.stage.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "artifacts": self.artifacts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RenderCheckpoint":
        return cls(
            job_id=data["job_id"],
            stage=CheckpointStage(data["stage"]),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message"),
            artifacts=data.get("artifacts", {})
        )


@dataclass
class JobCheckpointState:
    """Complete checkpoint state for a rendering job."""
    
    job_id: str
    organization_id: str
    checkpoints: List[RenderCheckpoint] = field(default_factory=list)
    current_stage: Optional[CheckpointStage] = None
    started_at: Optional[float] = None
    last_updated: float = field(default_factory=lambda: time.time())
    can_resume: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "organization_id": self.organization_id,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "current_stage": self.current_stage.value if self.current_stage else None,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
            "can_resume": self.can_resume
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobCheckpointState":
        checkpoints = [
            RenderCheckpoint.from_dict(cp) 
            for cp in data.get("checkpoints", [])
        ]
        current_stage = None
        if data.get("current_stage"):
            current_stage = CheckpointStage(data["current_stage"])
        
        return cls(
            job_id=data["job_id"],
            organization_id=data["organization_id"],
            checkpoints=checkpoints,
            current_stage=current_stage,
            started_at=data.get("started_at"),
            last_updated=data.get("last_updated", time.time()),
            can_resume=data.get("can_resume", True)
        )


class RenderCheckpointManager:
    """
    Manages checkpoints for rendering jobs.
    
    Supports:
    - Creating checkpoints at each stage
    - Retrieving last successful checkpoint
    - Resuming from checkpoint
    - Cleaning up old checkpoints
    """
    
    # In-memory storage (should be replaced with Redis/DB in production)
    _checkpoint_store: Dict[str, JobCheckpointState] = {}
    
    def __init__(self, storage_backend: Optional[Any] = None):
        self.logger = logging.getLogger("rendering.checkpoints.manager")
        self.storage = storage_backend  # Could be Redis, database, etc.
    
    def create_job_state(
        self,
        job_id: str,
        organization_id: str
    ) -> JobCheckpointState:
        """Create initial checkpoint state for a new job."""
        now = time.time()
        
        state = JobCheckpointState(
            job_id=job_id,
            organization_id=organization_id,
            started_at=now,
            last_updated=now
        )
        
        self._checkpoint_store[job_id] = state
        self.logger.info(f"Created checkpoint state for job {job_id}")
        
        return state
    
    def record_checkpoint(
        self,
        job_id: str,
        stage: CheckpointStage,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, str]] = None,
        error_message: Optional[str] = None
    ) -> Optional[RenderCheckpoint]:
        """
        Record a checkpoint at a specific stage.
        
        Args:
            job_id: Rendering job ID
            stage: Checkpoint stage
            status: Checkpoint status (pending, completed, failed)
            metadata: Additional metadata about the checkpoint
            artifacts: Dictionary of artifact names to file paths
            error_message: Error message if checkpoint failed
            
        Returns:
            Created checkpoint or None if job state not found
        """
        if job_id not in self._checkpoint_store:
            self.logger.warning(f"Cannot record checkpoint for unknown job {job_id}")
            return None
        
        state = self._checkpoint_store[job_id]
        now = time.time()
        
        checkpoint = RenderCheckpoint(
            job_id=job_id,
            stage=stage,
            created_at=now,
            completed_at=now if status == "completed" else None,
            status=status,
            metadata=metadata or {},
            artifacts=artifacts or {},
            error_message=error_message
        )
        
        # Add to checkpoints list
        state.checkpoints.append(checkpoint)
        
        # Update current stage
        if status == "completed":
            state.current_stage = stage
        
        state.last_updated = now
        
        # Check if this is a failure that prevents resumption
        if status == "failed":
            # Determine if this failure is recoverable
            recoverable_stages = {
                CheckpointStage.TIMELINE_COMPLETED,
                CheckpointStage.ASSETS_VALIDATED,
                CheckpointStage.COMPOSITION_COMPLETED,
                CheckpointStage.AUDIO_COMPLETED,
                CheckpointStage.SUBTITLES_COMPLETED,
            }
            state.can_resume = stage in recoverable_stages
        
        self.logger.info(
            f"Recorded checkpoint {stage.value} for job {job_id}: {status}"
        )
        
        return checkpoint
    
    def get_job_state(self, job_id: str) -> Optional[JobCheckpointState]:
        """Get checkpoint state for a job."""
        return self._checkpoint_store.get(job_id)
    
    def get_last_successful_checkpoint(
        self,
        job_id: str
    ) -> Optional[RenderCheckpoint]:
        """
        Get the last successfully completed checkpoint for a job.
        
        Returns:
            Last successful checkpoint or None if none found
        """
        state = self.get_job_state(job_id)
        if not state:
            return None
        
        # Find last completed checkpoint
        for checkpoint in reversed(state.checkpoints):
            if checkpoint.status == "completed":
                return checkpoint
        
        return None
    
    def get_checkpoint_for_stage(
        self,
        job_id: str,
        stage: CheckpointStage
    ) -> Optional[RenderCheckpoint]:
        """Get checkpoint for a specific stage."""
        state = self.get_job_state(job_id)
        if not state:
            return None
        
        for checkpoint in state.checkpoints:
            if checkpoint.stage == stage:
                return checkpoint
        
        return None
    
    def can_resume_from_checkpoint(self, job_id: str) -> bool:
        """Check if a job can be resumed from its last checkpoint."""
        state = self.get_job_state(job_id)
        if not state:
            return False
        
        return state.can_resume and state.current_stage is not None
    
    def get_resume_stage(self, job_id: str) -> Optional[CheckpointStage]:
        """
        Get the stage to resume from.
        
        Returns the stage after the last successful checkpoint.
        """
        if not self.can_resume_from_checkpoint(job_id):
            return None
        
        state = self._checkpoint_store[job_id]
        last_checkpoint = self.get_last_successful_checkpoint(job_id)
        
        if not last_checkpoint:
            return None
        
        # Define stage order
        stage_order = list(CheckpointStage)
        current_idx = stage_order.index(last_checkpoint.stage)
        
        # Return next stage
        if current_idx + 1 < len(stage_order):
            return stage_order[current_idx + 1]
        
        return None
    
    def get_all_checkpoints(self, job_id: str) -> List[RenderCheckpoint]:
        """Get all checkpoints for a job."""
        state = self.get_job_state(job_id)
        if not state:
            return []
        
        return state.checkpoints
    
    def get_progress_percentage(self, job_id: str) -> float:
        """
        Calculate rendering progress percentage based on checkpoints.
        
        Returns:
            Progress as percentage (0-100)
        """
        state = self.get_job_state(job_id)
        if not state or not state.checkpoints:
            return 0.0
        
        # Define stage weights (some stages take longer than others)
        stage_weights = {
            CheckpointStage.TIMELINE_COMPLETED: 5,
            CheckpointStage.ASSETS_VALIDATED: 5,
            CheckpointStage.COMPOSITION_COMPLETED: 20,
            CheckpointStage.AUDIO_COMPLETED: 15,
            CheckpointStage.SUBTITLES_COMPLETED: 10,
            CheckpointStage.FFMPEG_STARTED: 5,
            CheckpointStage.RENDER_COMPLETED: 30,
            CheckpointStage.THUMBNAIL_GENERATED: 5,
            CheckpointStage.OUTPUT_STORED: 3,
            CheckpointStage.QUALITY_EVALUATED: 2,
        }
        
        total_weight = sum(stage_weights.values())
        completed_weight = 0
        
        completed_stages = {
            cp.stage for cp in state.checkpoints 
            if cp.status == "completed"
        }
        
        for stage, weight in stage_weights.items():
            if stage in completed_stages:
                completed_weight += weight
        
        return (completed_weight / total_weight) * 100
    
    def cleanup_old_checkpoints(
        self,
        max_age_hours: int = 24,
        organization_id: Optional[str] = None
    ) -> int:
        """
        Clean up old checkpoint data.
        
        Args:
            max_age_hours: Maximum age of checkpoints to keep
            organization_id: Optional filter by organization
            
        Returns:
            Number of checkpoint states cleaned up
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned = 0
        
        jobs_to_remove = []
        
        for job_id, state in self._checkpoint_store.items():
            # Filter by organization if specified
            if organization_id and state.organization_id != organization_id:
                continue
            
            # Check if state is old enough to clean up
            if state.last_updated and (now - state.last_updated) > max_age_seconds:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._checkpoint_store[job_id]
            cleaned += 1
            self.logger.info(f"Cleaned up old checkpoint state for job {job_id}")
        
        return cleaned
    
    def export_checkpoint_state(self, job_id: str) -> Optional[str]:
        """Export checkpoint state as JSON string."""
        state = self.get_job_state(job_id)
        if not state:
            return None
        
        return json.dumps(state.to_dict(), indent=2)
    
    def import_checkpoint_state(self, json_data: str) -> Optional[JobCheckpointState]:
        """Import checkpoint state from JSON string."""
        try:
            data = json.loads(json_data)
            state = JobCheckpointState.from_dict(data)
            self._checkpoint_store[state.job_id] = state
            self.logger.info(f"Imported checkpoint state for job {state.job_id}")
            return state
        except Exception as e:
            self.logger.error(f"Failed to import checkpoint state: {e}")
            return None


# Singleton instance
_checkpoint_manager: Optional[RenderCheckpointManager] = None


def get_checkpoint_manager() -> RenderCheckpointManager:
    """Get or create the checkpoint manager singleton."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = RenderCheckpointManager()
    return _checkpoint_manager
