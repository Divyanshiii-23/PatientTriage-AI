"""
Database connection management for PostgreSQL.

Handles connection pooling, session management, and engine configuration.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

# Database configuration from environment variables
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://triage_user:triage_pass@localhost:5432/triage_db'
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Maintain 20 connections
    max_overflow=30,  # Allow 30 additional connections under load
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
    echo=False,  # Set to True for SQL logging in development
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db_engine():
    """
    Get the database engine.
    
    Returns:
        SQLAlchemy engine instance
    """
    return engine


def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session for dependency injection.
    
    Usage with FastAPI:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db_session)):
            # Use db session
            pass
    
    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Event listener to enable connection debugging (optional)
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log new database connections."""
    pass  # Add logging here if needed


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Validate connection on checkout from pool."""
    pass  # Connection validation handled by pool_pre_ping
