"""
Workflow Engine V2

Main workflow orchestration engine for AI content production.
Replaces the deprecated Project/WorkflowStage-based workflow system.

Architecture:
    ChannelProfile -> Playlist -> Episode -> ContentJob -> AgentExecution -> AI Agent Runtime
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import time

from sqlalchemy.orm import Session

from database.models import (
    Episode,
    ChannelProfile,
    Playlist,
    ContentJob,
    ContentJobStatus,
    AgentExecution,
    AgentExecutionStatus,
    Organization
)

from .stages import WorkflowStageType
from .exceptions import (
    WorkflowError,
    StageExecutionError,
    StageNotFoundError,
    WorkflowNotPausedError,
    InvalidStageTransitionError,
    AgentExecutionError,
    WorkflowValidationError
)


class WorkflowContext:
    """
    Workflow execution context.
    
    Contains all information needed for workflow execution including:
    - Episode being processed
    - Channel profile for brand consistency
    - Organization ID for tenant isolation
    - Previous stage outputs for context
    - Settings for customization
    """
    
    def __init__(
        self,
        episode: Episode,
        channel_profile: ChannelProfile,
        organization_id: int,
        previous_outputs: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None
    ):
        self.episode = episode
        self.channel_profile = channel_profile
        self.organization_id = organization_id
        self.previous_outputs = previous_outputs or {}
        self.settings = settings or {}
        
    def add_previous_output(self, stage_type: str, output: Dict[str, Any]) -> None:
        """Add output from a completed stage."""
        self.previous_outputs[stage_type] = output
        
    def get_previous_output(self, stage_type: str) -> Optional[Dict[str, Any]]:
        """Get output from a specific stage."""
        return self.previous_outputs.get(stage_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "episode_id": self.episode.id,
            "episode_title": self.episode.title,
            "channel_profile_id": self.channel_profile.id,
            "channel_name": self.channel_profile.name,
            "organization_id": self.organization_id,
            "previous_outputs": self.previous_outputs,
            "settings": self.settings
        }


class WorkflowEngineV2:
    """
    Workflow Engine V2 for AI content production.
    
    Capabilities:
    - start_episode_workflow(): Initialize and start workflow for an episode
    - execute_stage(): Execute a specific workflow stage
    - retry_stage(): Retry a failed stage
    - pause_workflow(): Pause workflow execution
    - resume_workflow(): Resume a paused workflow
    - get_status(): Get detailed workflow status
    """
    
    # Stage order definition
    STAGE_ORDER = WorkflowStageType.get_stage_order()
    
    def __init__(self, db: Session):
        """
        Initialize the workflow engine.
        
        Args:
            db: Database session with tenant-scoped access.
        """
        self.db = db
        self.logger = logging.getLogger("workflow_v2")
        self.agents: Dict[str, Any] = {}
        
    def register_agent(self, stage_type: WorkflowStageType, agent: Any) -> None:
        """
        Register an agent for a specific stage.
        
        Args:
            stage_type: The workflow stage type.
            agent: Agent instance implementing BaseAgent interface.
        """
        self.agents[stage_type.value] = agent
        self.logger.info(f"Registered agent '{agent.name}' for stage '{stage_type.value}'")
    
    def start_episode_workflow(
        self,
        episode: Episode,
        auto_start: bool = True
    ) -> ContentJob:
        """
        Start workflow for an episode.
        
        Creates ContentJob records for each stage and optionally starts execution.
        
        Args:
            episode: Episode to process.
            auto_start: If True, automatically start the first stage.
            
        Returns:
            The main ContentJob record for this workflow.
            
        Raises:
            WorkflowValidationError: If episode or channel profile is invalid.
        """
        # Validate episode
        if not episode:
            raise WorkflowValidationError("Episode is required")
            
        # Get channel profile
        channel_profile = self.db.query(ChannelProfile).filter(
            ChannelProfile.id == episode.channel_profile_id,
            ChannelProfile.organization_id == episode.organization_id
        ).first()
        
        if not channel_profile:
            raise WorkflowValidationError(
                f"Channel profile not found for episode {episode.id}"
            )
        
        # Check if workflow already exists
        existing_job = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.job_type == "workflow"
        ).first()
        
        if existing_job:
            self.logger.warning(f"Workflow already exists for episode {episode.id}")
            return existing_job
        
        # Create main workflow ContentJob
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        workflow_job = ContentJob(
            episode_id=episode.id,
            organization_id=episode.organization_id,
            job_name=f"Workflow: {episode.title}",
            job_type="workflow",
            status=ContentJobStatus.PENDING,
            extra_data={
                "channel_profile_id": channel_profile.id,
                "channel_name": channel_profile.name,
                "playlist_id": episode.playlist_id,
                "stages": [s.value for s in self.STAGE_ORDER]
            },
            updated_at=now
        )
        
        self.db.add(workflow_job)
        self.db.flush()  # Get the ID
        
        # Create ContentJob for each stage
        for idx, stage_type in enumerate(self.STAGE_ORDER):
            stage_job = ContentJob(
                episode_id=episode.id,
                organization_id=episode.organization_id,
                parent_job_id=workflow_job.id,
                job_name=f"Stage: {stage_type.value}",
                job_type="stage",
                stage_type=stage_type.value,
                stage_order=idx,
                status=ContentJobStatus.PENDING,
                metadata={"stage_index": idx}
            )
            self.db.add(stage_job)
            
            # Create initial AgentExecution record for this stage
            agent_name = self.agents.get(stage_type.value, {}).name if stage_type.value in self.agents else None
            
            agent_execution = AgentExecution(
                episode_id=episode.id,
                organization_id=episode.organization_id,
                content_job_id=stage_job.id,
                agent_name=agent_name or f"agent_{stage_type.value}",
                agent_type=stage_type.value,
                status=AgentExecutionStatus.PENDING,
                input_data={},
                metadata={"stage_order": idx}
            )
            self.db.add(agent_execution)
        
        self.db.commit()
        self.db.refresh(workflow_job)
        
        self.logger.info(f"Created workflow for episode {episode.id} with {len(self.STAGE_ORDER)} stages")
        
        # Auto-start if requested
        if auto_start:
            self.execute_stage(episode, self.STAGE_ORDER[0])
        
        return workflow_job
    
    def execute_stage(
        self,
        episode: Episode,
        stage_type: WorkflowStageType,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific workflow stage.
        
        Creates/updates ContentJob and AgentExecution records.
        
        Args:
            episode: Episode being processed.
            stage_type: Stage to execute.
            custom_instructions: Optional custom instructions for the agent.
            
        Returns:
            Dictionary with execution result including success status and output.
            
        Raises:
            StageNotFoundError: If no job exists for this stage.
            StageExecutionError: If stage execution fails.
        """
        stage_type_str = stage_type.value
        start_time = time.time()
        
        # Get the stage ContentJob
        stage_job = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.stage_type == stage_type_str
        ).first()
        
        if not stage_job:
            raise StageNotFoundError(stage_type_str, episode.id)
        
        # Get or create AgentExecution
        agent_execution = self.db.query(AgentExecution).filter(
            AgentExecution.content_job_id == stage_job.id,
            AgentExecution.agent_type == stage_type_str
        ).first()
        
        if not agent_execution:
            agent_execution = AgentExecution(
                episode_id=episode.id,
                organization_id=episode.organization_id,
                content_job_id=stage_job.id,
                agent_name=self.agents.get(stage_type_str, {}).name if stage_type_str in self.agents else None,
                agent_type=stage_type_str,
                status=AgentExecutionStatus.PENDING,
                input_data={},
                metadata={"stage_order": stage_job.stage_order}
            )
            self.db.add(agent_execution)
            self.db.flush()
        
        # Update statuses
        stage_job.status = ContentJobStatus.RUNNING
        stage_job.started_at = datetime.utcnow()
        agent_execution.status = AgentExecutionStatus.RUNNING
        agent_execution.started_at = datetime.utcnow()
        self.db.commit()
        
        # Get channel profile
        channel_profile = self.db.query(ChannelProfile).filter(
            ChannelProfile.id == episode.channel_profile_id
        ).first()
        
        if not channel_profile:
            raise StageExecutionError(
                f"Channel profile not found for episode {episode.id}",
                stage_type_str
            )
        
        # Gather previous outputs from completed stages
        previous_outputs = self._gather_previous_outputs(episode)
        
        # Build workflow context
        context = WorkflowContext(
            episode=episode,
            channel_profile=channel_profile,
            organization_id=episode.organization_id,
            previous_outputs=previous_outputs,
            settings={"custom_instructions": custom_instructions} if custom_instructions else {}
        )
        
        self.logger.info(f"Executing stage '{stage_type_str}' for episode {episode.id}")
        
        # Get the agent for this stage
        agent = self.agents.get(stage_type_str)
        if not agent:
            error_msg = f"No agent registered for stage: {stage_type_str}"
            self._mark_stage_failed(stage_job, agent_execution, error_msg, start_time)
            raise StageExecutionError(error_msg, stage_type_str)
        
        # Execute the agent
        try:
            # Validate input
            if not agent.validate_input(context):
                raise WorkflowValidationError("Agent input validation failed")
            
            # Execute agent
            result = agent.execute(context)
            
            # Validate output
            if not agent.validate_output(result.output):
                raise WorkflowValidationError("Agent output validation failed")
            
            execution_time = time.time() - start_time
            
            # Update agent execution record
            agent_execution.status = AgentExecutionStatus.SUCCESS if result.success else AgentExecutionStatus.FAILED
            agent_execution.completed_at = datetime.utcnow()
            agent_execution.output_data = result.output
            agent_execution.error_message = result.error_message
            agent_execution.execution_time_seconds = execution_time
            agent_execution.tokens_used = getattr(result, 'tokens_used', 0)
            
            # Update stage job
            stage_job.status = ContentJobStatus.COMPLETED if result.success else ContentJobStatus.FAILED
            stage_job.completed_at = datetime.utcnow()
            stage_job.output_data = result.output
            
            self.db.commit()
            
            # Store output in context for next stages
            if result.success:
                context.add_previous_output(stage_type_str, result.output)
            
            self.logger.info(
                f"Stage '{stage_type_str}' completed: {'success' if result.success else 'failed'} "
                f"in {execution_time:.2f}s"
            )
            
            return {
                "success": result.success,
                "stage_type": stage_type_str,
                "output": result.output,
                "error_message": result.error_message,
                "execution_time": execution_time
            }
            
        except Exception as e:
            self.logger.error(f"Stage '{stage_type_str}' failed with error: {str(e)}")
            self._mark_stage_failed(stage_job, agent_execution, str(e), start_time)
            
            return {
                "success": False,
                "stage_type": stage_type_str,
                "error_message": str(e),
                "execution_time": time.time() - start_time
            }
    
    def retry_stage(
        self,
        episode: Episode,
        stage_type: WorkflowStageType,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Retry a failed stage.
        
        Args:
            episode: Episode being processed.
            stage_type: Stage to retry.
            max_retries: Maximum number of retry attempts.
            
        Returns:
            Execution result dictionary.
            
        Raises:
            StageNotFoundError: If stage is not found.
        """
        stage_type_str = stage_type.value
        
        # Get the stage ContentJob
        stage_job = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.stage_type == stage_type_str
        ).first()
        
        if not stage_job:
            raise StageNotFoundError(stage_type_str, episode.id)
        
        # Check current status
        if stage_job.status != ContentJobStatus.FAILED:
            self.logger.warning(f"Stage '{stage_type_str}' is not in FAILED status")
        
        # Check retry count
        retry_count = stage_job.metadata.get("retry_count", 0)
        if retry_count >= max_retries:
            error_msg = f"Max retries ({max_retries}) exceeded for stage '{stage_type_str}'"
            return {
                "success": False,
                "error_message": error_msg,
                "retry_count": retry_count
            }
        
        # Reset stage status
        stage_job.status = ContentJobStatus.RETRYING
        stage_job.metadata["retry_count"] = retry_count + 1
        self.db.commit()
        
        self.logger.info(f"Retrying stage '{stage_type_str}' (attempt {retry_count + 1}/{max_retries})")
        
        # Execute the stage
        return self.execute_stage(episode, stage_type)
    
    def pause_workflow(self, episode: Episode) -> bool:
        """
        Pause workflow execution.
        
        Args:
            episode: Episode whose workflow to pause.
            
        Returns:
            True if successfully paused.
        """
        # Find running jobs
        running_jobs = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.status == ContentJobStatus.RUNNING
        ).all()
        
        for job in running_jobs:
            job.status = ContentJobStatus.PENDING  # Use PENDING as paused state
            self.db.add(job)
        
        # Update running agent executions
        running_executions = self.db.query(AgentExecution).filter(
            AgentExecution.episode_id == episode.id,
            AgentExecution.status == AgentExecutionStatus.RUNNING
        ).all()
        
        for execution in running_executions:
            execution.status = AgentExecutionStatus.PENDING
            self.db.add(execution)
        
        self.db.commit()
        
        self.logger.info(f"Paused workflow for episode {episode.id}")
        return True
    
    def resume_workflow(self, episode: Episode) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            episode: Episode whose workflow to resume.
            
        Returns:
            True if successfully resumed.
            
        Raises:
            WorkflowNotPausedError: If workflow is not paused.
        """
        # Find paused jobs
        paused_jobs = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.status == ContentJobStatus.PENDING
        ).all()
        
        if not paused_jobs:
            raise WorkflowNotPausedError(episode.id)
        
        # Find the first incomplete stage
        for job in sorted(paused_jobs, key=lambda j: j.stage_order or 0):
            if job.status == ContentJobStatus.PENDING:
                stage_type = WorkflowStageType(job.stage_type)
                self.execute_stage(episode, stage_type)
                break
        
        self.logger.info(f"Resumed workflow for episode {episode.id}")
        return True
    
    def get_status(self, episode: Episode) -> Dict[str, Any]:
        """
        Get detailed workflow status for an episode.
        
        Args:
            episode: Episode to get status for.
            
        Returns:
            Dictionary with comprehensive workflow status.
        """
        # Get all ContentJobs for this episode
        content_jobs = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id
        ).order_by(ContentJob.stage_order).all()
        
        # Get all AgentExecutions
        agent_executions = self.db.query(AgentExecution).filter(
            AgentExecution.episode_id == episode.id
        ).order_by(AgentExecution.created_at).all()
        
        # Build stage statuses
        stage_statuses = []
        for job in content_jobs:
            if job.job_type == "stage":
                stage_executions = [
                    {
                        "id": ex.id,
                        "agent_name": ex.agent_name,
                        "status": ex.status.value,
                        "started_at": ex.started_at.isoformat() if ex.started_at else None,
                        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                        "execution_time": ex.execution_time_seconds,
                        "error_message": ex.error_message,
                        "tokens_used": ex.tokens_used
                    }
                    for ex in agent_executions if ex.content_job_id == job.id
                ]
                
                stage_statuses.append({
                    "stage_type": job.stage_type,
                    "stage_order": job.stage_order,
                    "job_id": job.id,
                    "status": job.status.value,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "retry_count": job.metadata.get("retry_count", 0),
                    "executions": stage_executions
                })
        
        # Determine overall status
        overall_status = ContentJobStatus.PENDING
        if any(s["status"] == ContentJobStatus.FAILED.value for s in stage_statuses):
            overall_status = ContentJobStatus.FAILED
        elif all(s["status"] == ContentJobStatus.COMPLETED.value for s in stage_statuses):
            overall_status = ContentJobStatus.COMPLETED
        elif any(s["status"] == ContentJobStatus.RUNNING.value for s in stage_statuses):
            overall_status = ContentJobStatus.RUNNING
        
        return {
            "episode_id": episode.id,
            "episode_title": episode.title,
            "overall_status": overall_status.value,
            "total_stages": len(stage_statuses),
            "completed_stages": sum(1 for s in stage_statuses if s["status"] == ContentJobStatus.COMPLETED.value),
            "stages": stage_statuses
        }
    
    def _gather_previous_outputs(self, episode: Episode) -> Dict[str, Any]:
        """Gather outputs from completed stages."""
        outputs = {}
        
        completed_jobs = self.db.query(ContentJob).filter(
            ContentJob.episode_id == episode.id,
            ContentJob.status == ContentJobStatus.COMPLETED,
            ContentJob.job_type == "stage"
        ).order_by(ContentJob.stage_order).all()
        
        for job in completed_jobs:
            if job.output_data:
                outputs[job.stage_type] = job.output_data
        
        return outputs
    
    def _mark_stage_failed(
        self,
        stage_job: ContentJob,
        agent_execution: AgentExecution,
        error_message: str,
        start_time: float
    ) -> None:
        """Mark a stage and its agent execution as failed."""
        stage_job.status = ContentJobStatus.FAILED
        stage_job.completed_at = datetime.utcnow()
        stage_job.error_message = error_message
        
        agent_execution.status = AgentExecutionStatus.FAILED
        agent_execution.completed_at = datetime.utcnow()
        agent_execution.error_message = error_message
        agent_execution.execution_time_seconds = time.time() - start_time
        
        self.db.add(stage_job)
        self.db.add(agent_execution)
        self.db.commit()
