"""
Base Agent Interface

Abstract base class defining the interface for all AI agents.
Each agent handles a specific stage in the content production workflow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class AgentContext:
    """
    Context passed to agents during execution.
    
    Contains:
    - episode: The episode being processed
    - channel_profile: Channel identity and brand guidelines
    - organization_id: Tenant ID for isolation
    - previous_outputs: Results from completed stages
    - settings: Configuration options
    """
    episode: Any  # Episode model instance
    channel_profile: Any  # ChannelProfile model instance
    organization_id: int
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_custom_instructions(self) -> Optional[str]:
        """Get custom instructions from settings."""
        return self.settings.get("custom_instructions")


@dataclass
class AgentResult:
    """
    Result returned by agent execution.
    
    Contains:
    - success: Whether execution succeeded
    - output: Agent output data
    - error_message: Error details if failed
    - tokens_used: LLM tokens consumed
    - execution_time_seconds: Time taken
    """
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str] = None
    tokens_used: int = 0
    execution_time_seconds: float = 0.0


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.
    
    Each agent is responsible for one workflow stage.
    Agents must implement:
    - execute(context): Main execution logic
    - validate_input(context): Validate incoming context
    - validate_output(output): Validate result data
    
    Agents should return mock outputs initially.
    External AI APIs are not called yet.
    """
    
    # Agent identification
    name: str = "base_agent"
    description: str = "Base agent class"
    stage_type: str = "unknown"  # Matches WorkflowStageType value
    
    def __init__(self):
        """Initialize the agent."""
        self.logger = logging.getLogger(f"agents.{self.name}")
    
    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's main logic.
        
        Args:
            context: Workflow context with episode, profile, and previous outputs.
            
        Returns:
            AgentResult with success status and output data.
        """
        pass
    
    @abstractmethod
    def validate_input(self, context: AgentContext) -> bool:
        """
        Validate the input context before execution.
        
        Args:
            context: Workflow context to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """
        Validate the agent output after execution.
        
        Args:
            output: Dictionary of output data.
            
        Returns:
            True if valid, False otherwise.
        """
        pass
    
    def _get_brand_context(self, context: AgentContext) -> Dict[str, Any]:
        """Extract brand context from channel profile."""
        profile = context.channel_profile
        return {
            "channel_name": profile.name,
            "niche": getattr(profile, 'niche', None),
            "target_audience": getattr(profile, 'target_audience', None),
            "visual_style": getattr(profile, 'visual_style', None),
            "storytelling_rules": getattr(profile, 'storytelling_rules', []),
            "forbidden_elements": getattr(profile, 'forbidden_elements', []),
            "language": getattr(profile, 'language', 'en'),
            "video_duration": getattr(profile, 'video_duration', 'medium')
        }
    
    def log_execution(self, message: str, level: str = "info"):
        """Log an execution message."""
        log_func = getattr(self.logger, level)
        log_func(f"[{self.name}] {message}")
