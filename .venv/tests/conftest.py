import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the app and dependencies
import sys

sys.path.insert(0, r"C:\Users\leokn\PycharmProjects\bakeryApi\.venv")

from bakery import app, get_db
from models import Base

# Use the same database as the main app (Supabase)
from database import DATABASE_URL, API_KEY

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,
    },
    pool_pre_ping=True,
    pool_recycle=300,
)

TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the get_db dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Test client fixture"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Database session fixture for direct DB operations in tests"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# API key headers for authenticated requests
@pytest.fixture
def auth_headers():
    """Headers with API key for authenticated requests"""
    return {"X-API-Key": API_KEY}


# Test admin credentials for fixtures
TEST_ADMIN_USERNAME = "test_admin_fixture_user"
TEST_ADMIN_PASSWORD = "test_admin_fixture_pass_123"


@pytest.fixture
def admin_user_headers(client, db_session):
    """Headers with admin user token for user-authenticated requests"""
    from models import User
    from bakery import hash_password

    # Check if test admin exists in database
    admin_user = (
        db_session.query(User).filter(User.username == TEST_ADMIN_USERNAME).first()
    )

    if not admin_user:
        # Create test admin user directly in database
        admin_user = User(
            username=TEST_ADMIN_USERNAME,
            password_hash=hash_password(TEST_ADMIN_PASSWORD),
            is_approved=True,
            is_admin=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Login with test admin to get token
    response = client.post(
        "/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"X-Token": token}

    # If login fails, return empty token (tests will fail clearly)
    return {"X-Token": ""}
