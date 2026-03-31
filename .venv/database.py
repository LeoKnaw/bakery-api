from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=dotenv_path)

DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
API_KEY = os.getenv("API_KEY", "default-change-me")

if not DATABASE_PASSWORD:
    raise ValueError(
        "DATABASE_PASSWORD not found in environment variables. Check your .env file."
    )

DATABASE_URL = f"postgresql://postgres:{DATABASE_PASSWORD}@db.ikrhsnplcrewjvapwmkr.supabase.co:6543/postgres"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,
    },
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
