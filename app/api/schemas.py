from enum import Enum
"""
Pydantic Schemas for API

Request/response schemas for the FastAPI application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============== Content Profile Schemas ==============

class ContentProfileBase(BaseModel):
    """Base schema for content profile."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    reference_websites: List[str] = Field(default_factory=list)
    visual_style: Optional[str] = None
    image_style_rules: Optional[str] = None
    aspect_ratio: str = "16:9"
    forbidden_elements: List[str] = Field(default_factory=list)
    recurring_characters: List[str] = Field(default_factory=list)
    storytelling_rules: Optional[str] = None
    music_style: Optional[str] = None
    video_duration: Optional[str] = None
    language: str = "English"


class ContentProfileCreate(ContentProfileBase):
    """Schema for creating a content profile."""
    pass


class ContentProfileUpdate(BaseModel):
    """Schema for updating a content profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    hashtags: Optional[List[str]] = None
    reference_websites: Optional[List[str]] = None
    visual_style: Optional[str] = None
    image_style_rules: Optional[str] = None
    aspect_ratio: Optional[str] = None
    forbidden_elements: Optional[List[str]] = None
    recurring_characters: Optional[List[str]] = None
    storytelling_rules: Optional[str] = None
    music_style: Optional[str] = None
    video_duration: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None


class ContentProfileResponse(ContentProfileBase):
    """Schema for content profile response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    
    class Config:
        from_attributes = True


# ============== Project Schemas ==============

class WorkflowStageType(str, Enum):
    """Workflow stage types."""
    IDEA = "idea"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    ASSETS = "assets"
    VIDEO = "video"
    SEO = "seo"
    PUBLISH = "publish"


class WorkflowStatus(str, Enum):
    """Workflow status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectBase(BaseModel):
    """Base schema for project."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    profile_id: int


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: int
    status: WorkflowStatus
    current_stage: WorkflowStageType
    idea: Optional[str] = None
    script: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkflowStageResponse(BaseModel):
    """Schema for workflow stage response."""
    id: int
    project_id: int
    stage_type: WorkflowStageType
    stage_order: int
    status: WorkflowStatus
    agent_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class WorkflowStatusResponse(BaseModel):
    """Schema for workflow status response."""
    project_id: int
    project_title: str
    overall_status: WorkflowStatus
    current_stage: WorkflowStageType
    stages: List[WorkflowStageResponse]


# ============== Agent Execution Schemas ==============

class AgentExecuteRequest(BaseModel):
    """Schema for agent execution request."""
    custom_instructions: Optional[str] = None


class AgentExecuteResponse(BaseModel):
    """Schema for agent execution response."""
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str] = None
    tokens_used: int = 0
    execution_time_seconds: float = 0.0


# ============== Generic Response Schemas ==============

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None

