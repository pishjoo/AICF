"""
Service Layer Exceptions

Custom exceptions for business logic errors.
"""


class ServiceError(Exception):
    """Base exception for service layer errors."""
    
    def __init__(self, message: str, code: str = "service_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(ServiceError):
    """
    Exception raised when a resource is not found.
    
    HTTP Status: 404
    """
    
    def __init__(self, resource_type: str, resource_id: int = None, message: str = None):
        if message is None:
            if resource_id is not None:
                message = f"{resource_type} with id {resource_id} not found"
            else:
                message = f"{resource_type} not found"
        
        super().__init__(message=message, code="not_found")
        self.resource_type = resource_type
        self.resource_id = resource_id


class PermissionDeniedError(ServiceError):
    """
    Exception raised when a user lacks permission for an action.
    
    HTTP Status: 403
    """
    
    def __init__(self, message: str = "Permission denied", action: str = None, resource: str = None):
        if action and resource:
            message = f"Permission denied: cannot {action} {resource}"
        
        super().__init__(message=message, code="permission_denied")
        self.action = action
        self.resource = resource


class DuplicateError(ServiceError):
    """
    Exception raised when attempting to create a duplicate resource.
    
    HTTP Status: 409
    """
    
    def __init__(self, resource_type: str, field: str = None, message: str = None):
        if message is None:
            if field:
                message = f"A {resource_type} with this {field} already exists"
            else:
                message = f"Duplicate {resource_type}"
        
        super().__init__(message=message, code="duplicate")
        self.resource_type = resource_type
        self.field = field


class ValidationError(ServiceError):
    """
    Exception raised when validation fails.
    
    HTTP Status: 422
    """
    
    def __init__(self, message: str, field: str = None):
        super().__init__(message=message, code="validation_error")
        self.field = field


class TenantIsolationError(ServiceError):
    """
    Exception raised when tenant isolation is violated.
    
    HTTP Status: 403
    """
    
    def __init__(self, message: str = "Tenant isolation violation"):
        super().__init__(message=message, code="tenant_isolation_error")
