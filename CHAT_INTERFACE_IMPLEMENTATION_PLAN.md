# YouTopia Chat Interface - Complete Implementation Plan

**Version:** 1.0
**Date:** 2025-12-31
**Status:** Planning Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [User Model & Requirements](#user-model--requirements)
3. [Architecture Overview](#architecture-overview)
4. [Database Schema Changes](#database-schema-changes)
5. [Backend Implementation](#backend-implementation)
6. [Frontend Implementation](#frontend-implementation)
7. [Authentication & Access Control](#authentication--access-control)
8. [Implementation Phases](#implementation-phases)
9. [Technical Specifications](#technical-specifications)
10. [Security & Privacy](#security--privacy)
11. [Testing Strategy](#testing-strategy)
12. [Future Enhancements](#future-enhancements)

---

## Executive Summary

This plan outlines the implementation of a conversational interface for YouTopia, enabling clone owners (e.g., Tiffany) to interact with their AI clones and grant access to their customers. The interface follows familiar chat patterns (ChatGPT, Claude, iMessage) with YouTopia's design system.

### Key Features

✅ **Chat Interface**: Simple, familiar chat UI with message history
✅ **Access Control**: Clone owners grant access to customers via email
✅ **Session Management**: Resume previous conversations, create new ones
✅ **Feedback System**: Thumbs up/down on clone responses
✅ **Clone Slugs**: Human-readable URLs (e.g., `/chat/tiffany-ai`)
✅ **Guest Authentication**: Minimal friction for customers (magic link)

### Success Metrics

- Clone owner can grant access to customers in <30 seconds
- Customer can start chatting in <60 seconds (including magic link)
- 90% of responses include relevant RAG context
- Average response time <5 seconds (including LLM latency)
- Customer satisfaction >80% (via feedback system)

---

## User Model & Requirements

### 1. User Types

**Clone Owner (e.g., Tiffany)**
- Has a Clerk account (existing auth)
- Creates one AI clone via training process
- Can chat with own clone (for testing)
- Grants access to customers via email
- Views all customer interactions in "Manage Clone" page
- Edits clone slug (default: "{name}-ai")

**Customer (e.g., Tiffany's clients)**
- Minimal guest account (no password)
- Authenticates via magic link (30-day expiry)
- Granted access by clone owner
- Has separate conversation history per clone
- Can resume previous sessions or start new ones
- Provides feedback on clone responses (thumbs up/down)

### 2. Core Requirements

**Early Stage (MVP - Weeks 1-4)**
- ✅ Simple chat UI (message bubbles, input, send)
- ✅ RAG-powered responses from clone's knowledge
- ✅ Typing indicator while generating response
- ✅ Session history (list past conversations)
- ✅ Access control (email-based allowlist)
- ✅ Clone slug URLs
- ✅ Feedback system (thumbs up/down)
- ✅ Magic link authentication for customers

**Later Stage (Post-MVP)**
- ⏳ Streaming responses (SSE)
- ⏳ "Manage Clone" page for owners (view all customer chats)
- ⏳ Analytics (popular questions, satisfaction scores)
- ⏳ Shareable link generation (auto-allowlist on email entry)
- ⏳ Customizable magic link expiry

### 3. User Flows

**Flow 1: Clone Owner Grants Access**
1. Tiffany logs in to YouTopia
2. Goes to Settings → Access Control
3. Adds customer email: `jane@example.com`
4. System creates access grant record
5. Tiffany shares clone URL: `youtopia.com/chat/tiffany-ai`

**Flow 2: Customer First Visit**
1. Jane visits `youtopia.com/chat/tiffany-ai`
2. Enters email address
3. System checks if email has access (from step 1.3 above)
4. If yes: sends magic link to jane@example.com
5. Jane clicks link, authenticated for 30 days
6. Sees chat interface, can start conversation

**Flow 3: Customer Return Visit**
1. Jane visits `youtopia.com/chat/tiffany-ai` again
2. If authenticated (magic link still valid): auto-resume last session
3. Can view history sidebar, switch to previous sessions
4. Can start new conversation

**Flow 4: Customer Provides Feedback**
1. Tiffany AI sends a response
2. Jane sees thumbs up/down buttons below message
3. Clicks thumbs down
4. System saves feedback_rating=-1 to Message record
5. (Later) Tiffany can see feedback in analytics

---

## Architecture Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │  Chat Page     │  │  Settings Page │  │  Manage Clone    │   │
│  │  /chat/:slug   │  │  /settings     │  │  (Future)        │   │
│  └────────────────┘  └────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (HTTP/REST)
┌──────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Chat Router                                                │ │
│  │  POST /api/chat/sessions                                    │ │
│  │  POST /api/chat/sessions/:id/messages                       │ │
│  │  GET  /api/chat/sessions/:id                                │ │
│  │  GET  /api/chat/sessions                                    │ │
│  │  POST /api/chat/feedback                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Access Control Router                                      │ │
│  │  POST /api/access/grants (grant access to customer)         │ │
│  │  GET  /api/access/grants (list granted customers)           │ │
│  │  DELETE /api/access/grants/:id (revoke access)              │ │
│  │  POST /api/access/check (verify customer access)            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Clone Router (Extend Existing)                             │ │
│  │  PUT /api/clone/slug (update clone slug)                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Services Layer                           │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │ ChatService  │  │ AccessControl   │  │ GuestAuthService  │   │
│  │              │  │ Service         │  │ (Magic Link)      │   │
│  └──────────────┘  └─────────────────┘  └───────────────────┘   │
│         │                                          │              │
│         ▼                                          ▼              │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │SessionManager│  │ CloneDataAccess │  │ EmailService      │   │
│  │(Existing)    │  │ (Existing)      │  │ (AWS SES)         │   │
│  └──────────────┘  └─────────────────┘  └───────────────────┘   │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐  ┌─────────────────┐                           │
│  │PromptBuilder │  │  RAGRetriever   │                           │
│  │(Existing)    │  │  (Existing)     │                           │
│  └──────────────┘  └─────────────────┘                           │
│         │                      │                                  │
│         ▼                      ▼                                  │
│  ┌──────────────┐  ┌─────────────────┐                           │
│  │  LLMClient   │  │ CloneVectorStore│                           │
│  │  (Existing)  │  │  (Existing)     │                           │
│  └──────────────┘  └─────────────────┘                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Database (PostgreSQL)                         │
│  • clones (+ slug, access_type columns)                          │
│  • clone_access_grants (new table)                               │
│  • guest_users (new table)                                       │
│  • magic_links (new table)                                       │
│  • sessions (existing)                                           │
│  • messages (existing, + feedback fields)                        │
└──────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. Authentication Strategy: Magic Link via Guest Accounts**

**Complexity vs Option A (Clerk accounts):** +20% code, -80% customer friction

Implementation:
- Customer enters email at `/chat/tiffany-ai`
- Backend checks access grant, creates guest_user + magic_link
- Email sent via AWS SES with one-time link
- Link contains JWT token (30-day expiry)
- Token stored in localStorage, auto-attached to API requests

**Why Magic Link?**
- ✅ No password friction (industry standard for guest access)
- ✅ Email verification (prevents abuse)
- ✅ Secure (token expires, can be revoked)
- ✅ Familiar UX (Slack, Notion, Linear all use this)

**2. Access Control: Email Allowlist**

**Complexity vs Shareable Link:** Hybrid adds only +50% code for flexibility

Implementation:
- Clone owner adds emails to allowlist in Settings
- (Optional) Clone owner generates shareable link that auto-adds email on entry
- Backend validates email before creating magic link

**Why Allowlist?**
- ✅ Granular control (owner decides who has access)
- ✅ Audit trail (track who was granted access, when)
- ✅ Revocable (owner can remove access anytime)
- ✅ Scalable (can add bulk import later)

**3. Session Management: Auto-Resume with History**

Implementation:
- On chat page load, fetch most recent active session
- Auto-load messages from that session
- Show "New Conversation" button in header
- Show "View History" sidebar (collapsible) with list of past sessions

**Why Auto-Resume?**
- ✅ Matches ChatGPT/Claude UX (user expectation)
- ✅ Reduces friction (no "which conversation?" modal)
- ✅ Clear escape hatch (explicit "New Conversation" button)

**4. Progress Indication: Typing Indicator (Phase 1) → Streaming (Phase 2)**

**Phase 1:** Typing indicator (3 animated dots)
- Simple to implement (~50 lines)
- Shows activity while waiting for response
- Familiar UX (iMessage, Slack)

**Phase 2:** Streaming responses (SSE)
- Better UX (see tokens as they arrive)
- More complex (~200 lines)
- Requires Server-Sent Events setup

**Why Phased?**
- ✅ MVP ships faster with typing indicator
- ✅ Can validate core chat flow before adding streaming
- ✅ Streaming is enhancement, not blocker

---

## Database Schema Changes

### 1. New Tables

**Table: `clone_access_grants`**
```sql
CREATE TABLE clone_access_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clone_id UUID NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
    granted_to_email VARCHAR NOT NULL,
    granted_by_clerk_user_id VARCHAR NOT NULL,

    -- Optional fields
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NULL,  -- NULL = no expiry
    revoked_at TIMESTAMP NULL,  -- NULL = still active

    -- Metadata
    grant_source VARCHAR DEFAULT 'manual',  -- 'manual' | 'link'
    notes TEXT NULL,

    -- Indexes
    UNIQUE(clone_id, granted_to_email),
    INDEX idx_clone_access_grants_clone_id (clone_id),
    INDEX idx_clone_access_grants_email (granted_to_email)
);
```

**Table: `guest_users`**
```sql
CREATE TABLE guest_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR NOT NULL UNIQUE,

    -- Name (optional, can be added later by user or inferred)
    first_name VARCHAR NULL,
    last_name VARCHAR NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_guest_users_email (email)
);
```

**Table: `magic_links`**
```sql
CREATE TABLE magic_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_user_id UUID NOT NULL REFERENCES guest_users(id) ON DELETE CASCADE,
    clone_id UUID NOT NULL REFERENCES clones(id) ON DELETE CASCADE,

    -- Token (hashed for security)
    token_hash VARCHAR NOT NULL UNIQUE,

    -- Expiry
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR NULL,
    user_agent TEXT NULL,

    -- Indexes
    INDEX idx_magic_links_token_hash (token_hash),
    INDEX idx_magic_links_guest_user (guest_user_id),
    INDEX idx_magic_links_expires_at (expires_at)
);
```

### 2. Modify Existing Tables

**Table: `clones`** (add columns)
```sql
ALTER TABLE clones ADD COLUMN slug VARCHAR UNIQUE;
ALTER TABLE clones ADD COLUMN access_type VARCHAR DEFAULT 'private';
-- access_type: 'private' (owner only) | 'allowlist' (granted customers)

-- Generate default slugs for existing clones
UPDATE clones SET slug = LOWER(CONCAT(first_name, '-ai')) WHERE slug IS NULL;

-- Create index
CREATE INDEX idx_clones_slug ON clones(slug);
```

**Table: `sessions`** (add columns)
```sql
ALTER TABLE sessions ADD COLUMN guest_user_id UUID REFERENCES guest_users(id) ON DELETE SET NULL;
ALTER TABLE sessions ADD COLUMN is_owner_session BOOLEAN DEFAULT FALSE;
-- is_owner_session: TRUE if clone owner chatting with own clone

CREATE INDEX idx_sessions_guest_user (guest_user_id);
```

**Table: `messages`** (feedback columns already exist)
```sql
-- No changes needed! feedback_rating and feedback_comment already exist
-- feedback_rating: -1 (thumbs down), 1 (thumbs up), NULL (no feedback)
-- feedback_comment: Optional text feedback
```

### 3. Migration Script

**File:** `alembic/versions/XXX_add_chat_interface_tables.py`

```python
"""Add chat interface tables and columns

Revision ID: XXX
Revises: YYY
Create Date: 2025-12-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'XXX'
down_revision = 'YYY'

def upgrade():
    # Create guest_users table
    op.create_table(
        'guest_users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_guest_users_email', 'guest_users', ['email'])

    # Create magic_links table
    op.create_table(
        'magic_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('guest_user_id', UUID(as_uuid=True), sa.ForeignKey('guest_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('clone_id', UUID(as_uuid=True), sa.ForeignKey('clones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
    )
    op.create_index('idx_magic_links_token_hash', 'magic_links', ['token_hash'])
    op.create_index('idx_magic_links_guest_user', 'magic_links', ['guest_user_id'])
    op.create_index('idx_magic_links_expires_at', 'magic_links', ['expires_at'])

    # Create clone_access_grants table
    op.create_table(
        'clone_access_grants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('clone_id', UUID(as_uuid=True), sa.ForeignKey('clones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('granted_to_email', sa.String(), nullable=False),
        sa.Column('granted_by_clerk_user_id', sa.String(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('grant_source', sa.String(), server_default='manual', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('idx_clone_access_grants_clone_id', 'clone_access_grants', ['clone_id'])
    op.create_index('idx_clone_access_grants_email', 'clone_access_grants', ['granted_to_email'])

    # Add columns to clones table
    op.add_column('clones', sa.Column('slug', sa.String(), nullable=True, unique=True))
    op.add_column('clones', sa.Column('access_type', sa.String(), server_default='private', nullable=False))

    # Generate default slugs for existing clones
    # Note: This uses raw SQL because we need to handle null values
    from sqlalchemy import text
    op.execute(text("""
        UPDATE clones
        SET slug = LOWER(CONCAT(COALESCE(first_name, 'clone'), '-ai'))
        WHERE slug IS NULL
    """))

    op.create_index('idx_clones_slug', 'clones', ['slug'])

    # Add columns to sessions table
    op.add_column('sessions', sa.Column('guest_user_id', UUID(as_uuid=True), sa.ForeignKey('guest_users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('sessions', sa.Column('is_owner_session', sa.Boolean(), server_default='false', nullable=False))
    op.create_index('idx_sessions_guest_user', 'sessions', ['guest_user_id'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_sessions_guest_user', 'sessions')
    op.drop_index('idx_clones_slug', 'clones')
    op.drop_index('idx_clone_access_grants_email', 'clone_access_grants')
    op.drop_index('idx_clone_access_grants_clone_id', 'clone_access_grants')
    op.drop_index('idx_magic_links_expires_at', 'magic_links')
    op.drop_index('idx_magic_links_guest_user', 'magic_links')
    op.drop_index('idx_magic_links_token_hash', 'magic_links')
    op.drop_index('idx_guest_users_email', 'guest_users')

    # Drop columns
    op.drop_column('sessions', 'is_owner_session')
    op.drop_column('sessions', 'guest_user_id')
    op.drop_column('clones', 'access_type')
    op.drop_column('clones', 'slug')

    # Drop tables
    op.drop_table('clone_access_grants')
    op.drop_table('magic_links')
    op.drop_table('guest_users')
```

---

## Backend Implementation

### Phase 1: Core Services & Models

#### 1.1 Database Models

**File:** `src/database/models.py` (add new models)

```python
class GuestUser(Base):
    """Guest user model - customers who chat with clones"""
    __tablename__ = "guest_users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    email = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)

    # Relationships
    magic_links = relationship("MagicLink", back_populates="guest_user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="guest_user")


class MagicLink(Base):
    """Magic link for passwordless authentication"""
    __tablename__ = "magic_links"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    guest_user_id = Column(UUID(as_uuid=True), ForeignKey("guest_users.id", ondelete="CASCADE"), nullable=False, index=True)
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    guest_user = relationship("GuestUser", back_populates="magic_links")
    clone = relationship("Clone")


class CloneAccessGrant(Base):
    """Access grant for customers to chat with clone"""
    __tablename__ = "clone_access_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    clone_id = Column(UUID(as_uuid=True), ForeignKey("clones.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_to_email = Column(String, nullable=False, index=True)
    granted_by_clerk_user_id = Column(String, nullable=False)
    granted_at = Column(DateTime, server_default=text('now()'), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    grant_source = Column(String, server_default='manual', nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    clone = relationship("Clone")
```

**Update Clone model:**
```python
# Add to Clone model:
slug = Column(String, unique=True, nullable=True, index=True)
access_type = Column(String, server_default='private', nullable=False)

# Add relationships
access_grants = relationship("CloneAccessGrant", back_populates="clone", cascade="all, delete-orphan")
```

**Update Session model:**
```python
# Add to Session model:
guest_user_id = Column(UUID(as_uuid=True), ForeignKey("guest_users.id", ondelete="SET NULL"), nullable=True, index=True)
is_owner_session = Column(Boolean, server_default='false', nullable=False)

# Add relationship
guest_user = relationship("GuestUser", back_populates="sessions")
```

#### 1.2 Access Control Service

**File:** `src/services/access_control_service.py`

```python
"""Access control service for clone chat permissions"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from src.database.models import CloneAccessGrant, Clone
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AccessControlService:
    """Manages access control for clone chat"""

    def __init__(self, db: Session):
        self.db = db

    def grant_access(
        self,
        clone_id: UUID,
        granted_to_email: str,
        granted_by_clerk_user_id: str,
        expires_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        grant_source: str = 'manual'
    ) -> CloneAccessGrant:
        """Grant access to a customer"""
        # Check if grant already exists
        existing = self.db.query(CloneAccessGrant).filter(
            and_(
                CloneAccessGrant.clone_id == clone_id,
                CloneAccessGrant.granted_to_email == granted_to_email.lower(),
                CloneAccessGrant.revoked_at.is_(None)
            )
        ).first()

        if existing:
            logger.info("Access already granted", clone_id=str(clone_id), email=granted_to_email)
            return existing

        # Create new grant
        grant = CloneAccessGrant(
            clone_id=clone_id,
            granted_to_email=granted_to_email.lower(),
            granted_by_clerk_user_id=granted_by_clerk_user_id,
            expires_at=expires_at,
            notes=notes,
            grant_source=grant_source
        )
        self.db.add(grant)
        self.db.commit()
        self.db.refresh(grant)

        logger.info("Access granted", clone_id=str(clone_id), email=granted_to_email, grant_id=str(grant.id))
        return grant

    def check_access(self, clone_id: UUID, email: str) -> bool:
        """Check if email has access to clone"""
        # Check clone access type
        clone = self.db.query(Clone).filter(Clone.id == clone_id).first()
        if not clone:
            return False

        if clone.access_type == 'private':
            # Private: no external access (owner only, checked elsewhere)
            return False

        if clone.access_type == 'allowlist':
            # Check if email has active grant
            grant = self.db.query(CloneAccessGrant).filter(
                and_(
                    CloneAccessGrant.clone_id == clone_id,
                    CloneAccessGrant.granted_to_email == email.lower(),
                    CloneAccessGrant.revoked_at.is_(None),
                    # Check expiry
                    CloneAccessGrant.expires_at.is_(None) | (CloneAccessGrant.expires_at > datetime.utcnow())
                )
            ).first()

            return grant is not None

        return False

    def revoke_access(self, grant_id: UUID) -> bool:
        """Revoke access grant"""
        grant = self.db.query(CloneAccessGrant).filter(CloneAccessGrant.id == grant_id).first()
        if not grant:
            return False

        grant.revoked_at = datetime.utcnow()
        self.db.commit()

        logger.info("Access revoked", grant_id=str(grant_id), email=grant.granted_to_email)
        return True

    def list_grants(self, clone_id: UUID, include_revoked: bool = False) -> List[CloneAccessGrant]:
        """List all access grants for a clone"""
        query = self.db.query(CloneAccessGrant).filter(CloneAccessGrant.clone_id == clone_id)

        if not include_revoked:
            query = query.filter(CloneAccessGrant.revoked_at.is_(None))

        return query.order_by(CloneAccessGrant.granted_at.desc()).all()
```

#### 1.3 Guest Authentication Service

**File:** `src/services/guest_auth_service.py`

```python
"""Guest authentication service using magic links"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
import secrets
import hashlib
from src.database.models import GuestUser, MagicLink, Clone
from src.services.access_control_service import AccessControlService
from src.utils.email import send_magic_link_email
from src.utils.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class GuestAuthService:
    """Manages guest user authentication via magic links"""

    MAGIC_LINK_EXPIRY_DAYS = 30
    TOKEN_LENGTH = 32  # bytes (64 hex chars)

    def __init__(self, db: Session):
        self.db = db
        self.access_control = AccessControlService(db)

    def request_magic_link(
        self,
        email: str,
        clone_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Request a magic link for guest authentication.
        Returns (success: bool, message: str)
        """
        email = email.lower().strip()

        # Verify clone exists
        clone = self.db.query(Clone).filter(Clone.id == clone_id).first()
        if not clone:
            return False, "Clone not found"

        # Check if email has access
        has_access = self.access_control.check_access(clone_id, email)
        if not has_access:
            logger.warning("Access denied for email", email=email, clone_id=str(clone_id))
            return False, "Access denied. Please contact the clone owner for access."

        # Get or create guest user
        guest_user = self.db.query(GuestUser).filter(GuestUser.email == email).first()
        if not guest_user:
            guest_user = GuestUser(email=email)
            self.db.add(guest_user)
            self.db.flush()
            logger.info("Created new guest user", email=email)

        # Generate magic link token
        token = secrets.token_urlsafe(self.TOKEN_LENGTH)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Create magic link record
        magic_link = MagicLink(
            guest_user_id=guest_user.id,
            clone_id=clone_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=self.MAGIC_LINK_EXPIRY_DAYS),
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(magic_link)
        self.db.commit()

        # Send email
        magic_link_url = f"{settings.frontend_url}/auth/magic-link?token={token}&clone_id={clone_id}"
        send_magic_link_email(
            to_email=email,
            clone_name=f"{clone.first_name} {clone.last_name}" if clone.first_name else clone.email,
            magic_link_url=magic_link_url,
            expiry_days=self.MAGIC_LINK_EXPIRY_DAYS
        )

        logger.info("Magic link sent", email=email, clone_id=str(clone_id))
        return True, "Magic link sent! Check your email."

    def verify_magic_link(self, token: str, clone_id: UUID) -> Optional[GuestUser]:
        """
        Verify magic link token and return guest user if valid.
        Returns None if invalid/expired.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find magic link
        magic_link = self.db.query(MagicLink).filter(
            MagicLink.token_hash == token_hash,
            MagicLink.clone_id == clone_id
        ).first()

        if not magic_link:
            logger.warning("Invalid magic link token")
            return None

        # Check if expired
        if magic_link.expires_at < datetime.utcnow():
            logger.warning("Expired magic link", email=magic_link.guest_user.email)
            return None

        # Check if already used (optional: allow reuse within expiry period)
        # For now, we allow reuse

        # Mark as used (first time only)
        if not magic_link.used_at:
            magic_link.used_at = datetime.utcnow()

        # Update guest user last seen
        guest_user = magic_link.guest_user
        guest_user.last_seen_at = datetime.utcnow()

        self.db.commit()

        logger.info("Magic link verified", email=guest_user.email, clone_id=str(clone_id))
        return guest_user

    def generate_jwt_for_guest(self, guest_user: GuestUser, clone_id: UUID) -> str:
        """Generate JWT token for guest user session"""
        from jose import jwt
        from datetime import datetime, timedelta

        payload = {
            "sub": str(guest_user.id),
            "email": guest_user.email,
            "clone_id": str(clone_id),
            "type": "guest",
            "exp": datetime.utcnow() + timedelta(days=self.MAGIC_LINK_EXPIRY_DAYS)
        }

        token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
        return token
```

#### 1.4 Chat Service

**File:** `src/services/chat_service.py`

```python
"""Chat service for clone conversations"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime
from src.database.models import Session as SessionModel, Message, Clone, GuestUser
from src.services.session_manager import SessionManager
from src.services.clone_data_access import CloneDataAccessService
from src.llm.prompt_builder import PromptBuilder
from src.llm.client import LLMClient
from src.personality.profile import PersonalityProfile
from src.utils.aws import S3Client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Orchestrates chat conversations between users and clones"""

    def __init__(self, clone_id: UUID, tenant_id: UUID, db: Session):
        self.clone_id = clone_id
        self.tenant_id = tenant_id
        self.db = db
        self.session_manager = SessionManager(db)
        self.data_access = CloneDataAccessService(clone_id, tenant_id, db)
        self.llm_client = LLMClient()

        # Get vector store and build prompt builder
        vector_store = self.data_access.get_vector_store()
        from src.rag.retriever import RAGRetriever
        self.rag_retriever = RAGRetriever(clone_vector_store=vector_store)
        self.prompt_builder = PromptBuilder(llm_client=self.llm_client, rag_retriever=self.rag_retriever)

    def get_or_create_session(
        self,
        guest_user_id: Optional[UUID] = None,
        is_owner: bool = False,
        external_user_name: Optional[str] = None
    ) -> SessionModel:
        """
        Get most recent active session or create new one.
        For guests: one active session at a time.
        For owners: can have multiple sessions.
        """
        # Find most recent active session
        query = self.db.query(SessionModel).filter(
            SessionModel.clone_id == self.clone_id,
            SessionModel.status == 'active'
        )

        if guest_user_id:
            query = query.filter(SessionModel.guest_user_id == guest_user_id)
        elif is_owner:
            query = query.filter(SessionModel.is_owner_session == True)

        recent_session = query.order_by(SessionModel.last_message_at.desc()).first()

        if recent_session:
            logger.info("Resuming existing session", session_id=recent_session.id)
            return recent_session

        # Create new session
        session = self.session_manager.create_session(
            clone_id=self.clone_id,
            external_user_name=external_user_name,
            external_platform='web'
        )

        # Set guest_user_id or is_owner_session
        if guest_user_id:
            session.guest_user_id = guest_user_id
        elif is_owner:
            session.is_owner_session = True

        self.db.commit()
        self.db.refresh(session)

        logger.info("Created new session", session_id=session.id, is_owner=is_owner)
        return session

    def send_message(
        self,
        session_id: int,
        user_message: str,
        external_user_name: Optional[str] = None
    ) -> Dict:
        """
        Send user message and generate clone response.
        Returns dict with user_message and clone_message.
        """
        start_time = datetime.utcnow()

        # Add user message
        user_msg = self.session_manager.add_message(
            session_id=session_id,
            role='external_user',
            content=user_message,
            external_user_name=external_user_name
        )

        # Load personality profile
        personality_profile = self._load_personality_profile()

        # Build messages for LLM
        messages = self.prompt_builder.build_messages(
            user_query=user_message,
            profile=personality_profile,
            include_context=True,
            clone_id=self.clone_id,
            tenant_id=self.tenant_id
        )

        # Generate response
        response = self.llm_client.generate(messages=messages)

        # Calculate response time
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Extract RAG context (from PromptBuilder)
        rag_context = self.rag_retriever.retrieve(user_message, top_k=5)

        # Add clone message
        clone_msg = self.session_manager.add_message(
            session_id=session_id,
            role='clone',
            content=response.content,
            rag_context_json={"chunks": rag_context},
            tokens_used=response.usage.total_tokens if response.usage else None,
            response_time_ms=response_time_ms
        )

        logger.info("Generated clone response",
                   session_id=session_id,
                   response_time_ms=response_time_ms,
                   tokens_used=response.usage.total_tokens if response.usage else None)

        return {
            "user_message": {
                "id": str(user_msg.id),
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
                "external_user_name": user_msg.external_user_name
            },
            "clone_message": {
                "id": str(clone_msg.id),
                "role": clone_msg.role,
                "content": clone_msg.content,
                "created_at": clone_msg.created_at.isoformat(),
                "rag_context": clone_msg.rag_context_json,
                "tokens_used": clone_msg.tokens_used,
                "response_time_ms": clone_msg.response_time_ms,
                "feedback_rating": clone_msg.feedback_rating
            }
        }

    def get_session_history(self, guest_user_id: Optional[UUID] = None, is_owner: bool = False) -> List[Dict]:
        """Get all sessions for guest user or owner"""
        query = self.db.query(SessionModel).filter(SessionModel.clone_id == self.clone_id)

        if guest_user_id:
            query = query.filter(SessionModel.guest_user_id == guest_user_id)
        elif is_owner:
            query = query.filter(SessionModel.is_owner_session == True)

        sessions = query.order_by(SessionModel.last_message_at.desc()).all()

        return [
            {
                "id": session.id,
                "started_at": session.started_at.isoformat(),
                "last_message_at": session.last_message_at.isoformat(),
                "message_count": session.message_count,
                "status": session.status,
                "preview": self._get_session_preview(session.id)
            }
            for session in sessions
        ]

    def submit_feedback(self, message_id: UUID, rating: int, comment: Optional[str] = None) -> bool:
        """Submit feedback on a clone message"""
        message = self.db.query(Message).filter(
            Message.id == message_id,
            Message.clone_id == self.clone_id,
            Message.role == 'clone'
        ).first()

        if not message:
            return False

        message.feedback_rating = rating
        message.feedback_comment = comment
        self.db.commit()

        logger.info("Feedback submitted", message_id=str(message_id), rating=rating)
        return True

    def _load_personality_profile(self) -> Optional[PersonalityProfile]:
        """Load personality profile from S3"""
        try:
            s3_client = S3Client()
            profile_key = f"profiles/{self.tenant_id}/{self.clone_id}/personality_profile.json"
            profile_data = s3_client.get_object(profile_key)

            if profile_data:
                return PersonalityProfile.from_dict(profile_data)
        except Exception as e:
            logger.warning("Could not load personality profile", error=str(e))

        return None

    def _get_session_preview(self, session_id: int) -> str:
        """Get first user message as session preview"""
        first_message = self.db.query(Message).filter(
            Message.session_id == session_id,
            Message.role == 'external_user'
        ).order_by(Message.created_at).first()

        if first_message:
            preview = first_message.content[:100]
            return preview + "..." if len(first_message.content) > 100 else preview

        return "New conversation"
```

### Phase 2: API Routers

#### 2.1 Chat Router

**File:** `src/api/routers/chat.py`

```python
"""Chat API router for clone conversations"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from uuid import UUID
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import Clone, GuestUser
from src.services.chat_service import ChatService
from src.services.guest_auth_service import GuestAuthService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request to create or resume session"""
    external_user_name: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str
    external_user_name: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request to submit feedback"""
    message_id: str
    rating: int  # -1 or 1
    comment: Optional[str] = None


class MessageResponse(BaseModel):
    """Message response model"""
    id: str
    role: str
    content: str
    created_at: str
    external_user_name: Optional[str] = None
    rag_context: Optional[dict] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    feedback_rating: Optional[int] = None


class SessionResponse(BaseModel):
    """Session response model"""
    id: int
    started_at: str
    last_message_at: str
    message_count: int
    status: str
    preview: str


# Helper function to get guest user from JWT
def get_guest_user(request: Request, db: Session = Depends(get_db)) -> Optional[GuestUser]:
    """Extract guest user from JWT token in Authorization header"""
    from jose import jwt, JWTError
    from src.config.settings import settings

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != "guest":
            return None

        guest_user_id = payload.get("sub")
        guest_user = db.query(GuestUser).filter(GuestUser.id == guest_user_id).first()
        return guest_user
    except JWTError:
        return None


# Endpoints
@router.post("/chat/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_or_resume_session(
    request_data: CreateSessionRequest,
    request: Request,
    clone_ctx: Optional[CloneContext] = Depends(get_clone_context),  # Owner
    db: Session = Depends(get_db)
):
    """
    Create new session or resume most recent active session.
    Works for both clone owners and guest users.
    """
    # Check if owner or guest
    guest_user = get_guest_user(request, db)
    is_owner = clone_ctx is not None

    if not is_owner and not guest_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Determine clone_id
    clone_id = clone_ctx.clone_id if is_owner else guest_user.sessions[0].clone_id if guest_user.sessions else None

    if not clone_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clone ID required"
        )

    # Get tenant_id
    clone = db.query(Clone).filter(Clone.id == clone_id).first()
    if not clone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clone not found")

    # Create chat service
    chat_service = ChatService(clone_id, clone.tenant_id, db)

    # Get or create session
    session = chat_service.get_or_create_session(
        guest_user_id=guest_user.id if guest_user else None,
        is_owner=is_owner,
        external_user_name=request_data.external_user_name
    )

    return SessionResponse(
        id=session.id,
        started_at=session.started_at.isoformat(),
        last_message_at=session.last_message_at.isoformat(),
        message_count=session.message_count,
        status=session.status,
        preview=chat_service._get_session_preview(session.id)
    )


@router.post("/chat/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    request_data: SendMessageRequest,
    request: Request,
    clone_ctx: Optional[CloneContext] = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Send message and get clone response"""
    # Verify session exists and user has access
    from src.database.models import Session as SessionModel
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Check authorization
    guest_user = get_guest_user(request, db)
    is_owner = clone_ctx is not None and clone_ctx.clone_id == session.clone_id
    is_session_owner = guest_user and session.guest_user_id == guest_user.id

    if not (is_owner or is_session_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )

    # Get clone
    clone = db.query(Clone).filter(Clone.id == session.clone_id).first()

    # Send message
    chat_service = ChatService(session.clone_id, clone.tenant_id, db)
    result = chat_service.send_message(
        session_id=session_id,
        user_message=request_data.content,
        external_user_name=request_data.external_user_name
    )

    return result


@router.get("/chat/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_session_messages(
    session_id: int,
    request: Request,
    clone_ctx: Optional[CloneContext] = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Get all messages in a session"""
    from src.database.models import Session as SessionModel, Message

    # Verify session exists and user has access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Check authorization (same as send_message)
    guest_user = get_guest_user(request, db)
    is_owner = clone_ctx is not None and clone_ctx.clone_id == session.clone_id
    is_session_owner = guest_user and session.guest_user_id == guest_user.id

    if not (is_owner or is_session_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get messages
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()

    return [
        MessageResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
            external_user_name=msg.external_user_name,
            rag_context=msg.rag_context_json,
            tokens_used=msg.tokens_used,
            response_time_ms=msg.response_time_ms,
            feedback_rating=msg.feedback_rating
        )
        for msg in messages
    ]


@router.get("/chat/sessions", response_model=List[SessionResponse])
def list_sessions(
    request: Request,
    clone_ctx: Optional[CloneContext] = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all sessions for current user"""
    guest_user = get_guest_user(request, db)
    is_owner = clone_ctx is not None

    if not is_owner and not guest_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    clone_id = clone_ctx.clone_id if is_owner else None

    # For guests, get clone_id from their sessions
    if guest_user and not clone_id:
        # Guest users chat with specific clones, get from first session
        from src.database.models import Session as SessionModel
        first_session = db.query(SessionModel).filter(SessionModel.guest_user_id == guest_user.id).first()
        if first_session:
            clone_id = first_session.clone_id

    if not clone_id:
        return []

    clone = db.query(Clone).filter(Clone.id == clone_id).first()
    chat_service = ChatService(clone_id, clone.tenant_id, db)

    return chat_service.get_session_history(
        guest_user_id=guest_user.id if guest_user else None,
        is_owner=is_owner
    )


@router.post("/chat/feedback", status_code=status.HTTP_204_NO_CONTENT)
def submit_feedback(
    request_data: FeedbackRequest,
    request: Request,
    clone_ctx: Optional[CloneContext] = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Submit feedback on a clone message"""
    from src.database.models import Message

    message = db.query(Message).filter(Message.id == UUID(request_data.message_id)).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Verify user has access to this message's session
    guest_user = get_guest_user(request, db)
    is_owner = clone_ctx is not None and clone_ctx.clone_id == message.clone_id
    is_session_owner = guest_user and message.session.guest_user_id == guest_user.id

    if not (is_owner or is_session_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Submit feedback
    clone = db.query(Clone).filter(Clone.id == message.clone_id).first()
    chat_service = ChatService(message.clone_id, clone.tenant_id, db)

    success = chat_service.submit_feedback(
        message_id=UUID(request_data.message_id),
        rating=request_data.rating,
        comment=request_data.comment
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to submit feedback")
```

#### 2.2 Access Control Router

**File:** `src/api/routers/access_control.py`

```python
"""Access control API router"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.services.access_control_service import AccessControlService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class GrantAccessRequest(BaseModel):
    """Request to grant access to a customer"""
    email: EmailStr
    notes: Optional[str] = None


class AccessGrantResponse(BaseModel):
    """Access grant response model"""
    id: str
    email: str
    granted_at: str
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    notes: Optional[str] = None


# Endpoints
@router.post("/access/grants", response_model=AccessGrantResponse, status_code=status.HTTP_201_CREATED)
def grant_access(
    request_data: GrantAccessRequest,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Grant access to a customer (clone owner only)"""
    access_service = AccessControlService(db)

    grant = access_service.grant_access(
        clone_id=clone_ctx.clone_id,
        granted_to_email=request_data.email,
        granted_by_clerk_user_id=clone_ctx.clone.clerk_user_id,
        notes=request_data.notes
    )

    return AccessGrantResponse(
        id=str(grant.id),
        email=grant.granted_to_email,
        granted_at=grant.granted_at.isoformat(),
        expires_at=grant.expires_at.isoformat() if grant.expires_at else None,
        revoked_at=grant.revoked_at.isoformat() if grant.revoked_at else None,
        notes=grant.notes
    )


@router.get("/access/grants", response_model=List[AccessGrantResponse])
def list_grants(
    include_revoked: bool = False,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all access grants for clone (clone owner only)"""
    access_service = AccessControlService(db)
    grants = access_service.list_grants(clone_ctx.clone_id, include_revoked=include_revoked)

    return [
        AccessGrantResponse(
            id=str(grant.id),
            email=grant.granted_to_email,
            granted_at=grant.granted_at.isoformat(),
            expires_at=grant.expires_at.isoformat() if grant.expires_at else None,
            revoked_at=grant.revoked_at.isoformat() if grant.revoked_at else None,
            notes=grant.notes
        )
        for grant in grants
    ]


@router.delete("/access/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    grant_id: str,
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Revoke access grant (clone owner only)"""
    access_service = AccessControlService(db)

    # Verify grant belongs to this clone
    from src.database.models import CloneAccessGrant
    grant = db.query(CloneAccessGrant).filter(CloneAccessGrant.id == UUID(grant_id)).first()
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

    if grant.clone_id != clone_ctx.clone_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = access_service.revoke_access(UUID(grant_id))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
```

#### 2.3 Guest Auth Router

**File:** `src/api/routers/guest_auth.py`

```python
"""Guest authentication API router"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from uuid import UUID
from src.api.dependencies import get_db
from src.database.models import Clone
from src.services.guest_auth_service import GuestAuthService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class RequestMagicLinkRequest(BaseModel):
    """Request magic link for guest authentication"""
    email: EmailStr
    clone_slug: str  # e.g., "tiffany-ai"


class VerifyMagicLinkRequest(BaseModel):
    """Verify magic link token"""
    token: str
    clone_id: str


class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    token: Optional[str] = None
    guest_user: Optional[dict] = None


# Endpoints
@router.post("/auth/magic-link/request", response_model=AuthResponse)
def request_magic_link(
    request_data: RequestMagicLinkRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request magic link for guest authentication"""
    # Get clone by slug
    clone = db.query(Clone).filter(Clone.slug == request_data.clone_slug).first()
    if not clone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clone not found")

    # Get IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Request magic link
    auth_service = GuestAuthService(db)
    success, message = auth_service.request_magic_link(
        email=request_data.email,
        clone_id=clone.id,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    return AuthResponse(success=True, message=message)


@router.post("/auth/magic-link/verify", response_model=AuthResponse)
def verify_magic_link(
    request_data: VerifyMagicLinkRequest,
    db: Session = Depends(get_db)
):
    """Verify magic link token and return JWT"""
    auth_service = GuestAuthService(db)

    guest_user = auth_service.verify_magic_link(
        token=request_data.token,
        clone_id=UUID(request_data.clone_id)
    )

    if not guest_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link"
        )

    # Generate JWT for guest user
    jwt_token = auth_service.generate_jwt_for_guest(guest_user, UUID(request_data.clone_id))

    return AuthResponse(
        success=True,
        message="Authentication successful",
        token=jwt_token,
        guest_user={
            "id": str(guest_user.id),
            "email": guest_user.email,
            "first_name": guest_user.first_name,
            "last_name": guest_user.last_name
        }
    )
```

#### 2.4 Register Routers in Server

**File:** `src/api/server.py` (add to existing file)

```python
# Add imports
from src.api.routers import chat, access_control, guest_auth

# Register routers (add to existing router registrations)
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(access_control.router, prefix="/api", tags=["access_control"])
app.include_router(guest_auth.router, prefix="/api", tags=["guest_auth"])
```

### Phase 3: Email Service

**File:** `src/utils/email.py`

```python
"""Email service for sending magic links and notifications"""

import boto3
from botocore.exceptions import ClientError
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def send_magic_link_email(
    to_email: str,
    clone_name: str,
    magic_link_url: str,
    expiry_days: int = 30
):
    """Send magic link email via AWS SES"""

    # Email content
    subject = f"Your access link to chat with {clone_name}"

    html_body = f"""
    <html>
    <head></head>
    <body>
      <h2>Welcome to YouTopia!</h2>
      <p>You've been granted access to chat with <strong>{clone_name}</strong>.</p>
      <p>Click the link below to start your conversation:</p>
      <p>
        <a href="{magic_link_url}" style="background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">
          Start Chatting
        </a>
      </p>
      <p style="color: #666; font-size: 14px;">
        This link will expire in {expiry_days} days.<br/>
        If you didn't request this, please ignore this email.
      </p>
      <p style="color: #999; font-size: 12px; margin-top: 40px;">
        © 2025 YouTopia. All rights reserved.
      </p>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to YouTopia!

    You've been granted access to chat with {clone_name}.

    Click the link below to start your conversation:
    {magic_link_url}

    This link will expire in {expiry_days} days.
    If you didn't request this, please ignore this email.

    © 2025 YouTopia. All rights reserved.
    """

    # Send email via SES
    try:
        ses_client = boto3.client(
            'ses',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )

        response = ses_client.send_email(
            Source=settings.ses_from_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }
        )

        logger.info("Magic link email sent", to_email=to_email, message_id=response['MessageId'])
        return True

    except ClientError as e:
        logger.error("Failed to send magic link email", error=str(e), to_email=to_email)
        return False
```

**Update `src/config/settings.py` to add email settings:**

```python
# Add to Settings class
ses_from_email: str = "noreply@youtopia.com"  # Must be verified in SES
jwt_secret_key: str  # For guest user JWTs
frontend_url: str = "https://app.youtopia.com"
```

---

## Frontend Implementation

### Phase 1: Types and API Client

#### 1.1 Type Definitions

**File:** `frontend/src/types/index.ts` (add to existing file)

```typescript
// Chat types
export interface ChatSession {
  id: number;
  started_at: string;
  last_message_at: string;
  message_count: number;
  status: 'active' | 'closed';
  preview: string;
}

export interface ChatMessage {
  id: string;
  role: 'external_user' | 'clone';
  content: string;
  created_at: string;
  external_user_name?: string;
  rag_context?: {
    chunks: Array<{
      content: string;
      score: number;
      metadata?: any;
    }>;
  };
  tokens_used?: number;
  response_time_ms?: number;
  feedback_rating?: number; // -1, 1, or null
}

export interface SendMessageRequest {
  content: string;
  external_user_name?: string;
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  clone_message: ChatMessage;
}

export interface FeedbackRequest {
  message_id: string;
  rating: number; // -1 or 1
  comment?: string;
}

// Access control types
export interface AccessGrant {
  id: string;
  email: string;
  granted_at: string;
  expires_at?: string;
  revoked_at?: string;
  notes?: string;
}

export interface GrantAccessRequest {
  email: string;
  notes?: string;
}

// Guest auth types
export interface RequestMagicLinkRequest {
  email: string;
  clone_slug: string;
}

export interface VerifyMagicLinkRequest {
  token: string;
  clone_id: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  token?: string;
  guest_user?: {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
  };
}

// Clone with slug
export interface CloneWithSlug {
  id: string;
  slug: string;
  first_name?: string;
  last_name?: string;
  email?: string;
}
```

#### 1.2 Extend API Client

**File:** `frontend/src/api/client.ts` (add to existing client)

```typescript
// Add to apiClient object:
chat: {
  createSession: (data: { external_user_name?: string }) =>
    apiClient.post<ChatSession>("/api/chat/sessions", data),

  sendMessage: (sessionId: number, data: SendMessageRequest) =>
    apiClient.post<SendMessageResponse>(`/api/chat/sessions/${sessionId}/messages`, data),

  getMessages: (sessionId: number) =>
    apiClient.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),

  listSessions: () =>
    apiClient.get<ChatSession[]>("/api/chat/sessions"),

  submitFeedback: (data: FeedbackRequest) =>
    apiClient.post("/api/chat/feedback", data),
},

access: {
  grantAccess: (data: GrantAccessRequest) =>
    apiClient.post<AccessGrant>("/api/access/grants", data),

  listGrants: (includeRevoked?: boolean) =>
    apiClient.get<AccessGrant[]>(`/api/access/grants${includeRevoked ? '?include_revoked=true' : ''}`),

  revokeAccess: (grantId: string) =>
    apiClient.delete(`/api/access/grants/${grantId}`),
},

guestAuth: {
  requestMagicLink: (data: RequestMagicLinkRequest) =>
    apiClient.post<AuthResponse>("/api/auth/magic-link/request", data),

  verifyMagicLink: (data: VerifyMagicLinkRequest) =>
    apiClient.post<AuthResponse>("/api/auth/magic-link/verify", data),
},
```

### Phase 2: Chat UI Components

#### 2.1 ChatMessageBubble Component

**File:** `frontend/src/components/features/ChatMessageBubble.tsx`

```typescript
import { ChatMessage } from "@/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, User, Bot } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useState } from "react";

interface ChatMessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
  cloneName?: string;
  onFeedback?: (rating: number) => void;
}

export const ChatMessageBubble = ({
  message,
  isUser,
  cloneName = "AI",
  onFeedback,
}: ChatMessageBubbleProps) => {
  const [feedbackGiven, setFeedbackGiven] = useState(message.feedback_rating !== undefined && message.feedback_rating !== null);

  const handleFeedback = (rating: number) => {
    if (onFeedback) {
      onFeedback(rating);
      setFeedbackGiven(true);
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} mb-4`}>
      {/* Avatar */}
      <Avatar className="w-8 h-8">
        <AvatarFallback className={isUser ? "bg-primary/20" : "bg-secondary/20"}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={`flex flex-col max-w-[70%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Message Bubble */}
        <Card
          className={`p-4 ${
            isUser
              ? "bg-gradient-primary text-white"
              : "bg-card border-border/50"
          }`}
        >
          <p className={`text-sm ${isUser ? "text-white" : "text-foreground"}`}>
            {message.content}
          </p>
        </Card>

        {/* Metadata */}
        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          <span>
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>

          {/* Feedback buttons (clone messages only) */}
          {!isUser && onFeedback && !feedbackGiven && (
            <div className="flex gap-1 ml-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-primary/10"
                onClick={() => handleFeedback(1)}
              >
                <ThumbsUp className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-destructive/10"
                onClick={() => handleFeedback(-1)}
              >
                <ThumbsDown className="w-3 h-3" />
              </Button>
            </div>
          )}

          {feedbackGiven && message.feedback_rating !== null && (
            <span className="text-xs ml-2">
              {message.feedback_rating === 1 ? "👍" : "👎"}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
```

#### 2.2 ChatInput Component

**File:** `frontend/src/components/features/ChatInput.tsx`

```typescript
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput = ({
  onSend,
  disabled = false,
  placeholder = "Type your message...",
}: ChatInputProps) => {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [message]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-2 items-end p-4 border-t border-border/50 bg-background">
      <Textarea
        ref={textareaRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="min-h-[60px] max-h-[200px] resize-none"
        rows={1}
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !message.trim()}
        className="bg-gradient-primary hover:shadow-glow"
        size="icon"
      >
        <Send className="w-5 h-5" />
      </Button>
    </div>
  );
};
```

#### 2.3 TypingIndicator Component

**File:** `frontend/src/components/features/TypingIndicator.tsx`

```typescript
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bot } from "lucide-react";

export const TypingIndicator = () => {
  return (
    <div className="flex gap-3 mb-4">
      <Avatar className="w-8 h-8">
        <AvatarFallback className="bg-secondary/20">
          <Bot className="w-4 h-4" />
        </AvatarFallback>
      </Avatar>

      <Card className="p-4 bg-card border-border/50">
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
        </div>
      </Card>
    </div>
  );
};
```

#### 2.4 ChatInterface Component

**File:** `frontend/src/components/features/ChatInterface.tsx`

```typescript
import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChatMessage, ChatSession } from "@/types";
import { apiClient } from "@/api/client";
import { ChatMessageBubble } from "./ChatMessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ChatInterfaceProps {
  sessionId?: number;
  cloneName?: string;
  onNewConversation?: () => void;
}

export const ChatInterface = ({
  sessionId: initialSessionId,
  cloneName = "AI",
  onNewConversation,
}: ChatInterfaceProps) => {
  const [sessionId, setSessionId] = useState<number | undefined>(initialSessionId);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Create or resume session
  const { data: session, isLoading: sessionLoading } = useQuery<ChatSession>({
    queryKey: ["chatSession", sessionId],
    queryFn: async () => {
      if (sessionId) {
        // TODO: Get existing session
        return { id: sessionId } as ChatSession;
      } else {
        // Create new session
        const newSession = await apiClient.chat.createSession({});
        setSessionId(newSession.id);
        return newSession;
      }
    },
    enabled: !sessionId || sessionId > 0,
  });

  // Get messages
  const { data: messages = [], isLoading: messagesLoading } = useQuery<ChatMessage[]>({
    queryKey: ["chatMessages", sessionId],
    queryFn: () => apiClient.chat.getMessages(sessionId!),
    enabled: !!sessionId,
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (content: string) =>
      apiClient.chat.sendMessage(sessionId!, { content }),
    onMutate: () => {
      setIsTyping(true);
    },
    onSuccess: (data) => {
      // Update messages cache
      queryClient.setQueryData<ChatMessage[]>(
        ["chatMessages", sessionId],
        (old = []) => [...old, data.user_message, data.clone_message]
      );
      setIsTyping(false);
    },
    onError: (error) => {
      setIsTyping(false);
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Submit feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: string; rating: number }) =>
      apiClient.chat.submitFeedback({ message_id: messageId, rating }),
    onSuccess: (_, variables) => {
      // Update message in cache
      queryClient.setQueryData<ChatMessage[]>(
        ["chatMessages", sessionId],
        (old = []) =>
          old.map((msg) =>
            msg.id === variables.messageId
              ? { ...msg, feedback_rating: variables.rating }
              : msg
          )
      );
      toast({
        title: "Feedback submitted",
        description: "Thank you for your feedback!",
      });
    },
  });

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleSend = (content: string) => {
    sendMessageMutation.mutate(content);
  };

  const handleFeedback = (messageId: string, rating: number) => {
    feedbackMutation.mutate({ messageId, rating });
  };

  if (sessionLoading || messagesLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div>
          <h2 className="text-xl font-semibold">{cloneName}</h2>
          <p className="text-sm text-muted-foreground">AI Assistant</p>
        </div>
        {onNewConversation && (
          <Button
            variant="outline"
            size="sm"
            onClick={onNewConversation}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </Button>
        )}
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        {messages.length === 0 ? (
          <Card className="p-8 text-center border-border/50 bg-gradient-secondary">
            <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
            <p className="text-sm text-muted-foreground">
              Ask me anything! I'm here to help.
            </p>
          </Card>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessageBubble
                key={message.id}
                message={message}
                isUser={message.role === "external_user"}
                cloneName={cloneName}
                onFeedback={
                  message.role === "clone"
                    ? (rating) => handleFeedback(message.id, rating)
                    : undefined
                }
              />
            ))}
            {isTyping && <TypingIndicator />}
            <div ref={scrollRef} />
          </>
        )}
      </ScrollArea>

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={sendMessageMutation.isPending || isTyping}
        placeholder="Type your message..."
      />
    </div>
  );
};
```

### Phase 3: Pages

#### 3.1 Chat Page

**File:** `frontend/src/pages/Chat.tsx`

```typescript
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChatInterface } from "@/components/features/ChatInterface";
import { Card } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import Header from "@/components/layout/Header";

const Chat = () => {
  const { slug } = useParams<{ slug: string }>();

  // TODO: Get clone by slug
  const { data: clone, isLoading } = useQuery({
    queryKey: ["clone", slug],
    queryFn: async () => {
      // This endpoint doesn't exist yet - needs to be added
      // For now, mock data
      return {
        id: "mock-id",
        slug: slug,
        first_name: "Tiffany",
        last_name: "AI",
      };
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </div>
    );
  }

  if (!clone) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <Card className="p-8 text-center">
            <h2 className="text-2xl font-semibold mb-2">Clone not found</h2>
            <p className="text-muted-foreground">
              The clone you're looking for doesn't exist.
            </p>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <div className="flex-1 container mx-auto px-6 py-8">
        <Card className="h-[calc(100vh-200px)]">
          <ChatInterface
            cloneName={`${clone.first_name} ${clone.last_name}`}
          />
        </Card>
      </div>
    </div>
  );
};

export default Chat;
```

#### 3.2 Magic Link Verification Page

**File:** `frontend/src/pages/MagicLinkVerify.tsx`

```typescript
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { Card } from "@/components/ui/card";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const MagicLinkVerify = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");

  const token = searchParams.get("token");
  const cloneId = searchParams.get("clone_id");

  const verifyMutation = useMutation({
    mutationFn: () =>
      apiClient.guestAuth.verifyMagicLink({
        token: token!,
        clone_id: cloneId!,
      }),
    onSuccess: (data) => {
      // Store JWT token
      if (data.token) {
        localStorage.setItem("guest_auth_token", data.token);
      }
      setStatus("success");

      // Redirect to chat after 2 seconds
      setTimeout(() => {
        // Get clone slug from clone_id (TODO: add endpoint)
        navigate(`/chat/tiffany-ai`);  // Hardcoded for now
      }, 2000);
    },
    onError: () => {
      setStatus("error");
    },
  });

  useEffect(() => {
    if (token && cloneId) {
      verifyMutation.mutate();
    } else {
      setStatus("error");
    }
  }, [token, cloneId]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Card className="p-8 max-w-md text-center">
        {status === "verifying" && (
          <>
            <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Verifying...</h2>
            <p className="text-muted-foreground">
              Please wait while we verify your magic link.
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Success!</h2>
            <p className="text-muted-foreground">
              Redirecting you to chat...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Invalid Link</h2>
            <p className="text-muted-foreground mb-4">
              This magic link is invalid or has expired.
            </p>
            <Button onClick={() => navigate("/")}>
              Go to Homepage
            </Button>
          </>
        )}
      </Card>
    </div>
  );
};

export default MagicLinkVerify;
```

#### 3.3 Access Control Settings Page

**File:** `frontend/src/pages/AccessControlSettings.tsx`

```typescript
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { AccessGrant } from "@/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import Header from "@/components/layout/Header";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const AccessControlSettings = () => {
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Get grants
  const { data: grants = [], isLoading } = useQuery<AccessGrant[]>({
    queryKey: ["accessGrants"],
    queryFn: () => apiClient.access.listGrants(),
  });

  // Grant access mutation
  const grantMutation = useMutation({
    mutationFn: () => apiClient.access.grantAccess({ email, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accessGrants"] });
      setEmail("");
      setNotes("");
      toast({
        title: "Access granted",
        description: `${email} can now chat with your clone.`,
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to grant access. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Revoke access mutation
  const revokeMutation = useMutation({
    mutationFn: (grantId: string) => apiClient.access.revokeAccess(grantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accessGrants"] });
      toast({
        title: "Access revoked",
        description: "User can no longer chat with your clone.",
      });
    },
  });

  const handleGrant = () => {
    if (email) {
      grantMutation.mutate();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-8">Access Control</h1>

          {/* Grant Access Form */}
          <Card className="p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Grant Access to Customer</h2>
            <div className="space-y-4">
              <div>
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="customer@example.com"
                />
              </div>
              <div>
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g., VIP customer, trial user, etc."
                  rows={2}
                />
              </div>
              <Button
                onClick={handleGrant}
                disabled={!email || grantMutation.isPending}
                className="bg-gradient-primary hover:shadow-glow"
              >
                {grantMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Plus className="w-4 h-4 mr-2" />
                )}
                Grant Access
              </Button>
            </div>
          </Card>

          {/* Granted Users List */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Granted Users</h2>
            {isLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            ) : grants.length === 0 ? (
              <p className="text-muted-foreground text-center p-8">
                No users have been granted access yet.
              </p>
            ) : (
              <div className="space-y-2">
                {grants.map((grant) => (
                  <div
                    key={grant.id}
                    className="flex items-center justify-between p-4 border border-border/50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{grant.email}</p>
                      {grant.notes && (
                        <p className="text-sm text-muted-foreground">{grant.notes}</p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Granted {new Date(grant.granted_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => revokeMutation.mutate(grant.id)}
                      disabled={revokeMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AccessControlSettings;
```

### Phase 4: Routing

**File:** `frontend/src/App.tsx` (add routes)

```typescript
import { Route } from "react-router-dom";
import Chat from "@/pages/Chat";
import MagicLinkVerify from "@/pages/MagicLinkVerify";
import AccessControlSettings from "@/pages/AccessControlSettings";
import ProtectedRoute from "@/components/layout/ProtectedRoute";

// Add to existing routes:
<Route path="/chat/:slug" element={<Chat />} />
<Route path="/auth/magic-link" element={<MagicLinkVerify />} />
<Route
  path="/settings/access"
  element={
    <ProtectedRoute>
      <AccessControlSettings />
    </ProtectedRoute>
  }
/>
```

**File:** `frontend/src/constants/routes.ts` (add constants)

```typescript
export const ROUTES = {
  // ... existing routes
  CHAT: (slug: string) => `/chat/${slug}`,
  MAGIC_LINK_VERIFY: "/auth/magic-link",
  ACCESS_SETTINGS: "/settings/access",
} as const;
```

---

## Implementation Phases

### Week 1: Database & Backend Foundation

**Tasks:**
1. ✅ Create Alembic migration for new tables/columns
2. ✅ Add database models (GuestUser, MagicLink, CloneAccessGrant)
3. ✅ Implement AccessControlService
4. ✅ Implement GuestAuthService
5. ✅ Implement ChatService
6. ✅ Set up AWS SES for email sending
7. ✅ Test services with unit tests

**Deliverable:** Backend services ready, migrations applied

---

### Week 2: API & Email

**Tasks:**
1. ✅ Implement Chat Router
2. ✅ Implement Access Control Router
3. ✅ Implement Guest Auth Router
4. ✅ Register routers in server.py
5. ✅ Test API endpoints (Postman/curl)
6. ✅ Set up email templates
7. ✅ Test magic link flow end-to-end

**Deliverable:** Full backend API functional

---

### Week 3: Frontend Core UI

**Tasks:**
1. ✅ Add TypeScript types
2. ✅ Extend API client
3. ✅ Create ChatMessageBubble component
4. ✅ Create ChatInput component
5. ✅ Create TypingIndicator component
6. ✅ Create ChatInterface component
7. ✅ Test components in isolation

**Deliverable:** Core chat UI components ready

---

### Week 4: Frontend Pages & Integration

**Tasks:**
1. ✅ Create Chat page
2. ✅ Create MagicLinkVerify page
3. ✅ Create AccessControlSettings page
4. ✅ Add routes to App.tsx
5. ✅ Test full user flows (owner + guest)
6. ✅ UI polish (animations, loading states, error handling)
7. ✅ Integration testing

**Deliverable:** MVP fully functional

---

## Testing Strategy

### Backend Tests

**Unit Tests** (`tests/test_chat_service.py`):
- Session creation/resumption
- Message sending and response generation
- RAG context retrieval
- Feedback submission

**Unit Tests** (`tests/test_access_control_service.py`):
- Grant access
- Check access (allowlist validation)
- Revoke access
- List grants

**Unit Tests** (`tests/test_guest_auth_service.py`):
- Request magic link
- Verify magic link
- Token expiry
- JWT generation

**Integration Tests** (`tests/test_chat_api.py`):
- End-to-end chat flow
- Access control validation
- Magic link authentication
- Feedback submission

### Frontend Tests

**Manual Testing Checklist:**
- [ ] Clone owner can grant access to customer
- [ ] Customer receives magic link email
- [ ] Customer can authenticate via magic link
- [ ] Customer can send message and receive response
- [ ] Messages display correctly (user right, clone left)
- [ ] Typing indicator shows while generating response
- [ ] Auto-scroll to bottom on new message
- [ ] Feedback buttons work (thumbs up/down)
- [ ] Session history shows past conversations
- [ ] New conversation button creates new session
- [ ] Error messages display for network failures
- [ ] Loading states show during API calls

---

## Security & Privacy

### Authentication Security

1. **Magic Link Tokens:**
   - Generate with `secrets.token_urlsafe(32)` (cryptographically secure)
   - Store hashed (SHA-256) in database
   - 30-day expiry (configurable)
   - One-time use (marked as used_at)

2. **JWT Tokens:**
   - Sign with HS256 algorithm
   - Include guest_user_id, email, clone_id
   - 30-day expiry (matches magic link)
   - Stored in localStorage (HTTPS only)

3. **Access Control:**
   - Verify grant before sending magic link
   - Check clone ownership before granting access
   - Validate session ownership before allowing messages

### Data Privacy

1. **Clone Isolation:**
   - RAG retrieval automatically filtered by clone_id
   - Sessions scoped to clone_id
   - Messages scoped to clone_id

2. **Tenant Isolation:**
   - All queries filtered by tenant_id
   - CloneVectorStore uses namespace isolation

3. **Guest User Privacy:**
   - Email addresses stored hashed (TODO: implement if needed)
   - No PII collected beyond email
   - Session data accessible only to guest user and clone owner

### Rate Limiting

**TODO:** Add rate limiting to prevent abuse
- Magic link requests: 3 per email per hour
- Message sending: 20 messages per session per minute
- Access grants: 10 grants per clone per day

---

## Future Enhancements

### Phase 5: Streaming Responses (SSE)

**Backend:**
- Add `/api/chat/stream` endpoint (Server-Sent Events)
- Use `LLMClient.generate_stream()` for token streaming
- Stream tokens as they arrive from OpenAI

**Frontend:**
- Use EventSource API to consume SSE
- Update message content incrementally
- Show partial response in real-time

**Complexity:** +200 lines backend, +150 lines frontend

---

### Phase 6: Manage Clone Page

**Features:**
- View all customer sessions (read-only)
- Filter by customer email
- Search message history
- View feedback statistics
- Popular questions analysis

**Complexity:** +300 lines backend, +500 lines frontend

---

### Phase 7: Analytics Dashboard

**Features:**
- Message volume over time
- Customer satisfaction (feedback ratings)
- Average response time
- Top questions/topics
- RAG quality metrics

**Complexity:** +400 lines backend, +600 lines frontend

---

### Phase 8: Shareable Links

**Features:**
- Generate shareable link (e.g., `youtopia.com/chat/tiffany-ai?key=abc123`)
- Auto-allowlist email on entry
- Optional link expiry
- Track link usage

**Complexity:** +150 lines backend, +200 lines frontend

---

### Phase 9: Voice Input/Output

**Features:**
- Voice input (Whisper API for transcription)
- Voice output (OpenAI TTS)
- Audio message history

**Complexity:** +500 lines backend, +800 lines frontend

---

## Success Metrics

### MVP (Week 4)

**Functional:**
- [ ] Clone owner can grant access in <30 seconds
- [ ] Customer can authenticate in <60 seconds
- [ ] Customer can send message and get response
- [ ] Response includes relevant RAG context
- [ ] Feedback system works (thumbs up/down)

**Performance:**
- [ ] 90% of responses <5 seconds
- [ ] 80% of responses include relevant context
- [ ] <2% error rate
- [ ] 99.5% API uptime

**UX:**
- [ ] Customer satisfaction >80% (via feedback)
- [ ] <5% bounce rate on chat page
- [ ] >70% message send success rate

---

## Conclusion

This implementation plan provides a complete roadmap for building the YouTopia chat interface. The phased approach enables rapid MVP delivery (4 weeks) while maintaining a clear path to advanced features (streaming, analytics, voice).

**Key Advantages:**
1. ✅ Leverages existing infrastructure (Session/Message models, RAG, auth)
2. ✅ Minimal friction for customers (magic link, no password)
3. ✅ Granular access control (email allowlist)
4. ✅ Familiar UX (ChatGPT-style interface)
5. ✅ Built for scale (clone isolation, tenant isolation)
6. ✅ Clear security model (JWT, access grants, rate limiting)

**Next Steps:**
1. Review plan with stakeholders
2. Create feature branch: `feature/chat-interface`
3. Apply database migrations
4. Start Week 1: Backend Foundation
5. Iterate with regular demos and user testing

---

**Document Version:** 1.0
**Last Updated:** 2025-12-31
**Status:** Ready for Implementation
