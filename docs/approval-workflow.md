# AICF v2 Approval Workflow Documentation

## Overview

The Human Approval Workflow system enables human review and approval of AI-generated content at key points in the production pipeline. It ensures quality control and provides governance for automated content generation.

---

## Purpose

The approval workflow system serves several critical functions:

1. **Quality Gate**: Human review before critical production steps
2. **Governance**: Ensure compliance with brand and policy standards
3. **Exception Handling**: Handle edge cases that automation cannot resolve
4. **Audit Trail**: Record all approval decisions for compliance
5. **Collaboration**: Enable team-based review processes

---

## Approval Status

### Status Definitions

| Status | Description | Allowed Actions |
|--------|-------------|-----------------|
| `pending` | Awaiting review | approve, reject, request_changes, cancel |
| `approved` | Approved for use | (terminal for this request) |
| `rejected` | Rejected | resubmit, escalate |
| `changes_requested` | Changes needed | resubmit, cancel |

### Status Transitions

```
┌─────────────┐
│   PENDING   │
└──────┬──────┘
       │
   ┌───┴───┬─────────────┬──────────────┐
   ▼       ▼             ▼              ▼
┌──────────┐  ┌───────────┐  ┌──────────────────┐  ┌─────────┐
│ APPROVED │  │ REJECTED  │  │ CHANGES_REQUESTED│  │ CANCEL  │
└──────────┘  └─────┬─────┘  └────────┬─────────┘  └─────────┘
                    │                 │
                    │ resubmit        │ resubmit
                    └────────┬────────┘
                             ▼
                       ┌─────────────┐
                       │   PENDING   │
                       └─────────────┘
```

---

## Database Schema

### ApprovalRequest Model

```python
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `organization_id` | Integer | Foreign key to organizations |
| `content_job_id` | Integer | Foreign key to content_jobs (nullable) |
| `agent_execution_id` | Integer | Foreign key to agent_executions (nullable) |
| `asset_id` | Integer | Foreign key to assets (nullable) |
| `episode_id` | Integer | Foreign key to episodes (nullable) |
| `request_type` | String(50) | content_job, agent_execution, asset, episode |
| `request_title` | String(255) | Title of the request |
| `request_description` | Text | Description (nullable) |
| `status` | ApprovalStatus | pending, approved, rejected, changes_requested |
| `requested_by` | Integer | Foreign key to users (requester) |
| `requested_at` | DateTime | Request timestamp |
| `reviewed_by` | Integer | Foreign key to users (reviewer) (nullable) |
| `reviewed_at` | DateTime | Review timestamp (nullable) |
| `decision_notes` | Text | Reviewer notes (nullable) |
| `rejection_reason` | String(100) | Reason for rejection (nullable) |
| `required_approvals` | Integer | Number of approvals needed (default: 1) |
| `current_approvals` | Integer | Current approval count (default: 0) |
| `approvers` | JSON | List of user IDs who have approved |
| `escalated` | Boolean | Whether request is escalated |
| `escalated_to` | Integer | Foreign key to users (escalation target) (nullable) |
| `escalated_at` | DateTime | Escalation timestamp (nullable) |
| `due_at` | DateTime | Due date for review (nullable) |
| `metadata` | JSON | Additional metadata |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

#### Indexes

```sql
CREATE INDEX idx_approval_org ON approval_requests(organization_id);
CREATE INDEX idx_approval_status ON approval_requests(status);
CREATE INDEX idx_approval_type ON approval_requests(request_type);
CREATE INDEX idx_approval_requested ON approval_requests(requested_by);
```

---

## Approval Actions

### Available Actions

| Action | Description | From Status | To Status |
|--------|-------------|-------------|-----------|
| `submit` | Submit for approval | (new) | pending |
| `approve` | Approve the request | pending | approved |
| `reject` | Reject the request | pending | rejected |
| `request_changes` | Request modifications | pending | changes_requested |
| `cancel` | Cancel the request | pending | cancelled |

### Action Service

```python
class ApprovalService:
    """Service for managing approval workflows."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_request(
        self,
        organization_id: int,
        request_type: str,
        request_title: str,
        requested_by: int,
        related_entity_id: Optional[int] = None,
        description: Optional[str] = None,
        required_approvals: int = 1,
        due_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> ApprovalRequest:
        """Create a new approval request."""
        pass
    
    def approve(
        self,
        request_id: int,
        reviewed_by: int,
        notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve a request."""
        pass
    
    def reject(
        self,
        request_id: int,
        reviewed_by: int,
        reason: str,
        notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Reject a request."""
        pass
    
    def request_changes(
        self,
        request_id: int,
        reviewed_by: int,
        change_requests: List[str],
        notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Request changes for a request."""
        pass
    
    def escalate(
        self,
        request_id: int,
        escalated_by: int,
        escalated_to: int,
        reason: str
    ) -> ApprovalRequest:
        """Escalate a request."""
        pass
```

---

## Integration Points

### With Content Jobs

```python
# Create approval request for completed job
if content_job.status == ContentJobStatus.COMPLETED:
    approval_request = ApprovalRequest(
        organization_id=content_job.organization_id,
        content_job_id=content_job.id,
        request_type="content_job",
        request_title=f"Review {content_job.job_type} output",
        requested_by=user_id,
        metadata={"job_output": content_job.output_data}
    )
```

### With Agent Executions

```python
# Request approval for agent output
if agent_result.requires_human_review():
    approval_service.create_request(
        organization_id=context.organization_id,
        request_type="agent_execution",
        agent_execution_id=execution_record.id,
        request_title=f"Review {agent_name} output",
        requested_by=context.user_id
    )
```

### With Assets

```python
# Asset approval after quality evaluation
if quality_score.quality_score < AUTO_APPROVE_THRESHOLD:
    approval_service.create_request(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        request_type="asset",
        request_title=f"Review {asset.asset_type} quality",
        requested_by=user_id,
        metadata={"quality_score": quality_score.quality_score}
    )
```

### With Asset Lifecycle

```python
# After approval, transition asset state
if approval_request.status == ApprovalStatus.APPROVED:
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.READY,
        triggered_by="user",
        triggered_by_id=approver_id,
        reason="Human approval granted"
    )
```

---

## Tenant Isolation

All approval requests are scoped by organization:

```python
# Query includes organization filter
requests = db.query(ApprovalRequest).filter(
    ApprovalRequest.id == request_id,
    ApprovalRequest.organization_id == organization_id
).all()

# Service validates organization context
def approve(self, request_id, reviewed_by, ...):
    request = self.db.query(ApprovalRequest).filter(
        ApprovalRequest.id == request_id,
        ApprovalRequest.organization_id == context.organization_id
    ).first()
    
    if not request:
        raise ApprovalRequestNotFoundError("Request not found in your organization")
```

---

## Usage Examples

### Creating an Approval Request

```python
# Submit content job for approval
request = approval_service.create_request(
    organization_id=org_id,
    request_type="content_job",
    content_job_id=job_id,
    request_title="Review script generation",
    requested_by=user_id,
    description="Please review the generated script for accuracy",
    required_approvals=2,
    due_at=datetime.now() + timedelta(days=1)
)
```

### Approving a Request

```python
# Approve with notes
request = approval_service.approve(
    request_id=request_id,
    reviewed_by=user_id,
    notes="Looks great! Approved for production."
)
```

### Requesting Changes

```python
# Request specific changes
request = approval_service.request_changes(
    request_id=request_id,
    reviewed_by=user_id,
    change_requests=[
        "Update the opening scene to be more engaging",
        "Add more detail to the character descriptions"
    ],
    notes="Overall good, but needs these adjustments"
)
```

### Escalating a Request

```python
# Escalate overdue request
if request.due_at and datetime.now() > request.due_at:
    request = approval_service.escalate(
        request_id=request.id,
        escalated_by=current_user_id,
        escalated_to=manager_id,
        reason="Request overdue for review"
    )
```

---

## Multi-Approval Workflow

For requests requiring multiple approvers:

```python
# Check if enough approvals received
if request.current_approvals >= request.required_approvals:
    request.status = ApprovalStatus.APPROVED
    request.reviewed_at = datetime.now()
    
    # Trigger next workflow step
    workflow_engine.continue_after_approval(request)
```

---

## Future Enhancements

### Planned Features

1. **Approval Templates**: Predefined approval flows for common scenarios
2. **Delegation**: Allow approvers to delegate to others
3. **Bulk Approval**: Approve multiple requests at once
4. **Conditional Approvals**: Approve with conditions
5. **SLA Tracking**: Track approval SLAs and send reminders

---

## Document Information

- **Version**: 1.0
- **Last Updated**: Phase 7.99
- **Author**: AICF Engineering Team
- **Status**: Production Ready
- **Related Documents**:
  - `database-schema.md`
  - `media-quality-system.md`
  - `asset-lifecycle.md`
  - `workflow-engine.md`
  - `aicf-current-architecture.md`
