import sys

import pytest
from fastapi.testclient import TestClient

# Add .venv directory to path for imports
sys.path.insert(0, r"C:\Users\leokn\PycharmProjects\bakeryApi\.venv")

from database_test import TestingSessionLocal, drop_test_db, init_test_db
from models_test import User
from test_app import TEST_API_KEY, app, hash_password


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database for each test."""
    init_test_db()
    yield
    drop_test_db()


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    """Database session fixture for direct DB operations in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers():
    """Headers with API key for authenticated requests."""
    return {"X-API-Key": TEST_API_KEY}


# Test admin credentials for fixtures
TEST_ADMIN_USERNAME = "test_admin_fixture_user"
TEST_ADMIN_PASSWORD = "test_admin_fixture_pass_123"


@pytest.fixture
def admin_user_headers(client, db_session):
    """Headers with admin user token for user-authenticated requests."""
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
