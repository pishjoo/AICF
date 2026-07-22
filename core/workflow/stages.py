"""
Workflow Stage Definitions

Defines the 8 stages of the AI production workflow.
"""

from enum import Enum


class WorkflowStageType(str, Enum):
    """
    Workflow stage enumeration for AI content production.
    
    Stages are executed in order from IDEA to PUBLISH.
    Each stage creates a ContentJob and one or more AgentExecution records.
    """
    
    IDEA = "idea"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    ASSET_GENERATION = "asset_generation"
    VIDEO_PRODUCTION = "video_production"
    SEO = "seo"
    PUBLISH = "publish"
    
    @classmethod
    def get_stage_order(cls) -> list:
        """Return ordered list of stages."""
        return [
            cls.IDEA,
            cls.RESEARCH,
            cls.SCRIPT,
            cls.STORYBOARD,
            cls.ASSET_GENERATION,
            cls.VIDEO_PRODUCTION,
            cls.SEO,
            cls.PUBLISH
        ]
    
    @classmethod
    def get_stage_index(cls, stage: "WorkflowStageType") -> int:
        """Get the index of a stage in the workflow order."""
        return cls.get_stage_order().index(stage)
    
    @classmethod
    def is_before(cls, stage_a: "WorkflowStageType", stage_b: "WorkflowStageType") -> bool:
        """Check if stage_a comes before stage_b in the workflow."""
        return cls.get_stage_index(stage_a) < cls.get_stage_index(stage_b)
    
    @classmethod
    def is_after(cls, stage_a: "WorkflowStageType", stage_b: "WorkflowStageType") -> bool:
        """Check if stage_a comes after stage_b in the workflow."""
        return cls.get_stage_index(stage_a) > cls.get_stage_index(stage_b)
