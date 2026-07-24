"""
Asset Lifecycle Models

Defines asset states, transitions, and audit log models for lifecycle management.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from database.connection import Base


class AssetState(str, enum.Enum):
    """
    Asset lifecycle states.
    
    Defines the complete lifecycle of an asset from creation to deletion.
    """
    CREATED = "created"       # Asset initially created/uploaded
    PROCESSING = "processing" # Asset is being processed (transcoding, optimization, etc.)
    READY = "ready"          # Asset is ready for use
    IN_USE = "in_use"        # Asset is currently used in production
    FAILED = "failed"        # Processing failed
    ARCHIVED = "archived"    # Asset archived (cold storage)
    DELETED = "deleted"      # Asset marked for deletion (soft delete)


class AssetLifecycleTransition(Base):
    """
    AssetLifecycleTransition model - Tracks state transitions for assets.
    
    Records each state change with validation and context.
    """
    __tablename__ = "asset_lifecycle_transitions"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # State transition
    from_state = Column(SQLEnum(AssetState), nullable=True)  # None for initial state
    to_state = Column(SQLEnum(AssetState), nullable=False)
    
    # Transition metadata
    triggered_by = Column(String(100), nullable=True)  # User, system, agent
    triggered_by_id = Column(Integer, nullable=True)  # User ID or agent ID
    reason = Column(Text, nullable=True)
    context = Column(JSON, default=dict)
    
    # Validation
    validated = Column(Boolean, default=True)
    validation_errors = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    asset = relationship("Asset", back_populates="lifecycle_transitions")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_transition_asset', 'asset_id'),
        Index('idx_transition_org', 'organization_id'),
        Index('idx_transition_state', 'to_state'),
    )
    
    def __repr__(self):
        return f"<AssetLifecycleTransition(id={self.id}, asset_id={self.asset_id}, {self.from_state} -> {self.to_state})>"


class AssetAuditLog(Base):
    """
    AssetAuditLog model - Comprehensive audit history for assets.
    
    Records all actions performed on assets for compliance and debugging.
    """
    __tablename__ = "asset_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # create, update, transition, delete, etc.
    resource_type = Column(String(50), default="asset")
    
    # Actor information
    actor_type = Column(String(50), nullable=False)  # user, system, agent
    actor_id = Column(Integer, nullable=True)
    actor_email = Column(String(255), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Data changes
    before_data = Column(JSON, nullable=True)  # Previous state
    after_data = Column(JSON, nullable=True)  # New state
    changes = Column(JSON, nullable=True)  # Diff of changes
    
    # Result
    status = Column(String(20), nullable=True)  # success, failure
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    asset = relationship("Asset", back_populates="audit_logs")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_audit_asset', 'asset_id'),
        Index('idx_audit_org', 'organization_id'),
        Index('idx_audit_action_aicf', 'action'),
        Index('idx_audit_created_aicf', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AssetAuditLog(id={self.id}, asset_id={self.asset_id}, action='{self.action}')>"
