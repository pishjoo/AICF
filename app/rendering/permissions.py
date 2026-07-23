"""
Rendering RBAC Permissions

Defines rendering-specific permissions for the RBAC system.
"""

from typing import List, Dict


# Rendering permission slugs
RENDER_PERMISSIONS = {
    "render:create": "Create new rendering jobs",
    "render:view": "View rendering jobs and outputs",
    "render:cancel": "Cancel running or queued rendering jobs",
    "render:manage": "Full management of rendering jobs including retry and delete",
}


def get_rendering_permissions() -> Dict[str, str]:
    """Get all rendering permissions with descriptions."""
    return RENDER_PERMISSIONS.copy()


def get_rendering_permission_slugs() -> List[str]:
    """Get list of rendering permission slugs."""
    return list(RENDER_PERMISSIONS.keys())


def create_rendering_permissions_data() -> List[Dict]:
    """
    Create data for seeding rendering permissions into database.
    
    Returns list of dicts suitable for bulk insert into Permission table.
    """
    permissions = []
    
    for slug, description in RENDER_PERMISSIONS.items():
        resource, action = slug.split(":", 1)
        permissions.append({
            "name": f"Rendering - {action.capitalize()}",
            "slug": slug,
            "description": description,
            "resource": resource,
            "action": action,
        })
    
    return permissions


# Default role permission mappings for rendering
DEFAULT_ROLE_RENDERING_PERMISSIONS = {
    "owner": ["render:create", "render:view", "render:cancel", "render:manage"],
    "admin": ["render:create", "render:view", "render:cancel", "render:manage"],
    "manager": ["render:create", "render:view", "render:cancel"],
    "member": ["render:create", "render:view"],
    "viewer": ["render:view"],
}


def get_role_rendering_permissions(role_slug: str) -> List[str]:
    """Get rendering permissions for a specific role."""
    return DEFAULT_ROLE_RENDERING_PERMISSIONS.get(role_slug, [])
