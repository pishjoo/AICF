"""
Task Definitions

Predefined task types for workflow execution.
Integrates with WorkflowEngineV2 and AgentExecution.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .queue import TaskResult, TaskStatus
from database.models import (
    ContentJob,
    ContentJobStatus,
    AgentExecution,
    AgentExecutionStatus,
    Episode
)
from core.workflow.engine import WorkflowEngineV2
from core.workflow.stages import WorkflowStageType


logger = logging.getLogger("jobs.tasks")


class WorkflowTask:
    """Task definitions for workflow operations."""
    
    @staticmethod
    def create_workflow_task(db_session_factory) -> callable:
        """
        Create a workflow task handler.
        
        Args:
            db_session_factory: Callable that returns a new DB session
        
        Returns:
            Task handler function
        """
        def handler(payload: Dict[str, Any]) -> TaskResult:
            """
            Create and start a workflow for an episode.
            
            Payload expects:
            - episode_id: ID of the episode
            - organization_id: Tenant ID
            - auto_start: Whether to auto-start the first stage
            """
            db = db_session_factory()
            try:
                episode_id = payload.get("episode_id")
                organization_id = payload.get("organization_id")
                auto_start = payload.get("auto_start", False)
                
                if not episode_id:
                    return TaskResult.failure("episode_id is required")
                
                # Get episode
                episode = db.query(Episode).filter(
                    Episode.id == episode_id,
                    Episode.organization_id == organization_id
                ).first()
                
                if not episode:
                    return TaskResult.failure(f"Episode {episode_id} not found")
                
                # Create workflow engine and start workflow
                engine = WorkflowEngineV2(db)
                
                # Register agents from registry
                from agents.registry import AgentRegistry
                registry = AgentRegistry()
                for stage_type in WorkflowStageType:
                    agent = registry.get_agent(stage_type.value)
                    if agent:
                        engine.register_agent(stage_type, agent)
                
                workflow_job = engine.start_episode_workflow(
                    episode=episode,
                    auto_start=auto_start
                )
                
                logger.info(f"Created workflow {workflow_job.id} for episode {episode_id}")
                
                return TaskResult.success({
                    "workflow_job_id": workflow_job.id,
                    "episode_id": episode_id,
                    "status": workflow_job.status.value,
                    "stages_created": len(WorkflowStageType)
                })
                
            except Exception as e:
                logger.exception(f"Workflow creation failed: {e}")
                return TaskResult.failure(str(e))
            finally:
                db.close()
        
        return handler
    
    @staticmethod
    def execute_stage_task(db_session_factory) -> callable:
        """
        Create a stage execution task handler.
        
        Args:
            db_session_factory: Callable that returns a new DB session
        
        Returns:
            Task handler function
        """
        def handler(payload: Dict[str, Any]) -> TaskResult:
            """
            Execute a specific workflow stage.
            
            Payload expects:
            - episode_id: ID of the episode
            - stage_type: Stage type string (e.g., 'idea', 'research')
            - organization_id: Tenant ID
            - custom_instructions: Optional custom instructions
            """
            db = db_session_factory()
            try:
                episode_id = payload.get("episode_id")
                stage_type_str = payload.get("stage_type")
                organization_id = payload.get("organization_id")
                custom_instructions = payload.get("custom_instructions")
                
                if not episode_id or not stage_type_str:
                    return TaskResult.failure("episode_id and stage_type are required")
                
                # Get episode
                episode = db.query(Episode).filter(
                    Episode.id == episode_id,
                    Episode.organization_id == organization_id
                ).first()
                
                if not episode:
                    return TaskResult.failure(f"Episode {episode_id} not found")
                
                # Get stage type
                try:
                    stage_type = WorkflowStageType(stage_type_str)
                except ValueError:
                    return TaskResult.failure(f"Invalid stage type: {stage_type_str}")
                
                # Create workflow engine
                engine = WorkflowEngineV2(db)
                
                # Register agent for this stage
                from agents.registry import AgentRegistry
                registry = AgentRegistry()
                agent = registry.get_agent(stage_type.value)
                if agent:
                    engine.register_agent(stage_type, agent)
                
                # Execute stage
                result = engine.execute_stage(
                    episode=episode,
                    stage_type=stage_type,
                    custom_instructions=custom_instructions
                )
                
                if result.get("success"):
                    return TaskResult.success(result)
                else:
                    return TaskResult.failure(
                        result.get("error_message", "Stage execution failed"),
                        metadata=result
                    )
                
            except Exception as e:
                logger.exception(f"Stage execution failed: {e}")
                return TaskResult.failure(str(e))
            finally:
                db.close()
    
    @staticmethod
    def retry_stage_task(db_session_factory) -> callable:
        """
        Create a stage retry task handler.
        
        Args:
            db_session_factory: Callable that returns a new DB session
        
        Returns:
            Task handler function
        """
        def handler(payload: Dict[str, Any]) -> TaskResult:
            """
            Retry a failed workflow stage.
            
            Payload expects:
            - episode_id: ID of the episode
            - stage_type: Stage type string
            - organization_id: Tenant ID
            - max_retries: Maximum retry attempts
            """
            db = db_session_factory()
            try:
                episode_id = payload.get("episode_id")
                stage_type_str = payload.get("stage_type")
                organization_id = payload.get("organization_id")
                max_retries = payload.get("max_retries", 3)
                
                if not episode_id or not stage_type_str:
                    return TaskResult.failure("episode_id and stage_type are required")
                
                # Get episode
                episode = db.query(Episode).filter(
                    Episode.id == episode_id,
                    Episode.organization_id == organization_id
                ).first()
                
                if not episode:
                    return TaskResult.failure(f"Episode {episode_id} not found")
                
                # Get stage type
                try:
                    stage_type = WorkflowStageType(stage_type_str)
                except ValueError:
                    return TaskResult.failure(f"Invalid stage type: {stage_type_str}")
                
                # Create workflow engine
                engine = WorkflowEngineV2(db)
                
                # Register agent
                from agents.registry import AgentRegistry
                registry = AgentRegistry()
                agent = registry.get_agent(stage_type.value)
                if agent:
                    engine.register_agent(stage_type, agent)
                
                # Retry stage
                result = engine.retry_stage(
                    episode=episode,
                    stage_type=stage_type,
                    max_retries=max_retries
                )
                
                if result.get("success"):
                    return TaskResult.success(result)
                else:
                    return TaskResult.failure(
                        result.get("error_message", "Stage retry failed"),
                        metadata=result
                    )
                
            except Exception as e:
                logger.exception(f"Stage retry failed: {e}")
                return TaskResult.failure(str(e))
            finally:
                db.close()


class StageExecutionTask:
    """Alias for backward compatibility."""
    create_workflow_task = WorkflowTask.create_workflow_task
    execute_stage_task = WorkflowTask.execute_stage_task
    retry_stage_task = WorkflowTask.retry_stage_task
