"""
Media Quality Evaluation Models

Defines quality score models and approval status for media evaluation.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Float, Boolean, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database.connection import Base


class ApprovalStatus(str, enum.Enum):
    """
    Approval status for media assets.
    
    Used in quality evaluation and human approval workflows.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class QualityEvaluationType(str, enum.Enum):
    """Types of quality evaluations."""
    IMAGE = "image"
    VOICE = "voice"
    STORYBOARD = "storyboard"
    VIDEO = "video"


class MediaQualityScore(Base):
    """
    MediaQualityScore model - Stores quality evaluation results for media assets.
    
    Evaluates images, voice, storyboards and other media types with:
    - Quality scores (0-100)
    - Issue tracking
    - Recommendations
    - Approval status
    """
    __tablename__ = "media_quality_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Evaluation type
    evaluation_type = Column(SQLEnum(QualityEvaluationType), nullable=False)
    
    # Scoring
    quality_score = Column(Float, nullable=False)  # 0-100 scale
    prompt_adherence_score = Column(Float, nullable=True)  # For images
    resolution_score = Column(Float, nullable=True)  # For images
    style_consistency_score = Column(Float, nullable=True)  # For images
    duration_score = Column(Float, nullable=True)  # For voice
    audio_quality_score = Column(Float, nullable=True)  # For voice
    pronunciation_score = Column(Float, nullable=True)  # For voice
    completeness_score = Column(Float, nullable=True)  # For storyboards
    consistency_score = Column(Float, nullable=True)  # For storyboards
    
    # Issues found during evaluation
    issues = Column(JSON, default=list)  # List of issue descriptions
    
    # Recommendations for improvement
    recommendations = Column(JSON, default=list)  # List of recommendations
    
    # Approval status
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    
    # Evaluator info
    evaluator_type = Column(String(50), nullable=False)  # automated, human, hybrid
    evaluator_id = Column(Integer, nullable=True)  # User ID if human evaluation
    evaluator_name = Column(String(255), nullable=True)
    
    # Evaluation metadata
    evaluation_criteria = Column(JSON, default=dict)  # Criteria used for evaluation
    evaluation_data = Column(JSON, default=dict)  # Raw evaluation data
    
    # Review info
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    asset = relationship("Asset", back_populates="quality_scores")
    episode = relationship("Episode", back_populates="quality_scores")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_quality_asset', 'asset_id'),
        Index('idx_quality_episode', 'episode_id'),
        Index('idx_quality_org', 'organization_id'),
        Index('idx_quality_type', 'evaluation_type'),
        Index('idx_quality_approval', 'approval_status'),
    )
    
    def __repr__(self):
        return f"<MediaQualityScore(id={self.id}, type='{self.evaluation_type}', score={self.quality_score})>"
