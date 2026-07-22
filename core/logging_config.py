"""
AICF Logging System

Centralized logging configuration for request logging, error logging,
and user action logging.
"""

import logging
import sys
from datetime import datetime
from typing import Optional
from fastapi import Request


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Setup application logging.
    
    Args:
        level: Logging level
        log_file: Optional file path for log output
        use_colors: Enable colored console output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("aicf")
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if use_colors:
        console_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logging()


def log_request(request: Request, response_status: int, duration_ms: float):
    """
    Log HTTP request details.
    
    Args:
        request: FastAPI request object
        response_status: HTTP response status code
        duration_ms: Request processing time in milliseconds
    """
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    
    logger.info(
        f"REQUEST: {method} {path} - {response_status} - {duration_ms:.2f}ms - IP: {client_ip}"
    )


def log_error(
    error: Exception,
    context: Optional[str] = None,
    user_id: Optional[int] = None,
    request_path: Optional[str] = None
):
    """
    Log error with context information.
    
    Args:
        error: Exception object
        context: Additional context about where error occurred
        user_id: ID of user who triggered the error
        request_path: Path of the request that caused the error
    """
    extra_context = []
    if context:
        extra_context.append(f"Context: {context}")
    if user_id:
        extra_context.append(f"User ID: {user_id}")
    if request_path:
        extra_context.append(f"Path: {request_path}")
    
    context_str = " | ".join(extra_context) if extra_context else ""
    
    logger.error(
        f"ERROR: {type(error).__name__}: {str(error)}" + (f" - {context_str}" if context_str else ""),
        exc_info=True
    )


def log_user_action(
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
    success: bool = True
):
    """
    Log user action for audit trail.
    
    Args:
        user_id: ID of user performing action
        action: Action performed (create, update, delete, etc.)
        resource_type: Type of resource (user, channel, playlist, etc.)
        resource_id: ID of affected resource
        details: Additional details about the action
        success: Whether action was successful
    """
    log_level = logging.INFO if success else logging.WARNING
    
    message_parts = [
        f"USER_ACTION: user_id={user_id}",
        f"action={action}",
        f"resource_type={resource_type}"
    ]
    
    if resource_id is not None:
        message_parts.append(f"resource_id={resource_id}")
    
    if details:
        message_parts.append(f"details={details}")
    
    if not success:
        message_parts.append("status=failed")
    
    message = " | ".join(message_parts)
    logger.log(log_level, message)


class RequestLoggingMiddleware:
    """
    Middleware to log all incoming requests and their duration.
    
    Usage:
        app.add_middleware(RequestLoggingMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        from starlette.requests import Request
        from starlette.responses import Response
        
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = datetime.now()
        
        # Call the next middleware/handler
        response = await self.app(scope, receive, send)
        
        # Calculate duration
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Log the request
        log_request(request, response.status_code if hasattr(response, 'status_code') else 200, duration_ms)
        
        return response
