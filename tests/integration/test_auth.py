"""
Integration Tests for Authentication System

Tests for user registration, login, JWT validation, token refresh,
protected routes, and tenant isolation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from database.connection import Base, get_db
from database.models import User, Organization, Role, UserRole


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


from datetime import datetime

def create_test_organization(db):
    """Helper to create a test organization."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        description="Test organization for auth tests",
        updated_at=datetime.utcnow(),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def create_test_user(db, organization_id, email="test@example.com"):
    """Helper to create a test user."""
    from app.auth.password import hash_password
    
    user = User(
        organization_id=organization_id,
        email=email,
        password_hash=hash_password("SecurePass123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_role(db, organization_id, slug="member"):
    """Helper to create a test role."""
    role = Role(
        organization_id=organization_id,
        name="Member",
        slug=slug,
        description="Test role",
        is_builtin=True if slug == "member" else False,
        permissions=["channel:read", "episode:read"] if slug == "member" else [],
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def assign_role_to_user(db, organization_id, user_id, role_id):
    """Helper to assign a role to a user."""
    user_role = UserRole(
        organization_id=organization_id,
        user_id=user_id,
        role_id=role_id,
    )
    db.add(user_role)
    db.commit()
    return user_role


class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_success(self, client, db_session):
        """Test successful user registration."""
        org = create_test_organization(db_session)
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
                "organization_id": org.id,
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user was created
        user = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.full_name == "New User"
    
    def test_register_duplicate_email(self, client, db_session):
        """Test registration with duplicate email fails."""
        org = create_test_organization(db_session)
        create_test_user(db_session, org.id, "duplicate@example.com")
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123",
                "full_name": "Duplicate User",
                "organization_id": org.id,
            }
        )
        
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]
    
    def test_register_weak_password(self, client, db_session):
        """Test registration with weak password fails."""
        org = create_test_organization(db_session)
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",  # Too short, no complexity
                "full_name": "Weak User",
                "organization_id": org.id,
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_invalid_email(self, client, db_session):
        """Test registration with invalid email fails."""
        org = create_test_organization(db_session)
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
                "full_name": "Invalid User",
                "organization_id": org.id,
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_organization_not_found(self, client, db_session):
        """Test registration with non-existent organization fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
                "full_name": "Test User",
                "organization_id": 99999,
            }
        )
        
        assert response.status_code == 404


class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, db_session):
        """Test successful login."""
        org = create_test_organization(db_session)
        user = create_test_user(db_session, org.id)
        role = create_test_role(db_session, org.id)
        assign_role_to_user(db_session, org.id, user.id, role.id)
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, db_session):
        """Test login with wrong password fails."""
        org = create_test_organization(db_session)
        create_test_user(db_session, org.id)
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123",
            }
        )
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SecurePass123",
            }
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user fails."""
        org = create_test_organization(db_session)
        user = create_test_user(db_session, org.id)
        user.is_active = False
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
            }
        )
        
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"]


class TestJWTValidation:
    """Test JWT token validation."""
    
    def test_access_protected_route_with_valid_token(self, client, db_session):
        """Test accessing protected route with valid token."""
        org = create_test_organization(db_session)
        user = create_test_user(db_session, org.id)
        role = create_test_role(db_session, org.id)
        assign_role_to_user(db_session, org.id, user.id, role.id)
        
        # Login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
            }
        )
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # Access protected route
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == user.id
    
    def test_access_protected_route_without_token(self, client, db_session):
        """Test accessing protected route without token fails."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_access_protected_route_with_invalid_token(self, client, db_session):
        """Test accessing protected route with invalid token fails."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh endpoint."""
    
    def test_refresh_token_success(self, client, db_session):
        """Test successful token refresh."""
        org = create_test_organization(db_session)
        user = create_test_user(db_session, org.id)
        role = create_test_role(db_session, org.id)
        assign_role_to_user(db_session, org.id, user.id, role.id)
        
        # Login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
            }
        )
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Refresh tokens
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]
    
    def test_refresh_with_invalid_token(self, client, db_session):
        """Test refresh with invalid token fails."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == 401


class TestTenantIsolation:
    """Test tenant isolation functionality."""
    
    def test_user_cannot_access_other_organization_data(self, client, db_session):
        """Test that users cannot access data from other organizations."""
        # Create two organizations
        org1 = create_test_organization(db_session)
        org1.name = "Organization 1"
        org1.slug = "org-1"
        
        org2 = create_test_organization(db_session)
        org2.name = "Organization 2"
        org2.slug = "org-2"
        db_session.commit()
        
        # Create user in org1
        user1 = create_test_user(db_session, org1.id, "user1@org1.com")
        
        # Login as user1
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user1@org1.com",
                "password": "SecurePass123",
            }
        )
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # Get current user info - should show org1
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == org1.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
