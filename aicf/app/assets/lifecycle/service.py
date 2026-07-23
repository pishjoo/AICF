"""
Asset Lifecycle Service

Provides business logic for asset lifecycle management including:
- State transitions with validation
- Lifecycle rules enforcement
- Audit logging
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from aicf.app.assets.lifecycle.models import AssetState, AssetLifecycleTransition, AssetAuditLog
from database.models import Asset
from services.exceptions import NotFoundError, ValidationError


# Define valid state transitions
VALID_TRANSITIONS = {
    AssetState.CREATED: [AssetState.PROCESSING, AssetState.FAILED, AssetState.DELETED],
    AssetState.PROCESSING: [AssetState.READY, AssetState.FAILED],
    AssetState.READY: [AssetState.IN_USE, AssetState.ARCHIVED, AssetState.DELETED],
    AssetState.IN_USE: [AssetState.READY, AssetState.ARCHIVED, AssetState.DELETED],
    AssetState.FAILED: [AssetState.PROCESSING, AssetState.DELETED],
    AssetState.ARCHIVED: [AssetState.READY, AssetState.DELETED],
    AssetState.DELETED: [],  # Terminal state
}

# Validation rules for each state
STATE_VALIDATION_RULES = {
    AssetState.CREATED: lambda asset: True,
    AssetState.PROCESSING: lambda asset: asset.filename is not None,
    AssetState.READY: lambda asset: (
        asset.storage_path is not None and 
        asset.processing_status == "completed"
    ),
    AssetState.IN_USE: lambda asset: asset.episode_id is not None or asset.extra_data.get("in_use_context") is not None,
    AssetState.FAILED: lambda asset: asset.processing_metadata is not None and asset.processing_metadata.get("error"),
    AssetState.ARCHIVED: lambda asset: asset.storage_provider is not None,
    AssetState.DELETED: lambda asset: True,  # Always valid
}


class AssetLifecycleService:
    """
    Service for managing asset lifecycle transitions.
    
    Provides state machine functionality with validation and audit logging.
    """
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_current_state(self, asset_id: int) -> Optional[AssetState]:
        """
        Get the current state of an asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Current AssetState or None if no transitions recorded
        """
        last_transition = self.db.query(AssetLifecycleTransition).filter(
            AssetLifecycleTransition.asset_id == asset_id
        ).order_by(AssetLifecycleTransition.created_at.desc()).first()
        
        if last_transition is None:
            # Check if asset exists and return default state
            asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                return AssetState.CREATED
            return None
        
        return last_transition.to_state
    
    def can_transition(self, from_state: Optional[AssetState], to_state: AssetState) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            from_state: Current state (None for initial transition)
            to_state: Target state
            
        Returns:
            True if transition is valid
        """
        if from_state is None:
            # Initial transition to CREATED is always valid
            return to_state == AssetState.CREATED
        
        if from_state not in VALID_TRANSITIONS:
            return False
        
        return to_state in VALID_TRANSITIONS[from_state]
    
    def validate_transition(self, asset: Asset, to_state: AssetState) -> Tuple[bool, List[str]]:
        """
        Validate that an asset can transition to a target state.
        
        Args:
            asset: Asset instance
            to_state: Target state
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check if validation rule exists for target state
        if to_state in STATE_VALIDATION_RULES:
            rule = STATE_VALIDATION_RULES[to_state]
            try:
                if not rule(asset):
                    errors.append(f"Asset does not meet validation requirements for state '{to_state.value}'")
            except Exception as e:
                errors.append(f"Validation rule failed: {str(e)}")
        
        return (len(errors) == 0, errors)
    
    def transition(
        self,
        asset_id: int,
        to_state: AssetState,
        triggered_by: str = "system",
        triggered_by_id: Optional[int] = None,
        reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        organization_id: Optional[int] = None
    ) -> AssetLifecycleTransition:
        """
        Transition an asset to a new state.
        
        Args:
            asset_id: Asset ID
            to_state: Target state
            triggered_by: Who triggered the transition (user, system, agent)
            triggered_by_id: ID of the trigger
            reason: Reason for transition
            context: Additional context data
            organization_id: Organization ID for tenant isolation
            
        Returns:
            Created AssetLifecycleTransition
            
        Raises:
            NotFoundError: If asset not found
            ValidationError: If transition is invalid
        """
        # Get asset
        asset_query = self.db.query(Asset).filter(Asset.id == asset_id)
        if organization_id:
            asset_query = asset_query.filter(Asset.organization_id == organization_id)
        asset = asset_query.first()
        
        if asset is None:
            raise NotFoundError(resource_type="asset", resource_id=asset_id)
        
        # Get current state
        from_state = self.get_current_state(asset_id)
        
        # Validate transition
        if not self.can_transition(from_state, to_state):
            raise ValidationError(
                message=f"Invalid state transition: {from_state.value if from_state else 'None'} -> {to_state.value}",
                field="to_state"
            )
        
        # Validate asset meets requirements for target state
        is_valid, validation_errors = self.validate_transition(asset, to_state)
        
        # Create transition record
        transition = AssetLifecycleTransition(
            asset_id=asset_id,
            organization_id=asset.organization_id,
            from_state=from_state,
            to_state=to_state,
            triggered_by=triggered_by,
            triggered_by_id=triggered_by_id,
            reason=reason,
            context=context or {},
            validated=is_valid,
            validation_errors=validation_errors
        )
        
        self.db.add(transition)
        self.db.commit()
        self.db.refresh(transition)
        
        # Log audit
        self._log_audit(
            asset_id=asset_id,
            organization_id=asset.organization_id,
            action="state_transition",
            actor_type=triggered_by,
            actor_id=triggered_by_id,
            before_data={"state": from_state.value if from_state else None},
            after_data={"state": to_state.value},
            status="success" if is_valid else "failure",
            error_message="; ".join(validation_errors) if validation_errors else None
        )
        
        return transition
    
    def _log_audit(
        self,
        asset_id: int,
        organization_id: int,
        action: str,
        actor_type: str,
        actor_id: Optional[int] = None,
        actor_email: Optional[str] = None,
        before_data: Optional[Dict[str, Any]] = None,
        after_data: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> AssetAuditLog:
        """
        Log an audit entry for an asset action.
        
        Args:
            asset_id: Asset ID
            organization_id: Organization ID
            action: Action performed
            actor_type: Type of actor (user, system, agent)
            actor_id: Actor ID
            actor_email: Actor email
            before_data: State before action
            after_data: State after action
            changes: Diff of changes
            status: Action status
            error_message: Error message if failed
            
        Returns:
            Created AssetAuditLog
        """
        audit_log = AssetAuditLog(
            asset_id=asset_id,
            organization_id=organization_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_email=actor_email,
            before_data=before_data,
            after_data=after_data,
            changes=changes,
            status=status,
            error_message=error_message
        )
        
        self.db.add(audit_log)
        self.db.commit()
        
        return audit_log
    
    def get_transitions(
        self,
        asset_id: int,
        organization_id: Optional[int] = None
    ) -> List[AssetLifecycleTransition]:
        """
        Get all transitions for an asset.
        
        Args:
            asset_id: Asset ID
            organization_id: Optional organization ID for tenant isolation
            
        Returns:
            List of AssetLifecycleTransition ordered by creation time
        """
        query = self.db.query(AssetLifecycleTransition).filter(
            AssetLifecycleTransition.asset_id == asset_id
        )
        
        if organization_id:
            query = query.filter(AssetLifecycleTransition.organization_id == organization_id)
        
        return query.order_by(AssetLifecycleTransition.created_at.asc()).all()
    
    def get_audit_logs(
        self,
        asset_id: int,
        organization_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AssetAuditLog]:
        """
        Get audit logs for an asset.
        
        Args:
            asset_id: Asset ID
            organization_id: Optional organization ID for tenant isolation
            limit: Maximum number of logs to return
            
        Returns:
            List of AssetAuditLog ordered by creation time (newest first)
        """
        query = self.db.query(AssetAuditLog).filter(
            AssetAuditLog.asset_id == asset_id
        )
        
        if organization_id:
            query = query.filter(AssetAuditLog.organization_id == organization_id)
        
        return query.order_by(AssetAuditLog.created_at.desc()).limit(limit).all()
    
    def initialize_asset(self, asset_id: int, organization_id: int) -> AssetLifecycleTransition:
        """
        Initialize a newly created asset to CREATED state.
        
        Args:
            asset_id: Asset ID
            organization_id: Organization ID
            
        Returns:
            Initial AssetLifecycleTransition
        """
        return self.transition(
            asset_id=asset_id,
            to_state=AssetState.CREATED,
            triggered_by="system",
            reason="Asset created",
            organization_id=organization_id
        )
