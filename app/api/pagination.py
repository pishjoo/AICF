"""
Pagination Utilities

Helper functions for pagination across API endpoints.
"""

from fastapi import Query
from typing import Optional


class PaginationParams:
    """
    Pagination parameters for API requests.
    
    Usage:
        @router.get("/items")
        def list_items(pagination: PaginationParams = Depends()):
            ...
    """
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.limit = limit
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit."""
        return (self.page - 1) * self.limit
    
    @property
    def skip(self) -> int:
        """Alias for offset (SQLAlchemy convention)."""
        return self.offset


def paginate_query(query, total: int, page: int, limit: int):
    """
    Apply pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        total: Total count of items
        page: Current page number (1-indexed)
        limit: Items per page
        
    Returns:
        Tuple of (paginated_items, page, limit, total)
    """
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    return items, page, limit, total


def create_pagination_response(items: list, page: int, limit: int, total: int) -> dict:
    """
    Create standard pagination response dictionary.
    
    Args:
        items: List of items for current page
        page: Current page number
        limit: Items per page
        total: Total number of items
        
    Returns:
        Dictionary with pagination structure
    """
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total
    }
