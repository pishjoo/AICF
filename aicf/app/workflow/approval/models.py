"""
Approval Workflow Models

Defines approval request models and status for human review workflows.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text, Boolean, Index
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
import enum

from database.connection import Base


class ApprovalStatus(str, enum.Enum):
    """
    Approval status for requests.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalAction(str, enum.Enum):
    """Actions that can be taken on an approval request."""
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    CANCEL = "cancel"


class ApprovalRequest(Base):
    """
    ApprovalRequest model - Human approval workflow for content production.
    
    Supports approval flows for:
    - ContentJob outputs
    - AgentExecution results
    - Assets (images, videos, voice)
    - Episodes
    """
    __tablename__ = "approval_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Related entities (polymorphic relationship)
    content_job_id = Column(Integer, ForeignKey("content_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Request info
    request_type = Column(String(50), nullable=False)  # content_job, agent_execution, asset, episode
    request_title = Column(String(255), nullable=False)
    request_description = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    
    # Requester
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Reviewer
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Decision
    decision_notes = Column(Text, nullable=True)
    rejection_reason = Column(String(100), nullable=True)
    
    # Required approvals
    required_approvals = Column(Integer, default=1)
    current_approvals = Column(Integer, default=0)
    
    # Approvers (JSON list of user IDs who have approved)
    approvers = Column(JSON, default=list)
    
    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Due date
    due_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    # NOTE: 'metadata' is a reserved attribute name in SQLAlchemy's Declarative
    # API, so the Python attribute is named 'request_metadata' while the
    # underlying database column remains 'metadata' for backward compatibility.
    request_metadata = Column("metadata", JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    escalated_user = relationship("User", foreign_keys=[escalated_to])
    content_job = relationship("ContentJob", back_populates="approval_requests")
    agent_execution = relationship("AgentExecution", back_populates="approval_requests")
    asset = relationship("Asset", back_populates="approval_requests")
    episode = relationship("Episode", back_populates="approval_requests")
    
    __table_args__ = (
        Index('idx_approval_org', 'organization_id'),
        Index('idx_approval_status', 'status'),
        Index('idx_approval_type', 'request_type'),
        Index('idx_approval_requested', 'requested_by'),
    )

    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, type='{self.request_type}', status='{self.status}')>"
