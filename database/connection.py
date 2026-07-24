"""
Database Connection Module

Manages database connections using SQLAlchemy 2.x.
Supports SQLite for development and PostgreSQL for production.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from core.config import settings


# Database URL
DATABASE_URL = settings.DATABASE_URL


# SQLite configuration (development)
if DATABASE_URL.startswith("sqlite"):

    engine = create_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO,
        connect_args={
            "check_same_thread": False
        }
    )


# PostgreSQL configuration (production)
else:

    engine = create_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        connect_args={
            "options": "-c timezone=utc"
        }
    )


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for models
Base = declarative_base()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
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
    """
    Initialize database tables.
    """

    from database import models

    Base.metadata.create_all(bind=engine)



def drop_db():
    """
    Drop all database tables.
    """

    from database import models

    Base.metadata.drop_all(bind=engine)



def get_db() -> Generator[Session, None, None]:
    """
    FastAPI database dependency.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()