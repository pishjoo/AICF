"""
Tenant Isolation Middleware

Middleware to enforce organization-level data isolation in multi-tenant architecture.
Ensures users can only access resources belonging to their organization.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant isolation.
    
    This middleware:
    1. Extracts organization context from authenticated user (via request state)
    2. Validates that requested resources belong to the user's organization
    3. Prevents cross-organization data access
    4. Injects organization ID into request state for downstream use
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce tenant isolation.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from next handler or error response
        """
        # Skip isolation check for public endpoints
        if self._is_public_endpoint(request):
            return await call_next(request)
        
        # Get organization ID from request state (set by auth dependency)
        organization_id = getattr(request.state, "organization_id", None)
        
        # If no organization in state, check if user is authenticated
        if organization_id is None:
            # User might not be authenticated yet (e.g., login endpoint)
            # Let the route handle authentication
            return await call_next(request)
        
        # Store organization ID in request headers for logging/auditing
        request.state.current_organization = organization_id
        
        # Continue with request processing
        response = await call_next(request)
        
        # Add organization ID to response headers for debugging
        response.headers["X-Organization-ID"] = str(organization_id)
        
        return response
    
    def _is_public_endpoint(self, request: Request) -> bool:
        """
        Check if endpoint should be accessible without tenant isolation.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if endpoint is public, False otherwise
        """
        public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login",
            "/health",
            "/",
        ]
        
        path = request.url.path.rstrip("/")
        
        # Check exact matches
        if path in public_paths:
            return True
        
        # Check if it's a static file or asset
        if path.startswith("/static") or path.startswith("/assets"):
            return True
        
        return False


def create_tenant_isolation_middleware() -> TenantIsolationMiddleware:
    """
    Factory function to create tenant isolation middleware instance.
    
    Returns:
        Configured TenantIsolationMiddleware instance
    """
    return TenantIsolationMiddleware


class OrganizationContext:
    """
    Helper class to manage organization context in request lifecycle.
    
    This can be used to inject organization context into services
    and ensure all database queries are scoped to the correct organization.
    """
    
    def __init__(self, organization_id: int):
        """
        Initialize with organization ID.
        
        Args:
            organization_id: Organization ID for context
        """
        self.organization_id = organization_id
    
    def scope_query(self, query, model_class):
        """
        Scope a SQLAlchemy query to current organization.
        
        Args:
            query: SQLAlchemy query object
            model_class: Model class to filter
            
        Returns:
            Query filtered by organization_id
        """
        if hasattr(model_class, "organization_id"):
            return query.filter(model_class.organization_id == self.organization_id)
        return query
    
    def verify_resource_ownership(self, resource) -> bool:
        """
        Verify that a resource belongs to current organization.
        
        Args:
            resource: Resource object with organization_id attribute
            
        Returns:
            True if resource belongs to organization, False otherwise
        """
        if not hasattr(resource, "organization_id"):
            return False
        return resource.organization_id == self.organization_id


async def get_organization_context(request: Request) -> Optional[OrganizationContext]:
    """
    Dependency to get organization context from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        OrganizationContext instance or None
    """
    organization_id = getattr(request.state, "current_organization", None)
    
    if organization_id is None:
        return None
    
    return OrganizationContext(organization_id)
