"""
AICF Main Application

FastAPI application entry point with production-ready configuration.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import logging
import time
from datetime import datetime

from core.config import settings
from core.logging_config import logger, log_error, log_request, RequestLoggingMiddleware
from database.connection import engine, Base
from app.api.routes import router
from app.middleware.tenant_isolation import TenantIsolationMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="AICF v2 API",
        version="2.0.0",
        description="""
AI Content Factory multi-tenant SaaS platform

## Features

* **Multi-tenant Architecture** - Complete organization isolation
* **Channel Management** - YouTube channel profiles and strategies
* **Content Planning** - Playlists and episodes management
* **AI-Powered Production** - Automated content creation workflows
* **Asset Management** - Media storage and organization
* **Role-Based Access Control** - Granular permissions system

## Authentication

All endpoints require JWT Bearer token authentication except:
- `/auth/register`
- `/auth/login`
- `/health`
""",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "AICF Support",
            "email": "support@aicf.example.com"
        },
        license_info={
            "name": "Proprietary",
        },
    )
    
    # Configure CORS with security restrictions
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Organization-ID"],
        expose_headers=["X-Organization-ID", "X-Request-ID"],
        max_age=600,
    )
    
    # Add tenant isolation middleware
    app.add_middleware(TenantIsolationMiddleware)
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Include API router
    app.include_router(router, prefix=settings.API_PREFIX)
    
    # Register global exception handlers
    register_exception_handlers(app)
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        
        # Create database tables
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        
        logger.info(f"AI Provider: {settings.AI_PROVIDER}")
        logger.info(f"Storage path: {settings.STORAGE_PATH}")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down AICF application")
    
    return app


def register_exception_handlers(app: FastAPI):
    """Register global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent response format."""
        log_error(
            exc,
            context=f"HTTP {exc.status_code}",
            request_path=request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail
                }
            },
            headers=getattr(exc, "headers", None)
        )
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        log_error(
            exc,
            context="Validation Error",
            request_path=request.url.path
        )
        
        errors = exc.errors()
        error_messages = []
        for error in errors:
            field = ".".join(str(x) for x in error.get("loc", []))
            message = error.get("msg", "Invalid value")
            error_messages.append(f"{field}: {message}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "; ".join(error_messages)
                }
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors."""
        log_error(
            exc,
            context="Database Error",
            request_path=request.url.path
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "A database error occurred. Please try again later."
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        log_error(
            exc,
            context="Unexpected Error",
            request_path=request.url.path
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later."
                }
            }
        )
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

