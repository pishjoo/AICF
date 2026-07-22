"""
Test Configuration for AICF v2

Provides pytest fixtures for database testing with automatic cleanup.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

# Set pythonpath for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Base, get_db
from database import models  # noqa: F401 - Ensure all models are loaded


# Test database URL (in-memory SQLite for fast tests)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine with SQLite-compatible settings
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# Session factory for tests
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    
    Creates all tables before each test and drops them after.
    This ensures complete isolation between tests.
    """
    # Create all tables for this test
    Base.metadata.create_all(bind=test_engine)
    
    # Start a transaction
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to this connection
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        # Rollback all changes to ensure clean state for next test
        session.close()
        transaction.rollback()
        connection.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with database dependency overridden.
    
    This fixture overrides the FastAPI database dependency to use
    the test database session.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    
    def override_get_db() -> Generator[Session, None, None]:
        """Override database dependency for testing."""
        try:
            yield db_session
        finally:
            pass
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Remove override after test
    app.dependency_overrides.clear()


@contextmanager
def get_test_db_session() -> Generator[Session, None, None]:
    """
    Context manager for test database sessions.
    
    Usage:
        with get_test_db_session() as db:
            # use db session
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        # Drop all tables
        Base.metadata.drop_all(bind=test_engine)
