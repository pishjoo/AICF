"""
Health Check Endpoints

Provides /health, /readiness, and /liveness endpoints for monitoring.
Checks database, Redis, and storage connectivity.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import time

from database.connection import get_db, engine
from core.config import settings

logger = logging.getLogger("health")

router = APIRouter(tags=["Health"])


def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    start_time = time.time()
    
    try:
        db = SessionLocal()
        # Execute a simple query to test connection
        db.execute("SELECT 1")
        db.close()
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }


def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    start_time = time.time()
    
    try:
        from app.jobs.queue import RedisJobQueue
        
        # Try to connect to Redis
        redis_queue = RedisJobQueue(redis_url=settings.REDIS_URL)
        
        if not redis_queue.connected:
            return {
                "status": "unhealthy",
                "error": "Failed to connect to Redis",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Ping Redis
        redis_queue.redis.ping()
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "url": settings.REDIS_URL.replace(settings.REDIS_PASSWORD, "***") if settings.REDIS_PASSWORD else settings.REDIS_URL,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except ImportError:
        return {
            "status": "not_configured",
            "message": "Redis not installed or configured",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }


def check_storage() -> Dict[str, Any]:
    """Check storage provider connectivity."""
    start_time = time.time()
    
    try:
        from app.storage.providers import LocalStorageProvider, StorageProviderType
        
        # For now, check local storage (production would check configured provider)
        provider = LocalStorageProvider(base_path=settings.STORAGE_PATH)
        
        # Test write capability
        test_key = "_health_check_test_file.txt"
        test_content = b"health check"
        
        import io
        result = provider.upload(
            file=io.BytesIO(test_content),
            key=test_key,
            content_type="text/plain"
        )
        
        if not result.success:
            return {
                "status": "unhealthy",
                "error": f"Upload test failed: {result.error}",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Clean up test file
        provider.delete(test_key)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "provider": provider.provider_type.value,
            "base_path": str(provider.base_path),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns overall system health status.
    """
    return {
        "status": "healthy",
        "service": "aicf-api",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint.
    
    Verifies all critical dependencies are available.
    Used by load balancers to determine if service should receive traffic.
    """
    checks = {}
    all_healthy = True
    
    # Check database
    db_check = check_database()
    checks["database"] = db_check
    if db_check["status"] != "healthy":
        all_healthy = False
    
    # Check Redis (optional)
    redis_check = check_redis()
    checks["redis"] = redis_check
    # Redis is optional, don't fail readiness if not configured
    
    # Check storage
    storage_check = check_storage()
    checks["storage"] = storage_check
    if storage_check["status"] != "healthy":
        all_healthy = False
    
    overall_status = "ready" if all_healthy else "not_ready"
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, status_code


@router.get("/liveness")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Verifies the application is still running and responsive.
    Used by orchestrators to determine if container should be restarted.
    """
    return {
        "status": "alive",
        "service": "aicf-api",
        "uptime_seconds": time.time(),  # Would use actual uptime in production
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with all component statuses.
    
    Provides comprehensive system health information.
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "storage": check_storage()
    }
    
    # Count healthy checks
    healthy_count = sum(1 for c in checks.values() if c["status"] == "healthy")
    total_count = len(checks)
    
    return {
        "overall_status": "healthy" if healthy_count == total_count else "degraded",
        "healthy_checks": healthy_count,
        "total_checks": total_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Import SessionLocal for health checks
from database.connection import SessionLocal
