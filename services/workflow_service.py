"""
Workflow Service

Service layer for workflow operations.
Provides high-level methods for workflow management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from database.models import Episode, ChannelProfile, ContentJob, AgentExecution
from core.workflow import WorkflowEngineV2, WorkflowStageType, WorkflowContext
from agents.registry import AgentRegistry, get_registry


class WorkflowService:
    """
    Service for managing AI content production workflows.
    
    Provides:
    - create_workflow(): Initialize workflow for an episode
    - start_workflow(): Begin workflow execution
    - get_workflow_status(): Get detailed status
    - retry_failed_stage(): Retry a failed stage
    """
    
    def __init__(self, db: Session, registry: Optional[AgentRegistry] = None):
        """
        Initialize the workflow service.
        
        Args:
            db: Database session with tenant scope.
            registry: Optional agent registry. Uses default if None.
        """
        self.db = db
        self.registry = registry or get_registry()
        self.logger = logging.getLogger("workflow_service")
        self._engine: Optional[WorkflowEngineV2] = None
    
    @property
    def engine(self) -> WorkflowEngineV2:
        """Get or create the workflow engine."""
        if self._engine is None:
            self._engine = WorkflowEngineV2(self.db)
            # Register all agents from registry
            for stage_type, agent in self.registry.get_all_agents().items():
                self._engine.register_agent(WorkflowStageType(stage_type), agent)
        return self._engine
    
    def create_workflow(
        self,
        episode_id: int,
        organization_id: int,
        auto_start: bool = False
    ) -> Dict[str, Any]:
        """
        Create a workflow for an episode.
        
        Args:
            episode_id: ID of the episode to process.
            organization_id: Tenant organization ID.
            auto_start: If True, automatically start the first stage.
            
        Returns:
            Dictionary with workflow details including job IDs.
            
        Raises:
            ValueError: If episode not found or invalid.
        """
        # Get episode with tenant isolation
        episode = self.db.query(Episode).filter(
            Episode.id == episode_id,
            Episode.organization_id == organization_id
        ).first()
        
        if not episode:
            raise ValueError(f"Episode {episode_id} not found for organization {organization_id}")
        
        # Validate channel profile exists
        channel_profile = self.db.query(ChannelProfile).filter(
            ChannelProfile.id == episode.channel_profile_id,
            ChannelProfile.organization_id == organization_id
        ).first()
        
        if not channel_profile:
            raise ValueError(
                f"Channel profile {episode.channel_profile_id} not found "
                f"for organization {organization_id}"
            )
        
        # Check if workflow already exists
        existing_job = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode_id,
            ContentJob.job_type == "workflow"
        ).first()
        
        if existing_job:
            self.logger.info(f"Workflow already exists for episode {episode_id}")
            return {
                "workflow_id": existing_job.id,
                "episode_id": episode_id,
                "status": existing_job.status.value,
                "created_at": existing_job.created_at.isoformat() if existing_job.created_at else None,
                "already_exists": True
            }
        
        # Create workflow using engine
        workflow_job = self.engine.start_episode_workflow(episode, auto_start=auto_start)
        
        self.logger.info(f"Created workflow {workflow_job.id} for episode {episode_id}")
        
        return {
            "workflow_id": workflow_job.id,
            "episode_id": episode_id,
            "status": workflow_job.status.value,
            "stages_created": len(WorkflowStageType.get_stage_order()),
            "created_at": workflow_job.created_at.isoformat() if workflow_job.created_at else None,
            "already_exists": False
        }
    
    def start_workflow(
        self,
        episode_id: int,
        organization_id: int,
        stage_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start or resume workflow execution.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            stage_type: Optional specific stage to start from.
            
        Returns:
            Execution result dictionary.
        """
        episode = self._get_episode(episode_id, organization_id)
        
        if stage_type:
            stage = WorkflowStageType(stage_type)
            return self.engine.execute_stage(episode, stage)
        else:
            # Start from first incomplete stage
            pending_job = self.db.query(ContentJob).filter(
                ContentJob.episode_id == episode_id,
                ContentJob.status.in_(["pending", "retrying"]),
                ContentJob.job_type == "stage"
            ).order_by(ContentJob.stage_order).first()
            
            if not pending_job:
                return {"success": False, "error_message": "No pending stages found"}
            
            stage = WorkflowStageType(pending_job.stage_type)
            return self.engine.execute_stage(episode, stage)
    
    def get_workflow_status(
        self,
        episode_id: int,
        organization_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed workflow status.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            
        Returns:
            Comprehensive status dictionary.
        """
        episode = self._get_episode(episode_id, organization_id)
        return self.engine.get_status(episode)
    
    def retry_failed_stage(
        self,
        episode_id: int,
        organization_id: int,
        stage_type: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Retry a failed workflow stage.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            stage_type: Type of stage to retry.
            max_retries: Maximum retry attempts.
            
        Returns:
            Retry result dictionary.
        """
        episode = self._get_episode(episode_id, organization_id)
        stage = WorkflowStageType(stage_type)
        return self.engine.retry_stage(episode, stage, max_retries)
    
    def pause_workflow(
        self,
        episode_id: int,
        organization_id: int
    ) -> bool:
        """
        Pause workflow execution.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            
        Returns:
            True if successfully paused.
        """
        episode = self._get_episode(episode_id, organization_id)
        return self.engine.pause_workflow(episode)
    
    def resume_workflow(
        self,
        episode_id: int,
        organization_id: int
    ) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            
        Returns:
            True if successfully resumed.
        """
        episode = self._get_episode(episode_id, organization_id)
        return self.engine.resume_workflow(episode)
    
    def get_execution_history(
        self,
        episode_id: int,
        organization_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for an episode.
        
        Args:
            episode_id: ID of the episode.
            organization_id: Tenant organization ID.
            
        Returns:
            List of execution records.
        """
        executions = self.db.query(AgentExecution).filter(
            AgentExecution.episode_id == episode_id,
            AgentExecution.organization_id == organization_id
        ).order_by(AgentExecution.created_at).all()
        
        return [
            {
                "id": ex.id,
                "agent_name": ex.agent_name,
                "agent_type": ex.agent_type,
                "status": ex.status.value,
                "started_at": ex.started_at.isoformat() if ex.started_at else None,
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                "execution_time": ex.execution_time_seconds,
                "tokens_used": ex.tokens_used,
                "error_message": ex.error_message
            }
            for ex in executions
        ]
    
    def _get_episode(self, episode_id: int, organization_id: int) -> Episode:
        """Get episode with tenant isolation."""
        episode = self.db.query(Episode).filter(
            Episode.id == episode_id,
            Episode.organization_id == organization_id
        ).first()
        
        if not episode:
            raise ValueError(f"Episode {episode_id} not found for organization {organization_id}")
        
        return episode
