"""SQLAlchemy database models"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from src.database.db import Base


class User(Base):
    """User model - links Clerk user_id to backend data"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="user", cascade="all, delete-orphan")
    training_status = relationship("TrainingStatus", back_populates="user", uselist=False, cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Document model - stores document metadata"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    type = Column(String, nullable=False)  # MIME type or file extension
    status = Column(String, nullable=False, default="pending")  # pending, processing, complete, error
    s3_key = Column(String, nullable=False)  # S3 object key
    chunks_count = Column(Integer, default=0)  # Number of chunks created
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    error_message = Column(Text, nullable=True)  # Error message if status is error
    
    # Relationships
    user = relationship("User", back_populates="documents")


class Insight(Base):
    """Insight model - stores user insights (text or voice)"""
    __tablename__ = "insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # "text" or "voice"
    audio_url = Column(String, nullable=True)  # S3 URL for voice recordings
    transcription_id = Column(String, nullable=True)  # Reference to transcription job
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="insights")


class TrainingStatus(Base):
    """Training status model - tracks user's training progress"""
    __tablename__ = "training_status"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)  # 0-100
    documents_count = Column(Integer, default=0, nullable=False)
    insights_count = Column(Integer, default=0, nullable=False)
    integrations_count = Column(Integer, default=0, nullable=False)
    thresholds_json = Column(JSON, nullable=False, default={
        "minDocuments": 1,
        "minInsights": 1,
        "minIntegrations": 1,
    })
    achievements_json = Column(JSON, nullable=False, default=[])
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="training_status")


class Integration(Base):
    """Integration model - stores third-party integration connections"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # slack, email, gmail, etc.
    status = Column(String, nullable=False, default="disconnected")  # connected, disconnected, error
    credentials_encrypted = Column(Text, nullable=True)  # Encrypted OAuth tokens
    last_sync_at = Column(DateTime, nullable=True)
    sync_settings_json = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="integrations")
