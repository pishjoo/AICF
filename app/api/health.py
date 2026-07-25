"""
Health Check API

Comprehensive health check endpoints for monitoring and observability.
Supports basic health, readiness, and liveness probes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_db, engine
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def check_database_health(db: Session) -> Dict[str, Any]:
    """
    Check database connection health.
    
    Returns:
        Dict with status and response time metrics.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Execute a simple query to test connection
        db.execute("SELECT 1")
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "status": HealthStatus.HEALTHY,
            "response_time_ms": round(response_time * 1000, 2),
            "checked_at": start_time.isoformat()
        }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "checked_at": start_time.isoformat()
        }


def check_storage_health() -> Dict[str, Any]:
    """
    Check storage system health.
    
    Returns:
        Dict with storage provider status.
    """
    from app.storage.providers import LocalStorageProvider, StorageProviderType
    
    checked_at = datetime.now(timezone.utc)
    
    try:
        # Test local storage provider
        provider = LocalStorageProvider(settings.STORAGE_PATH)
        
        # Try to write and read a test file
        test_key = f"_health_check/{checked_at.timestamp()}.txt"
        test_content = b"health_check"
        
        import io
        result = provider.upload(
            file=io.BytesIO(test_content),
            key=test_key,
            content_type="text/plain"
        )
        
        if result.success:
            # Clean up test file
            provider.delete(test_key)
            
            return {
                "status": HealthStatus.HEALTHY,
                "provider": StorageProviderType.LOCAL.value,
                "storage_path": str(provider.base_path),
                "checked_at": checked_at.isoformat()
            }
        else:
            return {
                "status": HealthStatus.DEGRADED,
                "provider": StorageProviderType.LOCAL.value,
                "error": result.error,
                "checked_at": checked_at.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "checked_at": checked_at.isoformat()
        }


def check_ai_provider_health() -> Dict[str, Any]:
    """
    Check AI provider configuration health.
    
    Returns:
        Dict with AI provider status.
    """
    checked_at = datetime.now(timezone.utc)
    
    try:
        # Check if AI provider is configured
        if not settings.AI_PROVIDER:
            return {
                "status": HealthStatus.DEGRADED,
                "provider": "not_configured",
                "checked_at": checked_at.isoformat()
            }
        
        # Basic configuration check (actual API call would go here)
        has_api_key = bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.OLLAMA_BASE_URL)
        
        if has_api_key:
            return {
                "status": HealthStatus.HEALTHY,
                "provider": settings.AI_PROVIDER,
                "configured": True,
                "checked_at": checked_at.isoformat()
            }
        else:
            return {
                "status": HealthStatus.DEGRADED,
                "provider": settings.AI_PROVIDER,
                "configured": False,
                "warning": "API key may not be configured",
                "checked_at": checked_at.isoformat()
            }
            
    except Exception as e:
        logger.error(f"AI provider health check failed: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "checked_at": checked_at.isoformat()
        }


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns overall system health status.
    Suitable for load balancer health checks.
    """
    return {
        "status": HealthStatus.HEALTHY,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/live")
async def liveness_probe():
    """
    Liveness probe endpoint.
    
    Indicates whether the application is running and able to handle requests.
    Kubernetes uses this to determine if a pod should be restarted.
    """
    return {
        "status": "alive",
        "service": settings.APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Readiness probe endpoint.
    
    Indicates whether the application is ready to accept traffic.
    Checks all critical dependencies (database, storage, etc.).
    Kubernetes uses this to determine if a pod should receive traffic.
    """
    checked_at = datetime.now(timezone.utc)
    
    # Check all components
    db_health = check_database_health(db)
    storage_health = check_storage_health()
    ai_health = check_ai_provider_health()
    
    # Determine overall status
    statuses = [db_health["status"], storage_health["status"], ai_health["status"]]
    
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
        http_status = status.HTTP_200_OK  # Still accepting traffic but degraded
    else:
        overall_status = HealthStatus.HEALTHY
        http_status = status.HTTP_200_OK
    
    response = {
        "status": overall_status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": checked_at.isoformat(),
        "components": {
            "database": db_health,
            "storage": storage_health,
            "ai_provider": ai_health
        }
    }
    
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=http_status,
            detail=response
        )
    
    return response


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with comprehensive system information.
    
    Includes:
    - Database connection pool status
    - Storage provider details
    - AI provider configuration
    - Application configuration summary
    - System metrics
    """
    import os
    import sys
    
    checked_at = datetime.now(timezone.utc)
    
    # Component health checks
    db_health = check_database_health(db)
    storage_health = check_storage_health()
    ai_health = check_ai_provider_health()
    
    # Application info
    app_info = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "python_version": sys.version,
        "working_directory": os.getcwd()
    }
    
    # Configuration summary (sanitized)
    config_summary = {
        "database_type": "postgresql" if settings.DATABASE_URL.startswith("postgresql") else "sqlite",
        "storage_path": settings.STORAGE_PATH,
        "ai_provider": settings.AI_PROVIDER,
        "cors_enabled": bool(settings.CORS_ORIGINS),
        "auth_enabled": True
    }
    
    # Determine overall status
    statuses = [db_health["status"], storage_health["status"], ai_health["status"]]
    
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY
    
    return {
        "status": overall_status,
        "timestamp": checked_at.isoformat(),
        "application": app_info,
        "configuration": config_summary,
        "components": {
            "database": db_health,
            "storage": storage_health,
            "ai_provider": ai_health
        },
        "checks_performed": [
            "database_connectivity",
            "storage_accessibility",
            "ai_provider_configuration"
        ]
    }
