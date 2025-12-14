"""SQLAlchemy database models"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from src.database.db import Base


class Tenant(Base):
    """Tenant model - represents a company/organization"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    clerk_org_id = Column(String, nullable=True, index=True)  # Optional: for Clerk organization linking
    # TODO: Update tenant creation logic when onboarding enterprise customers with multiple clones per tenant
    # For now: 1:1 tenant per clone (solopreneur model)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    clones = relationship("Clone", back_populates="tenant", cascade="all, delete-orphan")


class Clone(Base):
    """Clone model - represents a person within an organization (tenant)"""
    __tablename__ = "clones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    clerk_user_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, inactive, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="clones")
    documents = relationship("Document", back_populates="clone", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="clone", cascade="all, delete-orphan")
    training_status = relationship("TrainingStatus", back_populates="clone", uselist=False, cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="clone", cascade="all, delete-orphan")


class User(Base):
    """User model - DEPRECATED: kept for migration purposes, use Clone instead"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - DEPRECATED
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="user", cascade="all, delete-orphan")
    training_status = relationship("TrainingStatus", back_populates="user", uselist=False, cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Document model - stores document metadata"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # DEPRECATED: kept for migration
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    type = Column(String, nullable=False)  # MIME type or file extension
    status = Column(String, nullable=False, default="pending")  # pending, processing, complete, error
    s3_key = Column(String, nullable=False)  # S3 object key
    chunks_count = Column(Integer, default=0)  # Number of chunks created
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When document was processed and chunks were created
    error_message = Column(Text, nullable=True)  # Error message if status is error
    
    # Relationships
    clone = relationship("Clone", back_populates="documents")
    user = relationship("User", back_populates="documents")  # DEPRECATED


class Insight(Base):
    """Insight model - stores clone insights (text or voice)"""
    __tablename__ = "insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # DEPRECATED: kept for migration
    content = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # "text" or "voice"
    audio_url = Column(String, nullable=True)  # S3 URL for voice recordings
    transcription_id = Column(String, nullable=True)  # Reference to transcription job
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="insights")
    user = relationship("User", back_populates="insights")  # DEPRECATED


class TrainingStatus(Base):
    """Training status model - tracks clone's training progress"""
    __tablename__ = "training_status"
    
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # DEPRECATED: kept for migration
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
    clone = relationship("Clone", back_populates="training_status")
    user = relationship("User", back_populates="training_status")  # DEPRECATED


class Integration(Base):
    """Integration model - stores third-party integration connections"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # DEPRECATED: kept for migration
    type = Column(String, nullable=False)  # slack, email, gmail, etc.
    status = Column(String, nullable=False, default="disconnected")  # connected, disconnected, error
    credentials_encrypted = Column(Text, nullable=True)  # Encrypted OAuth tokens
    last_sync_at = Column(DateTime, nullable=True)
    sync_settings_json = Column(JSON, nullable=True, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="integrations")
    user = relationship("User", back_populates="integrations")  # DEPRECATED
