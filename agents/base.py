"""
Base Agent Class

Abstract base class for all AICF agents.
Defines the common interface and shared functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from core.ai_provider import BaseAIProvider, Message, get_ai_provider
from database.models import ContentProfile, Project, WorkflowStage, WorkflowStatus


@dataclass
class AgentContext:
    """Context information passed to agents."""
    project: Project
    profile: ContentProfile
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    custom_instructions: Optional[str] = None


@dataclass
class AgentResult:
    """Result returned by an agent execution."""
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str] = None
    tokens_used: int = 0
    execution_time_seconds: float = 0.0


class BaseAgent(ABC):
    """
    Abstract base class for all AICF agents.
    
    Each agent is responsible for a specific stage in the workflow.
    Agents use the content profile to ensure on-brand output.
    """
    
    # Agent identification
    name: str = "base_agent"
    description: str = "Base agent class"
    stage_type: str = "unknown"  # Matches WorkflowStageType
    
    def __init__(self, ai_provider: Optional[BaseAIProvider] = None):
        """
        Initialize the agent.
        
        Args:
            ai_provider: AI provider instance. If None, uses default provider.
        """
        self.ai_provider = ai_provider or get_ai_provider()
        self.logger = logging.getLogger(f"agents.{self.name}")
    
    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's main logic.
        
        Args:
            context: Agent context with project and profile information.
        
        Returns:
            AgentResult with success status and output data.
        """
        pass
    
    def build_system_message(self, context: AgentContext) -> Message:
        """
        Build the system message for this agent.
        
        Includes channel identity, rules, and agent-specific instructions.
        """
        profile = context.profile
        
        # Build base context from profile
        profile_context = {
            "channel_name": profile.name,
            "niche": profile.niche,
            "target_audience": profile.target_audience,
            "visual_style": profile.visual_style,
            "storytelling_rules": profile.storytelling_rules,
            "forbidden_elements": profile.forbidden_elements,
            "recurring_characters": profile.recurring_characters,
            "music_style": profile.music_style,
            "video_duration": profile.video_duration,
            "language": profile.language,
        }
        
        # Get base system prompt from AI provider
        system_prompt = self.ai_provider.build_system_prompt(profile_context)
        
        # Add agent-specific instructions
        agent_instructions = self.get_agent_instructions(context)
        if agent_instructions:
            system_prompt += f"\n\n{agent_instructions}"
        
        # Add custom instructions if provided
        if context.custom_instructions:
            system_prompt += f"\n\nCustom Instructions:\n{context.custom_instructions}"
        
        return Message(role="system", content=system_prompt)
    
    def get_agent_instructions(self, context: AgentContext) -> str:
        """
        Get agent-specific instructions.
        
        Override this method in subclasses to provide specific guidance.
        """
        return ""
    
    def build_user_message(self, context: AgentContext) -> Message:
        """
        Build the user message for this agent.
        
        Contains the specific task and relevant data from previous stages.
        """
        task_description = self.get_task_description(context)
        
        # Include relevant previous outputs
        context_data = []
        
        if context.previous_outputs.get("idea"):
            context_data.append(f"Idea: {context.previous_outputs['idea']}")
        
        if context.previous_outputs.get("research"):
            context_data.append(f"Research: {context.previous_outputs['research']}")
        
        if context.previous_outputs.get("script"):
            context_data.append(f"Script: {context.previous_outputs['script']}")
        
        context_str = "\n\n".join(context_data) if context_data else "No previous context."
        
        return Message(
            role="user",
            content=f"{task_description}\n\nPrevious Context:\n{context_str}"
        )
    
    def get_task_description(self, context: AgentContext) -> str:
        """
        Get the task description for this agent.
        
        Override this method in subclasses.
        """
        return f"Execute {self.name} task."
    
    def save_result_to_stage(
        self, 
        db: Session, 
        stage: WorkflowStage, 
        result: AgentResult
    ) -> None:
        """
        Save agent result to the workflow stage record.
        
        Args:
            db: Database session.
            stage: Workflow stage record.
            result: Agent execution result.
        """
        stage.status = WorkflowStatus.COMPLETED if result.success else WorkflowStatus.FAILED
        stage.output_data = result.output
        stage.error_message = result.error_message
        stage.completed_at = datetime.utcnow()
        
        if stage.started_at:
            stage.duration_seconds = (stage.completed_at - stage.started_at).total_seconds()
        
        db.add(stage)
        db.commit()
    
    def update_project_stage(
        self, 
        db: Session, 
        project: Project, 
        next_stage_type: Optional[str] = None
    ) -> None:
        """
        Update project to reflect completion of current stage.
        
        Args:
            db: Database session.
            project: Project record.
            next_stage_type: Next stage type, or None to auto-advance.
        """
        # Store agent output in project
        stage_order_map = {
            "idea": 0,
            "research": 1,
            "script": 2,
            "storyboard": 3,
            "assets": 4,
            "video": 5,
            "seo": 6,
            "publish": 7
        }
        
        current_order = stage_order_map.get(self.stage_type, 0)
        
        # Auto-advance to next stage if not specified
        if next_stage_type is None:
            stage_types = list(stage_order_map.keys())
            if current_order + 1 < len(stage_types):
                next_stage_type = stage_types[current_order + 1]
        
        if next_stage_type:
            from database.models import WorkflowStageType
            try:
                project.current_stage = WorkflowStageType(next_stage_type)
            except ValueError:
                self.logger.warning(f"Invalid stage type: {next_stage_type}")
        
        db.add(project)
        db.commit()
    
    def log_execution(self, message: str, level: str = "info"):
        """Log execution message."""
        log_func = getattr(self.logger, level)
        log_func(f"[{self.name}] {message}")

