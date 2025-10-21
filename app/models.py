"""
Database models for MCP Analytics Server Phase 2
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Dataset(Base):
    """Dataset registry with encrypted connection strings"""
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    connection_string_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    schemas = relationship("DatasetSchema", back_populates="dataset", cascade="all, delete-orphan")
    metadata_entries = relationship("Metadata", back_populates="dataset", cascade="all, delete-orphan")


class DatasetSchema(Base):
    """Schema information for each dataset"""
    __tablename__ = "dataset_schemas"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    is_nullable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="schemas")
    
    # Composite index for fast lookups
    __table_args__ = (
        {'extend_existing': True}
    )


class Metadata(Base):
    """AI-generated metadata for columns"""
    __tablename__ = "metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False)
    column_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # Short AI-generated description
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_used = Column(String(100), default="gpt-4o-mini", nullable=False)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="metadata_entries")


class QueryLog(Base):
    """Query execution logs for tracking usage"""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    query = Column(Text, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    execution_time_ms = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    client_info = Column(JSON, nullable=True)  # Store MCP client info

