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
