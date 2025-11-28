"""
Database configuration
Supports SQLite (development) and PostgreSQL (production)
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app import config

# Create engine with proper connection args
connect_args = {}
if "sqlite" in config.DATABASE_URL:
    connect_args = {"check_same_thread": False}
elif "postgresql" in config.DATABASE_URL:
    connect_args = {"connect_timeout": 10}

# Create engine
engine = create_engine(
    config.DATABASE_URL,
    connect_args = connect_args,
    pool_pre_ping=True
)

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
