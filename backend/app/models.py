"""
Database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import json
from pgvector.sqlalchemy import Vector
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    history = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="user", cascade="all, delete-orphan")


class AnalysisHistory(Base):
    """Store complete analysis results for dashboard"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rfp_filename = Column(String(500), nullable=False)
    num_provided_docs = Column(Integer, nullable=False)
    num_required_docs = Column(Integer, nullable=False)
    num_matched = Column(Integer, nullable=False)
    num_review = Column(Integer, default=0)
    num_missing = Column(Integer, nullable=False)
    completion_rate = Column(Float, nullable=False)
    api_cost = Column(Float, default=0.0)
    results_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="history")
    
    def set_results(self, results_dict):
        """Store results as JSON string"""
        self.results_json = json.dumps(results_dict)
    
    def get_results(self):
        """Get results as dictionary"""
        if self.results_json:
            return json.loads(self.results_json)
        return None


class DocumentChunk(Base):
    """Store document chunks with embeddings for RAG"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_filename = Column(String(500), nullable=False, index=True)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    embedding = Column(Vector(1536), nullable=False)  # text-embedding-3-small dimension
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="document_chunks")
    
    # Indexes are defined in migration file
    __table_args__ = (
        Index('idx_document_chunks_user_id', 'user_id'),
        Index('idx_document_chunks_filename', 'source_filename'),
    )
