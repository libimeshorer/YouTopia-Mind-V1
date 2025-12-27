"""SQLAlchemy database models"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Float, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from src.database.db import Base


class Tenant(Base):
    """Tenant model - represents a company/organization"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name = Column(String, nullable=False)
    clerk_org_id = Column(String, nullable=True, index=True)  # Optional: for Clerk organization linking
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    clones = relationship("Clone", back_populates="tenant", cascade="all, delete-orphan")


class Clone(Base):
    """Clone model - represents a person within an organization (tenant)"""
    __tablename__ = "clones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    clerk_user_id = Column(String, unique=True, nullable=False, index=True)
    
    # Name fields (extracted from Clerk)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    
    description = Column(Text, nullable=True)
    status = Column(Enum('active', 'inactive', name='clone_status'), default='active', nullable=False)
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="clones")
    documents = relationship("Document", back_populates="clone", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="clone", cascade="all, delete-orphan")
    training_status = relationship("TrainingStatus", back_populates="clone", uselist=False, cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="clone", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="clone", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="clone", cascade="all, delete-orphan")
    data_sources = relationship("DataSource", back_populates="clone", cascade="all, delete-orphan")


class Session(Base):
    """Session model - represents a conversation between external user and clone"""
    __tablename__ = "sessions"
    
    # Unique numeric ID (BIGSERIAL auto-increment)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Which clone is in this conversation
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # External user info (if known)
    external_user_name = Column(String, nullable=True)
    external_user_id = Column(String, nullable=True, index=True)  # Platform-specific ID
    external_platform = Column(Enum('slack', 'web', 'api', 'email', name='session_platform'), nullable=True)
    
    # Session metadata
    started_at = Column(DateTime, server_default=text('now()'), nullable=False)
    last_message_at = Column(DateTime, server_default=text('now()'), nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    
    # Full conversation JSON (computed on-demand, nullable)
    conversation_json = Column(JSON, nullable=True)  # Built from messages when requested
    
    # Session status
    status = Column(Enum('active', 'closed', name='session_status'), default='active', nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Document(Base):
    """Document model - stores document metadata"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)  # Size in bytes
    type = Column(String, nullable=False)  # MIME type or file extension
    file_hash = Column(String, nullable=True, index=True)  # SHA256 hash for duplicate detection
    
    status = Column(Enum('pending', 'processing', 'complete', 'error', name='document_status'), default='pending', nullable=False)
    
    s3_key = Column(String, nullable=False)  # S3 object key
    chunks_count = Column(Integer, default=0, nullable=False)  # Number of chunks created
    is_core = Column(Boolean, default=False, nullable=False)  # Whether this is a core/foundational document

    uploaded_at = Column(DateTime, server_default=text('now()'), nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When document was processed and chunks were created
    error_message = Column(Text, nullable=True)  # Error message if status is error
    
    # Relationships
    clone = relationship("Clone", back_populates="documents")


class Insight(Base):
    """Insight model - stores clone insights (text or voice)"""
    __tablename__ = "insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    type = Column(Enum('text', 'voice', name='insight_type'), nullable=False)
    
    audio_url = Column(String, nullable=True)  # S3 URL for voice recordings
    transcription_id = Column(String, nullable=True)  # Reference to transcription job
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="insights")


class TrainingStatus(Base):
    """Training status model - tracks clone's training progress"""
    __tablename__ = "training_status"
    
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), primary_key=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)  # 0-100
    documents_count = Column(Integer, default=0, nullable=False)
    insights_count = Column(Integer, default=0, nullable=False)
    integrations_count = Column(Integer, default=0, nullable=False)
    thresholds_json = Column(JSON, nullable=False, server_default=text("'{}'::json"))
    achievements_json = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="training_status")


class Integration(Base):
    """Integration model - stores third-party integration connections"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    
    platform = Column(Enum('slack', 'gmail', 'email', 'notion', name='integration_platform'), nullable=False)
    status = Column(Enum('connected', 'disconnected', 'error', name='integration_status'), default='disconnected', nullable=False)
    
    credentials_encrypted = Column(Text, nullable=True)  # Encrypted OAuth tokens
    last_sync_at = Column(DateTime, nullable=True)
    sync_settings_json = Column(JSON, nullable=True, server_default=text("'{}'::json"))
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="integrations")
    data_sources = relationship("DataSource", back_populates="integration", cascade="all, delete-orphan")


class Message(Base):
    """Message model - stores conversation history between user and clone"""
    __tablename__ = "messages"
    
    # Identification
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message details
    role = Column(Enum('external_user', 'clone', name='message_role'), nullable=False)
    content = Column(Text, nullable=False)
    
    # External user info (for external_user messages)
    external_user_name = Column(String, nullable=True)
    
    # RAG context (for clone messages)
    rag_context_json = Column(JSON, nullable=True)
    
    # Feedback (for clone messages)
    feedback_rating = Column(Integer, nullable=True)  # -1, 1, or null
    feedback_comment = Column(Text, nullable=True)
    
    # Performance metrics (for clone messages)
    tokens_used = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=text('now()'), nullable=False, index=True)
    
    # Relationships
    clone = relationship("Clone", back_populates="messages")
    session = relationship("Session", back_populates="messages")


class DataSource(Base):
    """DataSource model - tracks specific data sources within integrations (e.g., Slack channels, Gmail labels)"""
    __tablename__ = "data_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    source_type = Column(String, nullable=False)  # "slack_channel", "gmail_label", "email_folder", etc.
    source_identifier = Column(String, nullable=False)  # Channel ID, label name, folder path, etc.
    display_name = Column(String, nullable=True)  # Human-readable name (e.g., "#general" or "Work/Inbox")
    
    is_active = Column(Boolean, default=True, nullable=False)  # Can disable without deleting
    chunks_count = Column(Integer, default=0, nullable=False)  # Number of chunks ingested from this source
    
    last_synced_at = Column(DateTime, nullable=True)  # Last successful sync
    last_error = Column(Text, nullable=True)  # Last error message if sync failed
    sync_settings_json = Column(JSON, nullable=True, server_default=text("'{}'::json"))  # Source-specific sync settings
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'), nullable=False)
    
    # Relationships
    clone = relationship("Clone", back_populates="data_sources")
    integration = relationship("Integration", back_populates="data_sources")
