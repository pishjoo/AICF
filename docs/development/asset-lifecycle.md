# AICF v2 Asset Lifecycle Documentation

## Overview

The Asset Lifecycle Management system provides comprehensive tracking and control of media assets from creation through archival. It ensures proper state transitions, validation, audit history, and compliance with organizational policies.

---

## Purpose

The asset lifecycle system serves several critical functions:

1. **State Management**: Track asset state from creation to deletion
2. **Validation**: Ensure only valid state transitions occur
3. **Audit Trail**: Maintain complete history of all asset actions
4. **Compliance**: Support regulatory and organizational requirements
5. **Cost Control**: Enable archival and deletion to reduce storage costs

---

## Asset States

### State Definitions

| State | Description | Allowed Transitions |
|-------|-------------|---------------------|
| `CREATED` | Asset initially created or uploaded | → PROCESSING, → FAILED |
| `PROCESSING` | Asset is being processed (transcoding, optimization) | → READY, → FAILED |
| `READY` | Asset is ready for use | → IN_USE, → ARCHIVED, → DELETED |
| `IN_USE` | Asset is currently used in production | → READY, → ARCHIVED |
| `FAILED` | Processing failed | → CREATED (retry), → DELETED |
| `ARCHIVED` | Asset archived to cold storage | → READY (restore), → DELETED |
| `DELETED` | Asset marked for deletion (soft delete) | (terminal state) |

### State Transition Diagram

```
                                    ┌─────────────┐
                                    │   CREATED   │
                                    └──────┬──────┘
                                           │ create
                                           ▼
                                    ┌─────────────┐
                              ┌────│  PROCESSING │◄────┐
                              │    └──────┬──────┘     │
                              │           │ process    │ retry
                              │           ▼            │
                         ┌────┴────┐ ┌────────┐       │
                         │  READY  │◄│ FAILED │───────┘
                         └────┬────┘ └───┬────┘
                              │          │ delete
                    use       │          ▼
                 ┌────────────┘     ┌─────────┐
                 │                  │ DELETED │
                 ▼                  └─────────┘
         ┌───────────────┐
         │    IN_USE     │
         └───────┬───────┘
                 │ done using
                 ▼
         ┌───────────────┐
         │   ARCHIVED    │──────────────► DELETED
         └───────────────┘    delete
              │
              │ restore
              ▼
         ┌───────────────┐
         │    READY      │
         └───────────────┘
```

---

## Database Schema

### AssetLifecycleTransition Model

```python
class AssetLifecycleTransition(Base):
    __tablename__ = "asset_lifecycle_transitions"
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `asset_id` | Integer | Foreign key to assets |
| `organization_id` | Integer | Foreign key to organizations (tenant isolation) |
| `from_state` | AssetState | Previous state (None for initial) |
| `to_state` | AssetState | New state after transition |
| `triggered_by` | String(100) | Who/what triggered transition (user, system, agent) |
| `triggered_by_id` | Integer | ID of trigger entity |
| `reason` | Text | Reason for transition |
| `context` | JSON | Additional context data |
| `validated` | Boolean | Whether transition was validated |
| `validation_errors` | JSON | List of validation errors if any |
| `created_at` | DateTime | Timestamp of transition |

#### Indexes

```sql
CREATE INDEX idx_transition_asset ON asset_lifecycle_transitions(asset_id);
CREATE INDEX idx_transition_org ON asset_lifecycle_transitions(organization_id);
CREATE INDEX idx_transition_state ON asset_lifecycle_transitions(to_state);
```

### AssetAuditLog Model

```python
class AssetAuditLog(Base):
    __tablename__ = "asset_audit_logs"
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `asset_id` | Integer | Foreign key to assets |
| `organization_id` | Integer | Foreign key to organizations |
| `action` | String(100) | Action performed (create, update, transition, delete) |
| `resource_type` | String(50) | Type of resource (default: "asset") |
| `actor_type` | String(50) | Type of actor (user, system, agent) |
| `actor_id` | Integer | ID of actor |
| `actor_email` | String(255) | Email of actor (for users) |
| `ip_address` | String(45) | IP address of request |
| `user_agent` | String(500) | User agent string |
| `before_data` | JSON | State before action |
| `after_data` | JSON | State after action |
| `changes` | JSON | Diff of changes |
| `status` | String(20) | Result status (success, failure) |
| `error_message` | Text | Error message if failed |
| `created_at` | DateTime | Timestamp of action |

#### Indexes

```sql
CREATE INDEX idx_audit_asset ON asset_audit_logs(asset_id);
CREATE INDEX idx_audit_org ON asset_audit_logs(organization_id);
CREATE INDEX idx_audit_action ON asset_audit_logs(action);
CREATE INDEX idx_audit_created ON asset_audit_logs(created_at);
```

---

## Validation Rules

### State Transition Validation

```python
VALID_TRANSITIONS = {
    AssetState.CREATED: [AssetState.PROCESSING, AssetState.FAILED],
    AssetState.PROCESSING: [AssetState.READY, AssetState.FAILED],
    AssetState.READY: [AssetState.IN_USE, AssetState.ARCHIVED, AssetState.DELETED],
    AssetState.IN_USE: [AssetState.READY, AssetState.ARCHIVED],
    AssetState.FAILED: [AssetState.CREATED, AssetState.DELETED],
    AssetState.ARCHIVED: [AssetState.READY, AssetState.DELETED],
    AssetState.DELETED: []  # Terminal state
}
```

### Validation Logic

```python
def validate_transition(asset: Asset, to_state: AssetState) -> Tuple[bool, List[str]]:
    """
    Validate state transition for an asset.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    current_state = asset.state
    
    # Check if transition is allowed
    allowed_states = VALID_TRANSITIONS.get(current_state, [])
    if to_state not in allowed_states:
        errors.append(
            f"Invalid transition from {current_state.value} to {to_state.value}. "
            f"Allowed: {[s.value for s in allowed_states]}"
        )
    
    # Business rule validations
    if to_state == AssetState.DELETED:
        # Check if asset is in use
        if asset.is_in_use():
            errors.append("Cannot delete asset that is currently in use")
        
        # Check retention policy
        if not asset.retention_period_expired():
            errors.append("Asset retention period has not expired")
    
    if to_state == AssetState.PROCESSING:
        # Check if required resources are available
        if not asset.has_required_resources():
            errors.append("Required processing resources not available")
    
    return len(errors) == 0, errors
```

---

## Service Layer

### AssetLifecycleService

```python
class AssetLifecycleService:
    """Service for managing asset lifecycle transitions."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def transition_state(
        self,
        asset_id: int,
        to_state: AssetState,
        triggered_by: str,
        triggered_by_id: Optional[int] = None,
        reason: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AssetLifecycleTransition:
        """
        Transition asset to new state.
        
        Args:
            asset_id: ID of asset to transition
            to_state: Target state
            triggered_by: Who triggered (user, system, agent)
            triggered_by_id: ID of trigger entity
            reason: Reason for transition
            context: Additional context
            
        Returns:
            AssetLifecycleTransition record
            
        Raises:
            InvalidTransitionError: If transition is not allowed
        """
        pass
    
    def get_current_state(self, asset_id: int) -> AssetState:
        """Get current state of asset."""
        pass
    
    def get_transition_history(self, asset_id: int) -> List[AssetLifecycleTransition]:
        """Get full transition history for asset."""
        pass
    
    def get_audit_log(self, asset_id: int) -> List[AssetAuditLog]:
        """Get audit log for asset."""
        pass
    
    def log_action(
        self,
        asset_id: int,
        action: str,
        actor_type: str,
        actor_id: Optional[int],
        before_data: Optional[Dict],
        after_data: Optional[Dict],
        status: str,
        error_message: Optional[str] = None
    ) -> AssetAuditLog:
        """Log an action performed on an asset."""
        pass
```

---

## Usage Examples

### Creating an Asset

```python
# Create new asset
asset = Asset(
    organization_id=org_id,
    episode_id=episode_id,
    asset_type="image",
    storage_key=f"org_{org_id}/episodes/{episode_id}/image_001.png",
    state=AssetState.CREATED
)
db.add(asset)
db.commit()

# Log creation
lifecycle_service.log_action(
    asset_id=asset.id,
    action="create",
    actor_type="user",
    actor_id=user_id,
    before_data=None,
    after_data={"state": "created"},
    status="success"
)

# Start processing
lifecycle_service.transition_state(
    asset_id=asset.id,
    to_state=AssetState.PROCESSING,
    triggered_by="system",
    reason="Starting asset processing pipeline"
)
```

### Processing Completion

```python
# After processing completes successfully
try:
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.READY,
        triggered_by="system",
        triggered_by_id=processor_id,
        reason="Processing completed successfully",
        context={"processing_time": 5.2, "output_size": 1024000}
    )
except InvalidTransitionError as e:
    logger.error(f"Failed to transition asset: {e}")
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.FAILED,
        triggered_by="system",
        reason=str(e)
    )
```

### Using Asset in Production

```python
# Mark asset as in use when included in video production
lifecycle_service.transition_state(
    asset_id=asset.id,
    to_state=AssetState.IN_USE,
    triggered_by="agent",
    triggered_by_id=video_production_agent_id,
    reason="Asset included in video production",
    context={"production_job_id": job_id}
)
```

### Archiving Old Assets

```python
# Archive assets not used in 90 days
old_assets = db.query(Asset).filter(
    Asset.state == AssetState.READY,
    Asset.last_used_at < datetime.now() - timedelta(days=90)
).all()

for asset in old_assets:
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.ARCHIVED,
        triggered_by="system",
        reason="Automatic archival after 90 days of inactivity"
    )
```

---

## Tenant Isolation

All asset lifecycle operations are scoped by organization:

```python
# Query always includes organization filter
transitions = db.query(AssetLifecycleTransition).filter(
    AssetLifecycleTransition.asset_id == asset_id,
    AssetLifecycleTransition.organization_id == organization_id
).all()

# Service validates organization context
def transition_state(self, asset_id, to_state, ...):
    asset = self.db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.organization_id == context.organization_id  # Enforced!
    ).first()
    
    if not asset:
        raise AssetNotFoundError("Asset not found in your organization")
```

---

## Audit History

### Querying Audit Logs

```python
# Get all actions on an asset
audit_logs = db.query(AssetAuditLog).filter(
    AssetAuditLog.asset_id == asset_id
).order_by(AssetAuditLog.created_at.desc()).all()

# Get actions by type
create_actions = db.query(AssetAuditLog).filter(
    AssetAuditLog.asset_id == asset_id,
    AssetAuditLog.action == "create"
).all()

# Get failed actions
failed_actions = db.query(AssetAuditLog).filter(
    AssetAuditLog.asset_id == asset_id,
    AssetAuditLog.status == "failure"
).all()
```

### Compliance Reporting

```python
def generate_compliance_report(
    organization_id: int,
    start_date: datetime,
    end_date: datetime
) -> Dict:
    """Generate compliance report for asset actions."""
    
    logs = db.query(AssetAuditLog).filter(
        AssetAuditLog.organization_id == organization_id,
        AssetAuditLog.created_at >= start_date,
        AssetAuditLog.created_at <= end_date
    ).all()
    
    return {
        "organization_id": organization_id,
        "period_start": start_date,
        "period_end": end_date,
        "total_actions": len(logs),
        "actions_by_type": Counter(log.action for log in logs),
        "failed_actions": sum(1 for log in logs if log.status == "failure"),
        "unique_assets": len(set(log.asset_id for log in logs)),
        "unique_actors": len(set(log.actor_id for log in logs if log.actor_id))
    }
```

---

## Integration Points

### With Quality Evaluation

```python
# After quality evaluation passes
if quality_score.approval_status == ApprovalStatus.APPROVED:
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.READY,
        triggered_by="system",
        reason="Quality evaluation passed",
        context={"quality_score": quality_score.quality_score}
    )
```

### With Approval Workflow

```python
# When approval is requested
approval_request = ApprovalRequest(
    asset_id=asset.id,
    request_type="asset",
    status=ApprovalStatus.PENDING
)

# After approval
if approval_request.status == ApprovalStatus.APPROVED:
    lifecycle_service.transition_state(
        asset_id=asset.id,
        to_state=AssetState.READY,
        triggered_by="user",
        triggered_by_id=approver_id,
        reason="Human approval granted"
    )
```

### With Cost Tracking

```python
# When archiving, calculate storage cost savings
if to_state == AssetState.ARCHIVED:
    storage_savings = calculate_storage_cost_savings(asset)
    cost_service.record_cost(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        cost_type="storage",
        provider="aws_s3",
        units=-asset.size_gb,  # Negative = savings
        unit_type="gigabytes",
        metadata={"reason": "archived_to_cold_storage"}
    )
```

---

## Future Enhancements

### Planned Features

1. **Automated Lifecycle Policies**: Define rules for automatic transitions
2. **Batch Operations**: Transition multiple assets at once
3. **Lifecycle Templates**: Predefined lifecycle configurations per asset type
4. **Advanced Analytics**: Predict optimal archival times based on usage patterns
5. **Integration with External Storage**: Direct integration with S3/GCS lifecycle policies

---

## Document Information

- **Version**: 1.0
- **Last Updated**: Phase 7.99
- **Author**: AICF Engineering Team
- **Status**: Production Ready
- **Related Documents**:
  - `database-schema.md`
  - `media-quality-system.md`
  - `approval-workflow.md`
  - `aicf-current-architecture.md`
