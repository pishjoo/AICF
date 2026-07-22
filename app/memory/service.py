"""
Memory Service Layer

This module provides CRUD operations for memory models with tenant isolation.
Designed to be compatible with future vector database migration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.memory.models import (
    OrganizationMemory,
    ChannelMemory,
    AudienceMemory,
    ContentMemory,
    AgentMemory,
)


class MemoryServiceBase:
    """Base class for memory services with common CRUD operations."""
    
    def __init__(self, db: Session, organization_id: int):
        self.db = db
        self.organization_id = organization_id
        self.model: Type = None  # Override in subclass
    
    def _ensure_tenant_isolation(self, query):
        """Ensure all queries include organization_id filter."""
        return query.filter(self.model.organization_id == self.organization_id)
    
    def create(self, key: str, value: Any, memory_type: str, **kwargs) -> Any:
        """Create a new memory entry."""
        instance = self.model(
            organization_id=self.organization_id,
            key=key,
            value=value,
            memory_type=memory_type,
            **kwargs
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def get(self, key: str) -> Optional[Any]:
        """Get a memory entry by key."""
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        return query.filter(self.model.key == key).first()
    
    def get_by_type(self, memory_type: str) -> List[Any]:
        """Get all memory entries of a specific type."""
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        return query.filter(self.model.memory_type == memory_type).all()
    
    def list(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """List memory entries with pagination."""
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        return query.order_by(self.model.created_at.desc()).offset(offset).limit(limit).all()
    
    def update(self, key: str, value: Any = None, **kwargs) -> Optional[Any]:
        """Update a memory entry."""
        instance = self.get(key)
        if not instance:
            return None
        
        if value is not None:
            instance.value = value
        
        for field, val in kwargs.items():
            if hasattr(instance, field):
                setattr(instance, field, val)
        
        instance.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def delete(self, key: str) -> bool:
        """Delete a memory entry."""
        instance = self.get(key)
        if not instance:
            return False
        
        self.db.delete(instance)
        self.db.commit()
        return True
    
    def search(self, query_text: str, memory_types: Optional[List[str]] = None) -> List[Any]:
        """
        Search memory entries by key or value content.
        
        Note: This is a basic text search. For production use with
        large datasets, migrate to a vector database.
        """
        db_query = self._ensure_tenant_isolation(self.db.query(self.model))
        
        filters = [
            self.model.key.ilike(f"%{query_text}%"),
        ]
        
        # Add value search (JSON field - may need DB-specific handling)
        # This is a simplified version; production should use proper JSON search
        
        if memory_types:
            db_query = db_query.filter(self.model.memory_type.in_(memory_types))
        
        return db_query.filter(or_(*filters)).limit(50).all()
    
    def record_access(self, key: str) -> None:
        """Record an access to a memory entry."""
        instance = self.get(key)
        if instance:
            instance.access_count += 1
            instance.last_accessed_at = datetime.utcnow()
            self.db.commit()
    
    def cleanup_expired(self) -> int:
        """Remove expired memory entries. Returns count of deleted entries."""
        now = datetime.utcnow()
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        expired = query.filter(self.model.expires_at < now).all()
        
        count = len(expired)
        for instance in expired:
            self.db.delete(instance)
        
        self.db.commit()
        return count


class OrganizationMemoryService(MemoryServiceBase):
    """Service for organization-level memory operations."""
    
    def __init__(self, db: Session, organization_id: int):
        super().__init__(db, organization_id)
        self.model = OrganizationMemory
    
    def get_campaign_history(self) -> List[OrganizationMemory]:
        """Get historical campaign data."""
        return self.get_by_type("campaign")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get organizational preferences as a dictionary."""
        prefs = self.get_by_type("preference")
        return {p.key: p.value for p in prefs}
    
    def store_preference(self, key: str, value: Any) -> OrganizationMemory:
        """Store an organizational preference."""
        return self.create(key=key, value=value, memory_type="preference")


class ChannelMemoryService(MemoryServiceBase):
    """Service for channel-level memory operations."""
    
    def __init__(self, db: Session, organization_id: int, channel_id: int):
        super().__init__(db, organization_id)
        self.model = ChannelMemory
        self.channel_id = channel_id
    
    def _ensure_tenant_isolation(self, query):
        """Override to include channel_id filter."""
        return query.filter(
            and_(
                self.model.organization_id == self.organization_id,
                self.model.channel_id == self.channel_id
            )
        )
    
    def get_performance_history(self) -> List[ChannelMemory]:
        """Get channel performance history."""
        return self.get_by_type("performance")
    
    def get_engagement_patterns(self) -> List[ChannelMemory]:
        """Get audience engagement patterns."""
        return self.get_by_type("engagement")
    
    def store_learning(self, key: str, value: Any) -> ChannelMemory:
        """Store a channel-specific learning."""
        return self.create(key=key, value=value, memory_type="learning")


class AudienceMemoryService(MemoryServiceBase):
    """Service for audience-level memory operations."""
    
    def __init__(self, db: Session, organization_id: int, channel_id: Optional[int] = None):
        super().__init__(db, organization_id)
        self.model = AudienceMemory
        self.channel_id = channel_id
    
    def _ensure_tenant_isolation(self, query):
        """Override to include optional channel_id filter."""
        query = query.filter(self.model.organization_id == self.organization_id)
        if self.channel_id:
            query = query.filter(self.model.channel_id == self.channel_id)
        return query
    
    def get_demographics(self) -> List[AudienceMemory]:
        """Get demographic information."""
        return self.get_by_type("demographic")
    
    def get_interests(self) -> List[AudienceMemory]:
        """Get audience interests."""
        return self.get_by_type("interest")
    
    def get_sentiment_history(self) -> List[AudienceMemory]:
        """Get sentiment analysis history."""
        return self.get_by_type("sentiment")
    
    def store_behavior(self, segment_id: str, key: str, value: Any) -> AudienceMemory:
        """Store audience behavior data for a segment."""
        return self.create(
            key=key,
            value=value,
            memory_type="behavior",
            segment_id=segment_id
        )


class ContentMemoryService(MemoryServiceBase):
    """Service for content-level memory operations."""
    
    def __init__(self, db: Session, organization_id: int):
        super().__init__(db, organization_id)
        self.model = ContentMemory
    
    def get_content_history(self, content_type: str, content_id: int) -> List[ContentMemory]:
        """Get memory entries for specific content."""
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        return query.filter(
            and_(
                self.model.content_type == content_type,
                self.model.content_id == content_id
            )
        ).all()
    
    def get_generation_params(self, content_type: str, content_id: int) -> Optional[Dict[str, Any]]:
        """Get AI generation parameters used for content."""
        query = self._ensure_tenant_isolation(self.db.query(self.model))
        instance = query.filter(
            and_(
                self.model.content_type == content_type,
                self.model.content_id == content_id,
                self.model.memory_type == "generation"
            )
        ).first()
        return instance.value if instance else None
    
    def store_performance(self, content_type: str, content_id: int, 
                         performance_score: int, metrics: Dict[str, Any]) -> ContentMemory:
        """Store content performance data."""
        return self.create(
            key=f"{content_type}:{content_id}:performance",
            value={"score": performance_score, "metrics": metrics},
            memory_type="performance",
            content_type=content_type,
            content_id=content_id,
            performance_score=performance_score,
            engagement_metrics=metrics
        )


class AgentMemoryService(MemoryServiceBase):
    """Service for agent-level memory operations."""
    
    def __init__(self, db: Session, organization_id: int, agent_name: str):
        super().__init__(db, organization_id)
        self.model = AgentMemory
        self.agent_name = agent_name
    
    def _ensure_tenant_isolation(self, query):
        """Override to include agent_name filter."""
        return query.filter(
            and_(
                self.model.organization_id == self.organization_id,
                self.model.agent_name == self.agent_name
            )
        )
    
    def get_outcomes(self) -> List[AgentMemory]:
        """Get agent execution outcomes."""
        return self.get_by_type("outcome")
    
    def get_errors(self) -> List[AgentMemory]:
        """Get error patterns."""
        return self.get_by_type("error")
    
    def get_optimizations(self) -> List[AgentMemory]:
        """Get optimization suggestions."""
        return self.get_by_type("optimization")
    
    def store_parameter_effectiveness(
        self, key: str, value: Any, confidence: int = 5
    ) -> AgentMemory:
        """Store parameter effectiveness data."""
        return self.create(
            key=key,
            value=value,
            memory_type="parameter",
            confidence_score=confidence
        )
    
    def mark_as_learned(self, key: str) -> bool:
        """Mark a memory as incorporated into agent behavior."""
        instance = self.get(key)
        if instance:
            instance.is_learned = True
            self.db.commit()
            return True
        return False


def create_memory_service(
    db: Session,
    organization_id: int,
    service_type: str,
    **kwargs
) -> MemoryServiceBase:
    """
    Factory function to create appropriate memory service.
    
    Args:
        db: Database session
        organization_id: Organization ID for tenant isolation
        service_type: Type of service ('organization', 'channel', 'audience', 'content', 'agent')
        **kwargs: Additional arguments for specific services
    
    Returns:
        Appropriate MemoryService instance
    """
    services = {
        "organization": OrganizationMemoryService,
        "channel": ChannelMemoryService,
        "audience": AudienceMemoryService,
        "content": ContentMemoryService,
        "agent": AgentMemoryService,
    }
    
    if service_type not in services:
        raise ValueError(f"Unknown service type: {service_type}")
    
    return services[service_type](db, organization_id, **kwargs)
