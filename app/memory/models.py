"""
Memory Foundation Models

This module defines the memory models for AICF v2.
These models store historical data that AI agents can use for context.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, BigInteger, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.connection import Base


class OrganizationMemory(Base):
    """
    Organization-level memory storage.
    
    Stores organization-wide historical data including:
    - Past campaigns and their performance
    - Organizational preferences
    - Long-term goals and strategies
    - Historical metrics
    """
    __tablename__ = "organization_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Memory type categorization
    memory_type = Column(String(50), nullable=False, index=True)  # campaign, preference, strategy, metric
    
    # Memory content
    key = Column(String(255), nullable=False, index=True)  # Unique identifier for this memory
    value = Column(JSON, nullable=False)  # Flexible JSON storage
    
    # Metadata
    importance_score = Column(Integer, default=1)  # 1-10 scale for relevance
    access_count = Column(Integer, default=0)  # How often this memory is accessed
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Expiration (for temporary memories)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_org_mem_org_type', 'organization_id', 'memory_type'),
        Index('idx_org_mem_key', 'organization_id', 'key', unique=True),
    )
    
    def __repr__(self):
        return f"<OrganizationMemory(id={self.id}, org={self.organization_id}, type={self.memory_type}, key={self.key})>"


class ChannelMemory(Base):
    """
    Channel-level memory storage.
    
    Stores channel-specific historical data including:
    - Content performance history
    - Audience engagement patterns
    - Posting schedule effectiveness
    - Platform-specific learnings
    """
    __tablename__ = "channel_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Memory type categorization
    memory_type = Column(String(50), nullable=False, index=True)  # performance, engagement, schedule, learning
    
    # Memory content
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    
    # Metadata
    importance_score = Column(Integer, default=1)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Content reference (optional link to specific content)
    content_id = Column(Integer, nullable=True)  # Reference to episode/playlist
    content_type = Column(String(50), nullable=True)  # episode, playlist, etc.
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    channel = relationship("ChannelProfile")
    
    __table_args__ = (
        Index('idx_chan_mem_org_channel', 'organization_id', 'channel_id'),
        Index('idx_chan_mem_type', 'channel_id', 'memory_type'),
        Index('idx_chan_mem_key', 'channel_id', 'key', unique=True),
    )
    
    def __repr__(self):
        return f"<ChannelMemory(id={self.id}, channel={self.channel_id}, type={self.memory_type})>"


class AudienceMemory(Base):
    """
    Audience-level memory storage.
    
    Stores audience-related historical data including:
    - Demographic changes over time
    - Interest evolution
    - Engagement patterns by segment
    - Feedback and sentiment history
    """
    __tablename__ = "audience_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channel_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Segment identifier (can be null for general audience)
    segment_id = Column(String(100), nullable=True, index=True)
    
    # Memory type
    memory_type = Column(String(50), nullable=False, index=True)  # demographic, interest, behavior, sentiment
    
    # Memory content
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    
    # Metadata
    importance_score = Column(Integer, default=1)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Sample size (for statistical validity)
    sample_size = Column(Integer, nullable=True)
    confidence_score = Column(Integer, default=5)  # 1-10 scale
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    channel = relationship("ChannelProfile")
    
    __table_args__ = (
        Index('idx_aud_mem_org', 'organization_id'),
        Index('idx_aud_mem_segment', 'organization_id', 'segment_id'),
    )
    
    def __repr__(self):
        return f"<AudienceMemory(id={self.id}, segment={self.segment_id}, type={self.memory_type})>"


class ContentMemory(Base):
    """
    Content-level memory storage.
    
    Stores content-specific historical data including:
    - Performance metrics per content piece
    - Generation parameters used
    - AI model performance for specific content types
    - User feedback and revisions
    """
    __tablename__ = "content_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Content reference
    content_type = Column(String(50), nullable=False, index=True)  # episode, script, thumbnail, etc.
    content_id = Column(Integer, nullable=False, index=True)
    
    # Memory type
    memory_type = Column(String(50), nullable=False, index=True)  # performance, generation, feedback, revision
    
    # Memory content
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    
    # AI generation metadata
    agent_type = Column(String(100), nullable=True)  # Which agent generated this
    provider = Column(String(50), nullable=True)  # AI provider used
    model = Column(String(100), nullable=True)  # Model used
    
    # Performance tracking
    performance_score = Column(Integer, nullable=True)  # Normalized 1-100 score
    engagement_metrics = Column(JSON, nullable=True)  # Views, likes, shares, etc.
    
    # Metadata
    importance_score = Column(Integer, default=1)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_content_mem_org_type', 'organization_id', 'content_type'),
        Index('idx_content_mem_content', 'content_type', 'content_id'),
    )
    
    def __repr__(self):
        return f"<ContentMemory(id={self.id}, content={self.content_type}:{self.content_id})>"


class AgentMemory(Base):
    """
    Agent-level memory storage.
    
    Stores agent execution history and learnings including:
    - Execution outcomes and success rates
    - Parameter effectiveness
    - Error patterns and resolutions
    - Optimization suggestions
    """
    __tablename__ = "agent_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Agent identification
    agent_name = Column(String(100), nullable=False, index=True)
    agent_version = Column(String(20), nullable=True)
    
    # Execution reference
    execution_id = Column(String(100), nullable=True, index=True)  # Reference to agent_executions
    episode_id = Column(Integer, nullable=True, index=True)
    
    # Memory type
    memory_type = Column(String(50), nullable=False, index=True)  # outcome, parameter, error, optimization
    
    # Memory content
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    
    # Learning metadata
    is_learned = Column(Boolean, default=False)  # Has this been incorporated into agent behavior?
    confidence_score = Column(Integer, default=5)  # 1-10 scale
    
    # Metadata
    importance_score = Column(Integer, default=1)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_agent_mem_org_agent', 'organization_id', 'agent_name'),
        Index('idx_agent_mem_execution', 'execution_id'),
    )
    
    def __repr__(self):
        return f"<AgentMemory(id={self.id}, agent={self.agent_name}, type={self.memory_type})>"
