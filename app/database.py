"""
Database connection and session management
"""
import os
from dotenv import load_dotenv
from contextlib import contextmanager

# Load environment variables
load_dotenv()
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import psycopg2

from app.models import Base

# Metadata database URL (for storing datasets, schemas, metadata)
METADATA_DATABASE_URL = os.getenv('DATABASE_URL', '')
if METADATA_DATABASE_URL.startswith('postgres://'):
    METADATA_DATABASE_URL = METADATA_DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine for metadata database
metadata_engine = create_engine(
    METADATA_DATABASE_URL,
    poolclass=NullPool,  # No connection pooling for metadata DB
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=metadata_engine)


def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=metadata_engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Get database session as context manager"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_dataset_connection(connection_string: str):
    """Create a direct psycopg2 connection to a dataset database"""
    # Normalize connection string
    if connection_string.startswith('postgres://'):
        connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(connection_string)


def test_connection(connection_string: str) -> tuple[bool, str]:
    """Test if a database connection string is valid"""
    try:
        conn = get_dataset_connection(connection_string)
        conn.close()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)

