"""
Test Rendering Security

Tests for RBAC permissions and tenant isolation in rendering.
"""

import pytest
from unittest.mock import Mock, patch

from app.rendering.permissions import (
    RENDER_PERMISSIONS,
    get_rendering_permissions,
    get_rendering_permission_slugs,
    create_rendering_permissions_data,
    get_role_rendering_permissions,
)


class TestRenderingPermissions:
    """Test rendering permission definitions."""
    
    def test_permissions_defined(self):
        """Test that all required permissions are defined."""
        assert "render:create" in RENDER_PERMISSIONS
        assert "render:view" in RENDER_PERMISSIONS
        assert "render:cancel" in RENDER_PERMISSIONS
        assert "render:manage" in RENDER_PERMISSIONS
    
    def test_permission_descriptions(self):
        """Test that permissions have descriptions."""
        for slug, description in RENDER_PERMISSIONS.items():
            assert description is not None
            assert len(description) > 0
    
    def test_get_rendering_permissions(self):
        """Test getting all permissions."""
        perms = get_rendering_permissions()
        
        assert isinstance(perms, dict)
        assert len(perms) == 4
        assert perms == RENDER_PERMISSIONS
    
    def test_get_permission_slugs(self):
        """Test getting permission slugs list."""
        slugs = get_rendering_permission_slugs()
        
        assert isinstance(slugs, list)
        assert len(slugs) == 4
        assert "render:create" in slugs
        assert "render:view" in slugs
        assert "render:cancel" in slugs
        assert "render:manage" in slugs
    
    def test_create_permissions_data(self):
        """Test creating data for database seeding."""
        data = create_rendering_permissions_data()
        
        assert isinstance(data, list)
        assert len(data) == 4
        
        for item in data:
            assert "name" in item
            assert "slug" in item
            assert "description" in item
            assert "resource" in item
            assert "action" in item
            
            # Verify format
            assert ":" in item["slug"]
            resource, action = item["slug"].split(":", 1)
            assert item["resource"] == resource
            assert item["action"] == action
    
    def test_role_permissions_owner(self):
        """Test owner role has all permissions."""
        perms = get_role_rendering_permissions("owner")
        
        assert "render:create" in perms
        assert "render:view" in perms
        assert "render:cancel" in perms
        assert "render:manage" in perms
    
    def test_role_permissions_admin(self):
        """Test admin role has all permissions."""
        perms = get_role_rendering_permissions("admin")
        
        assert "render:create" in perms
        assert "render:view" in perms
        assert "render:cancel" in perms
        assert "render:manage" in perms
    
    def test_role_permissions_manager(self):
        """Test manager role has limited permissions."""
        perms = get_role_rendering_permissions("manager")
        
        assert "render:create" in perms
        assert "render:view" in perms
        assert "render:cancel" in perms
        assert "render:manage" not in perms  # Managers cannot manage
    
    def test_role_permissions_member(self):
        """Test member role has basic permissions."""
        perms = get_role_rendering_permissions("member")
        
        assert "render:create" in perms
        assert "render:view" in perms
        assert "render:cancel" not in perms
        assert "render:manage" not in perms
    
    def test_role_permissions_viewer(self):
        """Test viewer role has read-only permissions."""
        perms = get_role_rendering_permissions("viewer")
        
        assert "render:view" in perms
        assert "render:create" not in perms
        assert "render:cancel" not in perms
        assert "render:manage" not in perms
    
    def test_unknown_role(self):
        """Test unknown role returns empty permissions."""
        perms = get_role_rendering_permissions("unknown_role")
        
        assert perms == []


class TestTenantIsolationInRendering:
    """Test tenant isolation for rendering components."""
    
    def test_storage_key_isolation(self):
        """Test storage keys include organization prefix."""
        from app.rendering.storage_extensions import RenderingStorageService
        from app.storage.providers import LocalStorageProvider
        
        provider = LocalStorageProvider()
        service = RenderingStorageService(provider)
        
        key = service._build_storage_key(
            organization_id=123,
            asset_type="videos",
            filename="test.mp4"
        )
        
        assert key.startswith("org_123/")
    
    def test_storage_key_with_episode(self):
        """Test storage key includes episode when provided."""
        from app.rendering.storage_extensions import RenderingStorageService
        from app.storage.providers import LocalStorageProvider
        
        provider = LocalStorageProvider()
        service = RenderingStorageService(provider)
        
        key = service._build_storage_key(
            organization_id=123,
            asset_type="videos",
            filename="test.mp4",
            episode_id=456
        )
        
        assert "org_123/" in key
        assert "episode_456/" in key
    
    def test_storage_key_with_job(self):
        """Test storage key includes job when provided."""
        from app.rendering.storage_extensions import RenderingStorageService
        from app.storage.providers import LocalStorageProvider
        
        provider = LocalStorageProvider()
        service = RenderingStorageService(provider)
        
        key = service._build_storage_key(
            organization_id=123,
            asset_type="intermediates",
            filename="frame.png",
            job_id=789
        )
        
        assert "org_123/" in key
        assert "job_789/" in key
    
    def test_url_access_denied_cross_org(self):
        """Test that accessing another org's URL raises error."""
        from app.rendering.storage_extensions import RenderingStorageService
        from app.storage.providers import LocalStorageProvider
        
        provider = LocalStorageProvider()
        service = RenderingStorageService(provider)
        
        with pytest.raises(PermissionError) as exc_info:
            service.get_video_url(
                organization_id=123,
                storage_key="org_456/videos/video.mp4"
            )
        
        assert "Access denied" in str(exc_info.value)
    
    def test_delete_denied_cross_org(self):
        """Test that deleting another org's asset raises error."""
        from app.rendering.storage_extensions import RenderingStorageService
        from app.storage.providers import LocalStorageProvider
        
        provider = LocalStorageProvider()
        service = RenderingStorageService(provider)
        
        with pytest.raises(PermissionError) as exc_info:
            service.delete_asset(
                organization_id=123,
                storage_key="org_456/videos/video.mp4"
            )
        
        assert "Access denied" in str(exc_info.value)


class TestDatabaseTenantIsolation:
    """Test tenant isolation at database model level."""
    
    def test_rendering_job_has_organization_id(self):
        """Test RenderingJob model has organization_id field."""
        from database.models import RenderingJob
        
        assert hasattr(RenderingJob, 'organization_id')
    
    def test_video_composition_has_organization_id(self):
        """Test VideoComposition model has organization_id field."""
        from database.models import VideoComposition
        
        assert hasattr(VideoComposition, 'organization_id')
    
    def test_render_output_has_organization_id(self):
        """Test RenderOutput model has organization_id field."""
        from database.models import RenderOutput
        
        assert hasattr(RenderOutput, 'organization_id')
    
    def test_models_inherit_tenant_mixin(self):
        """Test that rendering models inherit TenantMixin."""
        from database.models import RenderingJob, VideoComposition, RenderOutput
        from database.models import TenantMixin
        
        assert issubclass(RenderingJob, TenantMixin)
        assert issubclass(VideoComposition, TenantMixin)
        assert issubclass(RenderOutput, TenantMixin)
