"""
Database Models

SQLAlchemy ORM models for AICF entities.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database.connection import Base


class WorkflowStatus(str, enum.Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStageType(str, enum.Enum):
    """Workflow stage types."""
    IDEA = "idea"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    ASSETS = "assets"
    VIDEO = "video"
    SEO = "seo"
    PUBLISH = "publish"


class ContentProfile(Base):
    """
    Content Profile model.
    
    Defines the identity and rules for a YouTube channel.
    Each profile contains all the information agents need to generate
    on-brand content.
    """
    __tablename__ = "content_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Identity
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    niche = Column(String(255), nullable=True)
    target_audience = Column(Text, nullable=True)
    
    # Branding
    hashtags = Column(JSON, default=list)  # List of default hashtags
    reference_websites = Column(JSON, default=list)  # List of reference URLs
    
    # Visual Identity
    visual_style = Column(Text, nullable=True)  # e.g., "cinematic", "minimalist"
    image_style_rules = Column(Text, nullable=True)  # Specific image generation rules
    aspect_ratio = Column(String(20), default="16:9")  # 16:9, 9:16, 1:1, etc.
    
    # Content Rules
    forbidden_elements = Column(JSON, default=list)  # Elements to avoid
    recurring_characters = Column(JSON, default=list)  # Character descriptions
    storytelling_rules = Column(Text, nullable=True)  # Narrative guidelines
    
    # Audio
    music_style = Column(String(255), nullable=True)  # e.g., "epic orchestral", "lo-fi"
    
    # Video Format
    video_duration = Column(String(50), nullable=True)  # e.g., "30 seconds", "10 minutes"
    language = Column(String(50), default="English")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    projects = relationship("Project", back_populates="content_profile", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ContentProfile(id={self.id}, name='{self.name}')>"


class Project(Base):
    """
    Project model.
    
    Represents a single video production project tied to a content profile.
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Foreign key to content profile
    profile_id = Column(Integer, ForeignKey("content_profiles.id"), nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    current_stage = Column(SQLEnum(WorkflowStageType), default=WorkflowStageType.IDEA)
    
    # Content storage
    idea = Column(Text, nullable=True)
    research_data = Column(JSON, default=dict)
    script = Column(Text, nullable=True)
    storyboard = Column(JSON, default=list)
    assets = Column(JSON, default=list)
    seo_data = Column(JSON, default=dict)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    content_profile = relationship("ContentProfile", back_populates="projects")
    workflow_stages = relationship("WorkflowStage", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, title='{self.title}', status='{self.status}')>"


class WorkflowStage(Base):
    """
    Workflow Stage model.
    
    Tracks the progress of a project through each stage of the workflow.
    Records agent outputs and execution metadata.
    """
    __tablename__ = "workflow_stages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Stage identification
    stage_type = Column(SQLEnum(WorkflowStageType), nullable=False)
    stage_order = Column(Integer, nullable=False)  # Order in workflow (0-7)
    
    # Execution tracking
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    agent_name = Column(String(100), nullable=True)  # Which agent handled this
    
    # Output storage
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="workflow_stages")
    
    def __repr__(self):
        return f"<WorkflowStage(id={self.id}, stage='{self.stage_type}', status='{self.status}')>"
