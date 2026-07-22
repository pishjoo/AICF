"""
Standard API Response Formats

Consistent response structures for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict


class SuccessResponse(BaseModel):
    """
    Standard success response format.
    
    {
        "success": true,
        "data": {},
        "message": ""
    }
    """
    success: bool = Field(default=True, description="Indicates successful operation")
    data: Optional[Any] = Field(default=None, description="Response payload")
    message: str = Field(default="", description="Success message")


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    {
        "success": false,
        "error": {
            "code": "",
            "message": ""
        }
    }
    """
    success: bool = Field(default=False, description="Indicates failed operation")
    error: ErrorDetail = Field(..., description="Error details")


class PaginatedResponse(BaseModel):
    """
    Standard paginated response format.
    
    {
        "items": [],
        "page": 1,
        "limit": 20,
        "total": 100
    }
    """
    items: list = Field(default_factory=list, description="List of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    
    @classmethod
    def create(cls, items: list, page: int, limit: int, total: int):
        """Factory method to create paginated response."""
        return cls(
            items=items,
            page=page,
            limit=limit,
            total=total
        )
