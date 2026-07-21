"""
Database Connection Module

Manages PostgreSQL database connections using SQLAlchemy 2.x.
Provides session management and engine configuration.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from core.config import settings


# Create SQLAlchemy engine with PostgreSQL-optimized settings
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "options": "-c timezone=utc"  # Set timezone to UTC for all connections
    }
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as db:
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables by creating all models."""
    # Import all models to ensure they're registered with Base.metadata
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables (use with caution)."""
    from database import models  # noqa: F401
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.

    Usage in API:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
