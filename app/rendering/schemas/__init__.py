"""
Rendering Schemas

Pydantic schemas for rendering job requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class RenderingJobStatus(str, Enum):
    """Rendering job lifecycle status."""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderingJobCreate(BaseModel):
    """Schema for creating a rendering job."""
    
    name: str = Field(..., description="Job name")
    job_type: str = Field(..., description="Type of rendering job")
    organization_id: int = Field(..., description="Tenant organization ID")
    input_files: List[str] = Field(default_factory=list, description="Input file paths/keys")
    output_format: Optional[str] = Field(None, description="Output format (mp4, webm, etc.)")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Rendering parameters")
    priority: int = Field(default=0, description="Job priority (higher = more urgent)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class RenderingJobUpdate(BaseModel):
    """Schema for updating a rendering job."""
    
    name: Optional[str] = None
    status: Optional[RenderingJobStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class RenderingJobResponse(BaseModel):
    """Schema for rendering job response."""
    
    id: int
    job_id: str  # UUID
    name: str
    job_type: str
    status: RenderingJobStatus
    organization_id: int
    progress: int
    input_files: List[str]
    output_format: Optional[str]
    parameters: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class RenderingJobListResponse(BaseModel):
    """Schema for listing rendering jobs."""
    
    jobs: List[RenderingJobResponse]
    total: int
    page: int
    page_size: int


class VideoCompositionCreate(BaseModel):
    """Schema for creating a video composition."""
    
    name: str = Field(..., description="Composition name")
    organization_id: int = Field(..., description="Tenant organization ID")
    episode_id: Optional[int] = Field(None, description="Associated episode ID")
    clips: List[Dict[str, Any]] = Field(default_factory=list, description="Video clips in composition")
    transitions: List[Dict[str, Any]] = Field(default_factory=list, description="Transitions between clips")
    audio_tracks: List[Dict[str, Any]] = Field(default_factory=list, description="Audio tracks")
    subtitles: List[Dict[str, Any]] = Field(default_factory=list, description="Subtitle tracks")
    resolution: Optional[str] = Field("1920x1080", description="Output resolution")
    fps: Optional[float] = Field(30.0, description="Frames per second")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class VideoCompositionResponse(BaseModel):
    """Schema for video composition response."""
    
    id: int
    composition_id: str  # UUID
    name: str
    organization_id: int
    episode_id: Optional[int]
    status: str
    clips: List[Dict[str, Any]]
    transitions: List[Dict[str, Any]]
    audio_tracks: List[Dict[str, Any]]
    subtitles: List[Dict[str, Any]]
    resolution: str
    fps: float
    duration_seconds: Optional[float]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class RenderOutputCreate(BaseModel):
    """Schema for creating a render output record."""
    
    rendering_job_id: int = Field(..., description="Parent rendering job ID")
    organization_id: int = Field(..., description="Tenant organization ID")
    output_type: str = Field(..., description="Type of output (video, thumbnail, subtitle, etc.)")
    storage_key: str = Field(..., description="Storage key/path")
    storage_url: Optional[str] = Field(None, description="Access URL")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    duration_seconds: Optional[float] = Field(None, description="Duration for video/audio")
    resolution: Optional[str] = Field(None, description="Resolution for video/images")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RenderOutputResponse(BaseModel):
    """Schema for render output response."""
    
    id: int
    output_id: str  # UUID
    rendering_job_id: int
    organization_id: int
    output_type: str
    storage_key: str
    storage_url: Optional[str]
    file_size_bytes: Optional[int]
    duration_seconds: Optional[float]
    resolution: Optional[str]
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    created_at: datetime
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True
