"""
Test database configuration using SQLite in-memory.
This file provides a separate database setup for testing that doesn't
interact with the production Supabase database.
"""

from models_test import Base
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite in-memory database for fast, isolated tests
# Using StaticPool to share the same connection across all sessions
# This ensures the in-memory database persists across connections
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)


# Enable foreign key constraints in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=engine)


def init_test_db():
    """Create all tables in the test database."""
    Base.metadata.create_all(bind=engine)


def drop_test_db():
    """Drop all tables from the test database."""
    Base.metadata.drop_all(bind=engine)


def get_test_db():
    """Dependency override for getting a test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
