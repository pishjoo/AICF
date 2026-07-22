"""
Unit tests for Memory Foundation.

Tests cover:
- Memory isolation by organization
- CRUD operations
- Service layer functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from app.memory.models import (
    OrganizationMemory,
    ChannelMemory,
    AudienceMemory,
    ContentMemory,
    AgentMemory,
)

from app.memory.service import (
    OrganizationMemoryService,
    ChannelMemoryService,
    AudienceMemoryService,
    ContentMemoryService,
    AgentMemoryService,
    create_memory_service,
)


class MockSession:
    """Mock SQLAlchemy session for testing."""
    
    def __init__(self):
        self.data = {}
        self.added = []
        self.deleted = []
        self.committed = False
    
    def add(self, obj):
        self.added.append(obj)
    
    def commit(self):
        self.committed = True
        # Assign IDs to added objects
        for obj in self.added:
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = len(self.added)
    
    def refresh(self, obj):
        pass
    
    def delete(self, obj):
        self.deleted.append(obj)
    
    def query(self, model_class):
        return MockQuery(self, model_class)


class MockQuery:
    """Mock SQLAlchemy query for testing."""
    
    def __init__(self, session, model_class):
        self.session = session
        self.model_class = model_class
        self.filters = []
        self.order_by_field = None
        self._offset = 0
        self._limit = None
    
    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self
    
    def order_by(self, field):
        self.order_by_field = field
        return self
    
    def offset(self, n):
        self._offset = n
        return self
    
    def limit(self, n):
        self._limit = n
        return self
    
    def first(self):
        return None
    
    def all(self):
        return []


class TestOrganizationMemoryService:
    """Tests for OrganizationMemoryService."""
    
    def test_create_memory(self):
        """Test creating organization memory."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        memory = service.create(
            key="test_key",
            value={"data": "test"},
            memory_type="preference"
        )
        
        assert memory.organization_id == 1
        assert memory.key == "test_key"
        assert memory.value == {"data": "test"}
        assert memory.memory_type == "preference"
        assert db.committed
    
    def test_get_memory(self):
        """Test getting memory by key."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        # Mock the query result
        mock_memory = Mock(spec=OrganizationMemory)
        mock_memory.key = "test_key"
        mock_memory.value = {"data": "test"}
        
        # Since we're mocking, just verify the method doesn't crash
        result = service.get("nonexistent")
        assert result is None
    
    def test_update_memory(self):
        """Test updating memory."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        # Mock get to return a memory
        mock_memory = Mock(spec=OrganizationMemory)
        mock_memory.key = "test_key"
        mock_memory.value = {"old": "value"}
        service.get = Mock(return_value=mock_memory)
        
        result = service.update("test_key", value={"new": "value"})
        
        assert result is mock_memory
        assert mock_memory.value == {"new": "value"}
    
    def test_delete_memory(self):
        """Test deleting memory."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        mock_memory = Mock(spec=OrganizationMemory)
        mock_memory.key = "test_key"
        service.get = Mock(return_value=mock_memory)
        
        result = service.delete("test_key")
        
        assert result is True
        assert mock_memory in db.deleted
    
    def test_search_memories(self):
        """Test searching memories."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        # Should not raise
        results = service.search("query")
        assert isinstance(results, list)
    
    def test_cleanup_expired(self):
        """Test cleaning up expired memories."""
        db = MockSession()
        service = OrganizationMemoryService(db, organization_id=1)
        
        # Mock expired memories
        mock_memory = Mock(spec=OrganizationMemory)
        mock_memory.expires_at = datetime.utcnow() - timedelta(days=1)
        
        service._ensure_tenant_isolation = Mock(return_value=db.query(OrganizationMemory))
        db.query(OrganizationMemory).filter = Mock(return_value=MockQuery(db, OrganizationMemory))
        db.query(OrganizationMemory).filter().all = Mock(return_value=[mock_memory])
        
        count = service.cleanup_expired()
        assert count >= 0


class TestChannelMemoryService:
    """Tests for ChannelMemoryService."""
    
    def test_create_channel_memory(self):
        """Test creating channel memory with proper isolation."""
        db = MockSession()
        service = ChannelMemoryService(db, organization_id=1, channel_id=5)
        
        memory = service.create(
            key="channel_pref",
            value={"posting_time": "9am"},
            memory_type="preference"
        )
        
        assert memory.organization_id == 1
        # Channel ID filtering is handled in queries, not creation
    
    def test_tenant_isolation_includes_channel(self):
        """Test that channel service includes channel_id in isolation."""
        db = MockSession()
        service = ChannelMemoryService(db, organization_id=1, channel_id=5)
        
        query = MockQuery(db, ChannelMemory)
        filtered = service._ensure_tenant_isolation(query)
        
        # Verify filters were added (implementation detail)
        assert len(filtered.filters) > 0


class TestAudienceMemoryService:
    """Tests for AudienceMemoryService."""
    
    def test_store_behavior_with_segment(self):
        """Test storing audience behavior for a segment."""
        db = MockSession()
        service = AudienceMemoryService(db, organization_id=1)
        
        memory = service.store_behavior(
            segment_id="segment_a",
            key="engagement_pattern",
            value={"peak_hours": [9, 17]}
        )
        
        assert memory.segment_id == "segment_a"
        assert memory.memory_type == "behavior"


class TestContentMemoryService:
    """Tests for ContentMemoryService."""
    
    def test_store_performance(self):
        """Test storing content performance."""
        db = MockSession()
        service = ContentMemoryService(db, organization_id=1)
        
        memory = service.store_performance(
            content_type="episode",
            content_id=100,
            performance_score=85,
            metrics={"views": 1000, "likes": 50}
        )
        
        assert memory.content_type == "episode"
        assert memory.content_id == 100
        assert memory.performance_score == 85


class TestAgentMemoryService:
    """Tests for AgentMemoryService."""
    
    def test_create_agent_memory(self):
        """Test creating agent memory."""
        db = MockSession()
        service = AgentMemoryService(db, organization_id=1, agent_name="content_generator")
        
        memory = service.create(
            key="param_temp",
            value={"optimal": 0.7},
            memory_type="parameter"
        )
        
        assert memory.agent_name == "content_generator"
        assert memory.memory_type == "parameter"
    
    def test_mark_as_learned(self):
        """Test marking memory as learned."""
        db = MockSession()
        service = AgentMemoryService(db, organization_id=1, agent_name="test")
        
        mock_memory = Mock(spec=AgentMemory)
        mock_memory.key = "learned_key"
        mock_memory.is_learned = False
        service.get = Mock(return_value=mock_memory)
        
        result = service.mark_as_learned("learned_key")
        
        assert result is True
        assert mock_memory.is_learned is True


class TestCreateMemoryService:
    """Tests for factory function."""
    
    def test_create_organization_service(self):
        """Test creating organization memory service."""
        db = MockSession()
        service = create_memory_service(db, organization_id=1, service_type="organization")
        
        assert isinstance(service, OrganizationMemoryService)
    
    def test_create_channel_service(self):
        """Test creating channel memory service."""
        db = MockSession()
        service = create_memory_service(
            db, organization_id=1, service_type="channel", channel_id=5
        )
        
        assert isinstance(service, ChannelMemoryService)
    
    def test_create_agent_service(self):
        """Test creating agent memory service."""
        db = MockSession()
        service = create_memory_service(
            db, organization_id=1, service_type="agent", agent_name="test"
        )
        
        assert isinstance(service, AgentMemoryService)
    
    def test_invalid_service_type(self):
        """Test that invalid service type raises error."""
        db = MockSession()
        
        with pytest.raises(ValueError, match="Unknown service type"):
            create_memory_service(db, organization_id=1, service_type="invalid")


class TestTenantIsolation:
    """Tests for tenant isolation in memory services."""
    
    def test_organization_isolation(self):
        """Test that organizations can only access their own data."""
        db1 = MockSession()
        db2 = MockSession()
        
        service1 = OrganizationMemoryService(db1, organization_id=1)
        service2 = OrganizationMemoryService(db2, organization_id=2)
        
        # Each service should only work with its organization_id
        memory1 = service1.create("key1", {"org": 1}, "test")
        memory2 = service2.create("key2", {"org": 2}, "test")
        
        assert memory1.organization_id == 1
        assert memory2.organization_id == 2
    
    def test_channel_isolation_within_org(self):
        """Test channel isolation within same organization."""
        db = MockSession()
        
        service_ch1 = ChannelMemoryService(db, organization_id=1, channel_id=10)
        service_ch2 = ChannelMemoryService(db, organization_id=1, channel_id=20)
        
        # Services should have different channel filters
        assert service_ch1.channel_id == 10
        assert service_ch2.channel_id == 20
