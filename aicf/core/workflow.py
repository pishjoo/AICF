"""
Workflow Engine

Orchestrates the multi-stage workflow for content production.
Manages agent execution, stage transitions, and error handling.
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime
import logging
import time

from sqlalchemy.orm import Session

from database.models import (
    Project, 
    WorkflowStage, 
    WorkflowStatus, 
    WorkflowStageType,
    ContentProfile
)
from agents.base import BaseAgent, AgentContext, AgentResult


# Stage order definition
STAGE_ORDER = [
    WorkflowStageType.IDEA,
    WorkflowStageType.RESEARCH,
    WorkflowStageType.SCRIPT,
    WorkflowStageType.STORYBOARD,
    WorkflowStageType.ASSETS,
    WorkflowStageType.VIDEO,
    WorkflowStageType.SEO,
    WorkflowStageType.PUBLISH
]


class WorkflowEngine:
    """
    Workflow engine for orchestrating content production.
    
    Manages the execution of agents through all workflow stages,
    handles errors, and tracks progress.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the workflow engine.
        
        Args:
            db: Database session.
        """
        self.db = db
        self.logger = logging.getLogger("workflow")
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, stage_type: str, agent: BaseAgent) -> None:
        """
        Register an agent for a specific stage.
        
        Args:
            stage_type: The workflow stage type (e.g., "idea", "script").
            agent: The agent instance to handle this stage.
        """
        self.agents[stage_type] = agent
        self.logger.info(f"Registered agent '{agent.name}' for stage '{stage_type}'")
    
    def create_workflow(self, project: Project) -> List[WorkflowStage]:
        """
        Create workflow stages for a project.
        
        Args:
            project: The project to create workflow for.
        
        Returns:
            List of created workflow stage records.
        """
        stages = []
        
        for idx, stage_type in enumerate(STAGE_ORDER):
            stage = WorkflowStage(
                project_id=project.id,
                stage_type=stage_type,
                stage_order=idx,
                status=WorkflowStatus.PENDING,
                agent_name=self.agents.get(stage_type.value, {}).name if stage_type.value in self.agents else None
            )
            stages.append(stage)
            self.db.add(stage)
        
        self.db.commit()
        
        self.logger.info(f"Created {len(stages)} workflow stages for project {project.id}")
        return stages
    
    def execute_stage(
        self, 
        project: Project, 
        stage_type: WorkflowStageType,
        custom_instructions: Optional[str] = None
    ) -> AgentResult:
        """
        Execute a specific workflow stage.
        
        Args:
            project: The project being processed.
            stage_type: The stage to execute.
            custom_instructions: Optional custom instructions for the agent.
        
        Returns:
            AgentResult from the agent execution.
        
        Raises:
            ValueError: If no agent is registered for this stage.
        """
        stage_type_str = stage_type.value
        
        # Get the agent for this stage
        agent = self.agents.get(stage_type_str)
        if not agent:
            raise ValueError(f"No agent registered for stage: {stage_type_str}")
        
        # Get or create the workflow stage record
        stage = self.db.query(WorkflowStage).filter(
            WorkflowStage.project_id == project.id,
            WorkflowStage.stage_type == stage_type
        ).first()
        
        if not stage:
            # Create the stage if it doesn't exist
            stage_order = STAGE_ORDER.index(stage_type)
            stage = WorkflowStage(
                project_id=project.id,
                stage_type=stage_type,
                stage_order=stage_order,
                status=WorkflowStatus.PENDING,
                agent_name=agent.name
            )
            self.db.add(stage)
            self.db.commit()
            self.db.refresh(stage)
        
        # Update stage status
        stage.status = WorkflowStatus.IN_PROGRESS
        stage.started_at = datetime.utcnow()
        stage.agent_name = agent.name
        self.db.commit()
        
        # Get content profile
        profile = self.db.query(ContentProfile).filter(
            ContentProfile.id == project.profile_id
        ).first()
        
        if not profile:
            raise ValueError(f"Content profile not found for project {project.id}")
        
        # Gather previous outputs
        previous_outputs = self._gather_previous_outputs(project)
        
        # Build agent context
        context = AgentContext(
            project=project,
            profile=profile,
            previous_outputs=previous_outputs,
            custom_instructions=custom_instructions
        )
        
        self.logger.info(f"Executing stage '{stage_type_str}' for project {project.id}")
        
        # Execute the agent
        start_time = time.time()
        try:
            result = agent.execute(context)
            result.execution_time_seconds = time.time() - start_time
            
            # Save result to stage
            agent.save_result_to_stage(self.db, stage, result)
            
            # Update project if successful
            if result.success:
                self._store_output_in_project(project, stage_type_str, result.output)
                agent.update_project_stage(self.db, project)
            
            self.logger.info(
                f"Stage '{stage_type_str}' completed: {'success' if result.success else 'failed'}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Stage '{stage_type_str}' failed with error: {str(e)}")
            stage.status = WorkflowStatus.FAILED
            stage.error_message = str(e)
            stage.completed_at = datetime.utcnow()
            self.db.commit()
            
            return AgentResult(
                success=False,
                output={},
                error_message=str(e),
                execution_time_seconds=time.time() - start_time
            )
    
    def execute_full_workflow(
        self, 
        project: Project,
        stop_at_stage: Optional[WorkflowStageType] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, AgentResult]:
        """
        Execute the full workflow from current stage to completion.
        
        Args:
            project: The project to process.
            stop_at_stage: Optional stage to stop at (for partial execution).
            custom_instructions: Optional custom instructions for all agents.
        
        Returns:
            Dictionary mapping stage types to their results.
        """
        results = {}
        current_stage_idx = STAGE_ORDER.index(project.current_stage)
        stop_idx = STAGE_ORDER.index(stop_at_stage) if stop_at_stage else len(STAGE_ORDER)
        
        self.logger.info(f"Starting full workflow for project {project.id}")
        
        for idx in range(current_stage_idx, stop_idx):
            stage_type = STAGE_ORDER[idx]
            
            result = self.execute_stage(project, stage_type, custom_instructions)
            results[stage_type.value] = result
            
            # Stop if stage failed
            if not result.success:
                self.logger.warning(f"Workflow stopped at stage '{stage_type.value}' due to failure")
                break
            
            # Refresh project to get updated stage
            self.db.refresh(project)
        
        # Mark project as completed if all stages succeeded
        if project.current_stage == WorkflowStageType.PUBLISH:
            project.status = WorkflowStatus.COMPLETED
            project.completed_at = datetime.utcnow()
            self.db.commit()
            self.logger.info(f"Project {project.id} workflow completed successfully")
        
        return results
    
    def _gather_previous_outputs(self, project: Project) -> Dict[str, Any]:
        """Gather outputs from completed stages."""
        outputs = {}
        
        if project.idea:
            outputs["idea"] = project.idea
        
        if project.research_data:
            outputs["research"] = project.research_data
        
        if project.script:
            outputs["script"] = project.script
        
        if project.storyboard:
            outputs["storyboard"] = project.storyboard
        
        if project.assets:
            outputs["assets"] = project.assets
        
        if project.seo_data:
            outputs["seo"] = project.seo_data
        
        return outputs
    
    def _store_output_in_project(
        self, 
        project: Project, 
        stage_type: str, 
        output: Dict[str, Any]
    ) -> None:
        """Store agent output in the project record."""
        # Map stage types to project fields
        field_map = {
            "idea": ("idea", output.get("idea")),
            "research": ("research_data", output.get("research")),
            "script": ("script", output.get("script")),
            "storyboard": ("storyboard", output.get("storyboard")),
            "assets": ("assets", output.get("assets")),
            "seo": ("seo_data", output.get("seo"))
        }
        
        if stage_type in field_map:
            field_name, value = field_map[stage_type]
            if value is not None:
                setattr(project, field_name, value)
                self.db.add(project)
                self.db.commit()
    
    def get_workflow_status(self, project: Project) -> Dict[str, Any]:
        """
        Get detailed workflow status for a project.
        
        Args:
            project: The project to get status for.
        
        Returns:
            Dictionary with workflow status information.
        """
        stages = self.db.query(WorkflowStage).filter(
            WorkflowStage.project_id == project.id
        ).order_by(WorkflowStage.stage_order).all()
        
        stage_statuses = []
        for stage in stages:
            stage_statuses.append({
                "stage_type": stage.stage_type.value,
                "status": stage.status.value,
                "agent_name": stage.agent_name,
                "started_at": stage.started_at.isoformat() if stage.started_at else None,
                "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
                "duration_seconds": stage.duration_seconds,
                "error_message": stage.error_message
            })
        
        return {
            "project_id": project.id,
            "project_title": project.title,
            "overall_status": project.status.value,
            "current_stage": project.current_stage.value,
            "stages": stage_statuses
        }
