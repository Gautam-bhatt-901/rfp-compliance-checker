"""
Database configuration with connection pooling
Supports SQLite (development) and PostgreSQL (production)
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app import config

# Create engine with proper connection args and pooling
connect_args = {}

if "sqlite" in config.DATABASE_URL:
    connect_args = {"check_same_thread": False}
    # SQLite doesn't support connection pooling well
    engine = create_engine(
        config.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True
    )
    
elif "postgresql" in config.DATABASE_URL:
    connect_args = {
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }
    
    # PostgreSQL with connection pooling
    engine = create_engine(
        config.DATABASE_URL,
        connect_args=connect_args,
        poolclass=QueuePool,
        pool_size=config.DB_POOL_SIZE,            # Max connections in pool
        max_overflow=config.DB_MAX_OVERFLOW,      # Extra connections when needed
        pool_pre_ping=True,                       # Verify connections before use
        pool_recycle=config.DB_POOL_RECYCLE,      # Recycle connections after 1 hour
        echo=False,                               # Set True for SQL debugging
        echo_pool=False                           # Set True for pool debugging
    )
    
    # Event listener for connection setup
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_conn, connection_record):
        """Set search path and ensure extensions are loaded"""
        cursor = dbapi_conn.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()

else:
    # Fallback
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
