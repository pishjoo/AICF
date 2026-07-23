"""
Approval Workflow Service

Provides business logic for human approval workflows including:
- Creating approval requests
- Processing approvals/rejections
- Managing approval chains
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from aicf.app.workflow.approval.models import (
    ApprovalRequest, 
    ApprovalStatus, 
    ApprovalAction
)
from database.models import ContentJob, AgentExecution, Asset, Episode, User
from services.exceptions import NotFoundError, ValidationError


class ApprovalWorkflowService:
    """
    Service for managing human approval workflows.
    
    Supports approval flows for content jobs, agent executions, assets, and episodes.
    """
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_request(
        self,
        organization_id: int,
        request_type: str,
        request_title: str,
        requested_by: int,
        request_description: Optional[str] = None,
        content_job_id: Optional[int] = None,
        agent_execution_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        episode_id: Optional[int] = None,
        required_approvals: int = 1,
        due_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            organization_id: Organization ID
            request_type: Type of request (content_job, agent_execution, asset, episode)
            request_title: Title of the request
            requested_by: User ID requesting approval
            request_description: Description of what needs approval
            content_job_id: Associated content job ID
            agent_execution_id: Associated agent execution ID
            asset_id: Associated asset ID
            episode_id: Associated episode ID
            required_approvals: Number of approvals needed
            due_at: Due date for approval
            metadata: Additional metadata
            
        Returns:
            Created ApprovalRequest
            
        Raises:
            ValidationError: If no related entity provided or invalid type
        """
        # Validate that at least one related entity is provided
        related_entities = [content_job_id, agent_execution_id, asset_id, episode_id]
        if not any(related_entities):
            raise ValidationError(
                message="At least one related entity must be provided",
                field="related_entity"
            )
        
        # Validate request type
        valid_types = ["content_job", "agent_execution", "asset", "episode"]
        if request_type not in valid_types:
            raise ValidationError(
                message=f"Invalid request type. Must be one of: {valid_types}",
                field="request_type"
            )
        
        # Verify related entity exists and belongs to organization
        self._verify_entity(organization_id, request_type, related_entities)
        
        # Verify user exists
        user = self.db.query(User).filter(
            User.id == requested_by,
            User.organization_id == organization_id
        ).first()
        if not user:
            raise NotFoundError(resource_type="user", resource_id=requested_by)
        
        # Create approval request
        request = ApprovalRequest(
            organization_id=organization_id,
            request_type=request_type,
            request_title=request_title,
            request_description=request_description,
            content_job_id=content_job_id,
            agent_execution_id=agent_execution_id,
            asset_id=asset_id,
            episode_id=episode_id,
            status=ApprovalStatus.PENDING,
            requested_by=requested_by,
            required_approvals=required_approvals,
            current_approvals=0,
            approvers=[],
            due_at=due_at,
            metadata=metadata or {},
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def _verify_entity(
        self, 
        organization_id: int, 
        request_type: str, 
        entities: List[Optional[int]]
    ):
        """Verify that the related entity exists and belongs to the organization."""
        entity_map = {
            "content_job": (ContentJob, entities[0]),
            "agent_execution": (AgentExecution, entities[1]),
            "asset": (Asset, entities[2]),
            "episode": (Episode, entities[3]),
        }
        
        model, entity_id = entity_map.get(request_type, (None, None))
        
        if model and entity_id:
            entity = self.db.query(model).filter(
                model.id == entity_id,
                model.organization_id == organization_id
            ).first()
            
            if not entity:
                raise NotFoundError(
                    resource_type=request_type.replace("_", " "),
                    resource_id=entity_id
                )
    
    def approve(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
        decision_notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Approve an approval request.
        
        Args:
            request_id: Approval request ID
            user_id: User ID approving
            organization_id: Organization ID
            decision_notes: Notes about the approval
            
        Returns:
            Updated ApprovalRequest
            
        Raises:
            NotFoundError: If request not found
            ValidationError: If request not pending or user already approved
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        if request.status != ApprovalStatus.PENDING:
            raise ValidationError(
                message=f"Cannot approve request with status '{request.status.value}'",
                field="status"
            )
        
        if user_id in request.approvers:
            raise ValidationError(
                message="User has already approved this request",
                field="user_id"
            )
        
        # Add approval
        request.approvers.append(user_id)
        request.current_approvals += 1
        
        # Check if all required approvals received
        if request.current_approvals >= request.required_approvals:
            request.status = ApprovalStatus.APPROVED
            request.reviewed_by = user_id
            request.reviewed_at = datetime.utcnow()
            request.decision_notes = decision_notes
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def reject(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
        rejection_reason: str,
        decision_notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Reject an approval request.
        
        Args:
            request_id: Approval request ID
            user_id: User ID rejecting
            organization_id: Organization ID
            rejection_reason: Reason for rejection
            decision_notes: Additional notes
            
        Returns:
            Updated ApprovalRequest
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        if request.status != ApprovalStatus.PENDING:
            raise ValidationError(
                message=f"Cannot reject request with status '{request.status.value}'",
                field="status"
            )
        
        request.status = ApprovalStatus.REJECTED
        request.reviewed_by = user_id
        request.reviewed_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
        request.decision_notes = decision_notes
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def request_changes(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
        decision_notes: str,
    ) -> ApprovalRequest:
        """
        Request changes on an approval request.
        
        Args:
            request_id: Approval request ID
            user_id: User ID requesting changes
            organization_id: Organization ID
            decision_notes: Notes about required changes
            
        Returns:
            Updated ApprovalRequest
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        if request.status != ApprovalStatus.PENDING:
            raise ValidationError(
                message=f"Cannot request changes on request with status '{request.status.value}'",
                field="status"
            )
        
        request.status = ApprovalStatus.CHANGES_REQUESTED
        request.reviewed_by = user_id
        request.reviewed_at = datetime.utcnow()
        request.decision_notes = decision_notes
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def cancel(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
    ) -> ApprovalRequest:
        """
        Cancel an approval request.
        
        Args:
            request_id: Approval request ID
            user_id: User ID cancelling (must be requester)
            organization_id: Organization ID
            
        Returns:
            Updated ApprovalRequest
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        if request.requested_by != user_id:
            raise ValidationError(
                message="Only the requester can cancel the approval request",
                field="user_id"
            )
        
        if request.status != ApprovalStatus.PENDING:
            raise ValidationError(
                message=f"Cannot cancel request with status '{request.status.value}'",
                field="status"
            )
        
        request.status = ApprovalStatus.REJECTED  # Treat cancellation as rejection
        request.decision_notes = "Cancelled by requester"
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def resubmit(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
    ) -> ApprovalRequest:
        """
        Resubmit an approval request after changes.
        
        Args:
            request_id: Approval request ID
            user_id: User ID resubmitting
            organization_id: Organization ID
            
        Returns:
            Updated ApprovalRequest
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        if request.status != ApprovalStatus.CHANGES_REQUESTED:
            raise ValidationError(
                message=f"Can only resubmit requests with status 'changes_requested', current: '{request.status.value}'",
                field="status"
            )
        
        request.status = ApprovalStatus.PENDING
        request.approvers = []
        request.current_approvals = 0
        request.reviewed_by = None
        request.reviewed_at = None
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def escalate(
        self,
        request_id: int,
        user_id: int,
        organization_id: int,
        escalated_to: int,
    ) -> ApprovalRequest:
        """
        Escalate an approval request to another user.
        
        Args:
            request_id: Approval request ID
            user_id: User ID escalating
            organization_id: Organization ID
            escalated_to: User ID to escalate to
            
        Returns:
            Updated ApprovalRequest
        """
        request = self._get_request(request_id, organization_id)
        
        if request is None:
            raise NotFoundError(resource_type="approval request", resource_id=request_id)
        
        # Verify escalated user exists
        escalated_user = self.db.query(User).filter(
            User.id == escalated_to,
            User.organization_id == organization_id
        ).first()
        
        if not escalated_user:
            raise NotFoundError(resource_type="user", resource_id=escalated_to)
        
        request.escalated = True
        request.escalated_to = escalated_to
        request.escalated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def _get_request(self, request_id: int, organization_id: int) -> Optional[ApprovalRequest]:
        """Get approval request with tenant isolation."""
        return self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id,
            ApprovalRequest.organization_id == organization_id
        ).first()
    
    def get_request(self, request_id: int, organization_id: Optional[int] = None) -> Optional[ApprovalRequest]:
        """Get a single approval request."""
        query = self.db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id)
        
        if organization_id:
            query = query.filter(ApprovalRequest.organization_id == organization_id)
        
        return query.first()
    
    def list_requests(
        self,
        organization_id: int,
        status: Optional[ApprovalStatus] = None,
        request_type: Optional[str] = None,
        requested_by: Optional[int] = None,
        reviewed_by: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """
        List approval requests with filters.
        
        Args:
            organization_id: Organization ID
            status: Filter by status
            request_type: Filter by type
            requested_by: Filter by requester
            reviewed_by: Filter by reviewer
            skip: Pagination offset
            limit: Maximum results
            
        Returns:
            List of ApprovalRequest
        """
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.organization_id == organization_id
        )
        
        if status:
            query = query.filter(ApprovalRequest.status == status)
        
        if request_type:
            query = query.filter(ApprovalRequest.request_type == request_type)
        
        if requested_by:
            query = query.filter(ApprovalRequest.requested_by == requested_by)
        
        if reviewed_by:
            query = query.filter(ApprovalRequest.reviewed_by == reviewed_by)
        
        return query.order_by(ApprovalRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_pending_count(self, organization_id: int, user_id: Optional[int] = None) -> int:
        """
        Get count of pending approval requests.
        
        Args:
            organization_id: Organization ID
            user_id: Optional user ID to filter requests awaiting their review
            
        Returns:
            Count of pending requests
        """
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.organization_id == organization_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        )
        
        return query.count()
