# Agent Architecture Design

This document outlines the architecture for adding agentic capabilities to YouTopia Mind clones, starting with Slack observation.

## Overview

The agent layer enables clones to autonomously observe external systems, classify information by relevance, and surface interesting items to professionals. Users provide feedback to improve classification over time.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLONE                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     AGENT LAYER (NEW)                                │   │
│  │                                                                      │   │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐ │   │
│  │   │   OBSERVE    │───▶│   CLASSIFY   │───▶│      SURFACE         │ │   │
│  │   │              │    │              │    │                      │ │   │
│  │   │ Slack fetch  │    │ LLM + examples│   │ On-demand digest     │ │   │
│  │   │ (4-hourly)   │    │ 3 categories │    │ Feedback buttons     │ │   │
│  │   └──────────────┘    └──────────────┘    └──────────────────────┘ │   │
│  │           │                                         │               │   │
│  │           └─────────────────────────────────────────┘               │   │
│  │                              │                                      │   │
│  │                    ┌─────────▼─────────┐                           │   │
│  │                    │      LEARN        │                           │   │
│  │                    │                   │                           │   │
│  │                    │ Feedback → Examples│                          │   │
│  │                    │ Examples → Better  │                          │   │
│  │                    │ classification     │                          │   │
│  │                    └───────────────────┘                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐   │
│  │ KNOWLEDGE (RAG)  │  │ SESSIONS (Chat)  │  │ INTEGRATIONS           │   │
│  │ (existing)       │  │ (existing)       │  │ (existing)             │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MVP Scope (Phase 1)

### What We Build

1. **Slack Observer** - Fetch messages from selected channels every 4 hours
2. **LLM Classifier** - Classify messages into 3 categories using few-shot examples
3. **On-Demand Digest** - Display categorized observations with feedback buttons
4. **Feedback Loop** - User corrections become training examples

### What's NOT in MVP

- Draft/send message capabilities
- Scheduled email digests
- Embeddings/similarity search
- Pattern extraction from examples
- Thread expansion UI
- Multi-platform support (email, calendar)
- Progressive autonomy

---

## Data Model

### New Tables

#### 1. AgentCapability

Tracks which capabilities are enabled for a clone.

```sql
CREATE TABLE agent_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clone_id UUID NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES integrations(id),

    platform VARCHAR(50) NOT NULL,           -- "slack"
    capability_type VARCHAR(50) NOT NULL,    -- "observer"
    config JSONB DEFAULT '{}',               -- {channels: [...], frequency_minutes: 240}
    status VARCHAR(20) DEFAULT 'active',     -- "active", "paused", "setup_required", "error"
    last_run_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(clone_id, platform, capability_type)
);
```

**Config schema for Slack observer:**
```json
{
    "channels": [
        {"id": "C123", "name": "general"},
        {"id": "C456", "name": "deals"}
    ],
    "frequency_minutes": 240
}
```

#### 2. AgentPreference

Stores learned preferences per capability type.

```sql
CREATE TABLE agent_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clone_id UUID NOT NULL REFERENCES clones(id) ON DELETE CASCADE,

    capability_type VARCHAR(50) NOT NULL,    -- "observer"
    platform VARCHAR(50),                     -- "slack", NULL = universal
    preference_type VARCHAR(50) NOT NULL,    -- "very_interesting", "interesting", "not_interesting"

    description TEXT,                         -- User's description of this category
    keywords JSONB DEFAULT '[]',              -- ["partnership", "funding"]
    examples JSONB DEFAULT '[]',              -- [{text, explanation, source}]

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(clone_id, capability_type, platform, preference_type)
);
```

**Examples schema:**
```json
[
    {
        "id": "uuid",
        "text": "Looking for technical partners for our Series A startup...",
        "explanation": "Direct partnership opportunity with funded company",
        "source": "user_provided|user_feedback",
        "added_at": "2024-01-15T10:00:00Z",
        "metadata": {
            "channel": "#deals",
            "author": "founder"
        }
    }
]
```

#### 3. AgentObservation

Stores classified messages (only interesting + 10% sample of not_interesting).

```sql
CREATE TABLE agent_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clone_id UUID NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
    capability_id UUID NOT NULL REFERENCES agent_capabilities(id) ON DELETE CASCADE,

    -- Source identification
    source_type VARCHAR(50) NOT NULL,        -- "slack_message"
    source_id VARCHAR(255) NOT NULL,         -- Slack message ts
    source_metadata JSONB DEFAULT '{}',      -- {channel_id, channel_name, author_id, author_name, thread_ts}

    -- Content
    content TEXT NOT NULL,                   -- Plain text extracted from message

    -- Classification
    classification VARCHAR(50),              -- "very_interesting", "interesting", "not_interesting"
    classification_confidence FLOAT,         -- 0.0-1.0
    classification_reasoning TEXT,           -- "Matches partnership pattern"
    needs_review BOOLEAN DEFAULT FALSE,      -- True if confidence < 0.7

    -- User feedback
    user_feedback VARCHAR(50),               -- "confirmed", "corrected_to_interesting", etc.
    status VARCHAR(20) DEFAULT 'classified', -- "classified", "reviewed"

    observed_at TIMESTAMP NOT NULL,          -- When message was posted in Slack
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(clone_id, source_type, source_id)
);

CREATE INDEX ix_observations_clone_status ON agent_observations(clone_id, status);
CREATE INDEX ix_observations_classification ON agent_observations(clone_id, classification);
```

#### 4. ObservationCheckpoint

Lightweight tracking of observation progress per channel.

```sql
CREATE TABLE observation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability_id UUID NOT NULL REFERENCES agent_capabilities(id) ON DELETE CASCADE,

    channel_id VARCHAR(100) NOT NULL,        -- Slack channel ID
    last_message_ts VARCHAR(50),             -- Last seen message timestamp
    last_observed_at TIMESTAMP,

    messages_seen INTEGER DEFAULT 0,         -- Running count for stats
    messages_stored INTEGER DEFAULT 0,       -- How many we actually kept

    UNIQUE(capability_id, channel_id)
);
```

---

## Core Flows

### Flow 1: Setup

```
User enables Slack agent capability
    │
    ▼
Step 1: Select channels to monitor (opt-in)
    │
    ▼
Step 2: For each preference type, ask:
        "What would you define as [very interesting/interesting]?"
        (1-2 sentences)
    │
    ▼
Step 3 (optional): "Can you provide an example message?"
    │
    ▼
Create AgentCapability record
Create 3 AgentPreference records (one per category)
    │
    ▼
First observation runs within 4 hours (or trigger immediately)
```

### Flow 2: Observation (Celery Task - Every 4 Hours)

```
For each active slack_observer capability:
    │
    ▼
For each monitored channel:
    │
    ├── Get checkpoint (last_message_ts)
    ├── Fetch new messages from Slack API since checkpoint
    │
    ▼
Classify ALL messages in memory (batch LLM calls, max 15 per call)
    │
    ▼
Selective storage:
    ├── very_interesting  → STORE
    ├── interesting       → STORE
    ├── needs_review      → STORE
    └── not_interesting   → STORE 10% random sample, DISCARD rest
    │
    ▼
Update checkpoint per channel (last_message_ts, counts)
```

### Flow 3: Classification

```
Input: List of messages + Clone's preferences

Build prompt with:
    ├── Preference descriptions (from setup)
    ├── Keywords (if provided)
    └── Up to 5 examples per category (most recent)

LLM classifies each message:
    ├── category: very_interesting | interesting | not_interesting
    ├── confidence: 0.0-1.0
    └── reasoning: brief explanation

If confidence < 0.7 → needs_review = true
```

**Classification prompt structure:**
```
You are classifying Slack messages for a professional.

CATEGORIES:

1. VERY INTERESTING: {description}
   Keywords: {keywords}
   Examples:
   - "{example_1}" - {explanation_1}
   - "{example_2}" - {explanation_2}

2. INTERESTING: {description}
   ...

3. NOT INTERESTING: {description}
   ...

MESSAGES TO CLASSIFY:
[
  {"id": 1, "channel": "#deals", "author": "Sarah", "content": "..."},
  {"id": 2, "channel": "#general", "author": "Bot", "content": "..."},
  ...
]

Respond with JSON array:
[
  {"id": 1, "category": "very_interesting", "confidence": 0.9, "reasoning": "..."},
  {"id": 2, "category": "not_interesting", "confidence": 0.95, "reasoning": "..."},
  ...
]
```

### Flow 4: Digest (On-Demand)

```
User opens /agent/digest page
    │
    ▼
Fetch observations for clone:
    ├── Filter: last 7 days OR status != 'reviewed'
    ├── Order: observed_at DESC
    │
    ▼
Group by classification:
    ├── very_interesting: ALL items
    ├── interesting: Up to 10 (with "show more")
    ├── review_needed: Up to 10 (needs_review = true)
    └── not_interesting_sample: Up to 5 (for calibration feedback)
    │
    ▼
Return digest with metadata:
    ├── Items per section
    ├── Total counts
    └── Last observation timestamp
```

### Flow 5: Feedback & Learning

```
User clicks feedback button on observation
    │
    ├── "Good catch" (👍)
    │       └── user_feedback = "confirmed"
    │           status = "reviewed"
    │
    └── "Wrong category" (👎) → Select correct category
            │
            ▼
        user_feedback = "corrected_to_{category}"
        status = "reviewed"
            │
            ▼
        Add observation as example to CORRECT preference:
        {
            text: observation.content,
            explanation: "User correction from {original} to {correct}",
            source: "user_feedback",
            metadata: observation.source_metadata
        }
            │
            ▼
        Future classifications see this example (max 5 per category in prompt)
```

---

## API Endpoints

### Capabilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agent/capabilities` | List all capabilities for clone |
| POST | `/agent/capabilities/slack/setup` | Enable Slack observer |
| PATCH | `/agent/capabilities/{id}` | Update config (channels, pause/resume) |
| DELETE | `/agent/capabilities/{id}` | Disable capability |

**POST /agent/capabilities/slack/setup**
```json
// Request
{
    "channels": [
        {"id": "C123", "name": "general"},
        {"id": "C456", "name": "deals"}
    ],
    "preferences": {
        "very_interesting": {
            "description": "Partnership opportunities and investor outreach",
            "keywords": ["partnership", "invest", "funding"],
            "example": {  // optional
                "text": "Looking for technical partners...",
                "explanation": "Direct partnership request"
            }
        },
        "interesting": {
            "description": "Industry news and potential leads",
            "keywords": ["announcement", "launch"]
        },
        "not_interesting": {
            "description": "Routine updates, bot messages, casual chat"
        }
    }
}

// Response
{
    "capability_id": "uuid",
    "status": "active",
    "next_run_at": "2024-01-15T12:00:00Z"
}
```

### Digest

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agent/digest` | Get current digest |

**GET /agent/digest**
```json
// Response
{
    "very_interesting": [
        {
            "id": "uuid",
            "content": "Looking for technical partners...",
            "source_metadata": {
                "channel_name": "#deals",
                "author_name": "Sarah Chen",
                "observed_at": "2024-01-15T10:30:00Z"
            },
            "classification_reasoning": "Matches partnership pattern",
            "classification_confidence": 0.92
        }
    ],
    "interesting": [...],
    "review_needed": [...],
    "not_interesting_sample": [...],
    "stats": {
        "total_observations": 47,
        "pending_review": 12,
        "last_observation_at": "2024-01-15T12:00:00Z"
    }
}
```

### Feedback

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/observations/{id}/feedback` | Submit feedback |

**POST /agent/observations/{id}/feedback**
```json
// Request - confirmation
{
    "feedback": "confirmed"
}

// Request - correction
{
    "feedback": "corrected_to_interesting",
    "comment": "This is relevant for our sales pipeline"  // optional
}

// Response
{
    "success": true,
    "preference_updated": true  // if correction, example was added
}
```

### Preferences (for transparency/debugging)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agent/preferences` | List all preferences |
| POST | `/agent/preferences/{type}/examples` | Manually add example |

---

## Backend Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py                 # Coordinates observe → classify flow
│   │
│   ├── capabilities/
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseObserver abstract class
│   │   └── slack/
│   │       ├── __init__.py
│   │       ├── observer.py             # SlackObserver - fetches messages
│   │       ├── message_extractor.py    # Extract plain text from Slack messages
│   │       └── setup.py                # Setup/config validation
│   │
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── classifier.py               # LLM-based classifier
│   │   └── prompts.py                  # Prompt templates
│   │
│   ├── digest/
│   │   ├── __init__.py
│   │   └── service.py                  # DigestService - generates digest
│   │
│   └── feedback/
│       ├── __init__.py
│       └── service.py                  # FeedbackService - processes feedback
│
├── workers/
│   ├── __init__.py
│   ├── celery_app.py                   # Celery configuration
│   └── tasks.py                        # observe_and_classify tasks
│
├── api/routers/
│   └── agent.py                        # Agent API endpoints
│
└── database/
    └── models.py                       # Add new models (existing file)
```

---

## Infrastructure

### Celery + Redis

| Component | Purpose | Deployment |
|-----------|---------|------------|
| Redis | Message broker + result backend | Render Redis or Upstash |
| Celery Worker | Executes observation/classification tasks | Render worker process |
| Celery Beat | Schedules 4-hourly observation | Render worker process |

### Celery Configuration

```python
# src/workers/celery_app.py

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "youtopia_agents",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_time_limit=600,  # 10 min max per task
    task_acks_late=True,
)

# Beat schedule - every 4 hours
celery_app.conf.beat_schedule = {
    "observe-and-classify-all": {
        "task": "src.workers.tasks.observe_all_clones",
        "schedule": crontab(minute=0, hour="*/4"),  # 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    }
}
```

### Environment Variables (New)

```bash
# Redis
REDIS_URL=redis://...

# Celery (uses Redis)
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
```

### Render Deployment

```yaml
# render.yaml additions

services:
  # Existing web service...

  - type: worker
    name: celery-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A src.workers.celery_app worker --loglevel=info
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: youtopia-redis
          property: connectionString

  - type: worker
    name: celery-beat
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A src.workers.celery_app beat --loglevel=info
    envVars:
      - key: REDIS_URL
        fromService:
          type: redis
          name: youtopia-redis
          property: connectionString

databases:
  - name: youtopia-redis
    type: redis
    plan: starter  # $7/mo
```

---

## Frontend Components

### New Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/agent` | AgentDashboard | Overview of enabled capabilities |
| `/agent/slack/setup` | SlackSetupWizard | Channel selection + preference setup |
| `/agent/digest` | DigestPage | View observations + feedback |

### Component Structure

```
frontend/src/
├── pages/
│   └── Agent/
│       ├── index.tsx                 # AgentDashboard
│       ├── Digest.tsx                # DigestPage
│       └── Setup/
│           └── SlackSetup.tsx        # SlackSetupWizard
│
├── components/
│   └── agent/
│       ├── CapabilityCard.tsx        # Shows capability status
│       ├── ObservationCard.tsx       # Single observation with metadata
│       ├── DigestSection.tsx         # Section (very_interesting, etc.)
│       ├── FeedbackButtons.tsx       # Confirm/correct buttons
│       └── ErrorBanner.tsx           # In-app error notification
│
└── api/
    └── agent.ts                      # API client for agent endpoints
```

### Error Banner

Display when capability has `status: "error"`:

```tsx
// In AgentDashboard or layout
const { data: capabilities } = useCapabilities();
const errorCapabilities = capabilities?.filter(c => c.status === 'error');

{errorCapabilities?.length > 0 && (
  <Banner variant="warning">
    <AlertIcon />
    <span>Slack connection needs attention.</span>
    <Link to={`/agent/capabilities/${errorCapabilities[0].id}`}>
      Fix now
    </Link>
  </Banner>
)}
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Observation frequency | Every 4 hours | Balance between freshness and compute efficiency |
| Storage strategy | Interesting + 10% sample | ~85% storage reduction vs storing everything |
| Checkpointing | Per-channel | Lightweight, enables resume on failure |
| Classification | LLM with few-shot | Simple, works well with few examples |
| Categories | 3 (very/interesting/not) | Simple, covers main use cases |
| Low confidence handling | `needs_review` flag | Surfaces uncertainty to user |
| Learning | Examples-based | Feedback becomes training data |
| Digest | On-demand | Compute only when user needs it |
| Embeddings | NOT in MVP | Not needed for few-shot classification |
| Channel selection | Opt-in | User controls what's monitored |
| Preference scope | Per capability_type | Future-proof for drafter, etc. |
| Task framework | Celery + Redis | Mature, battle-tested, good scheduling |

---

## Error Handling

### Slack API Errors

| Error | Handling |
|-------|----------|
| Rate limit (429) | Exponential backoff, retry up to 3 times |
| Auth error (401/403) | Mark capability `status: "error"`, show banner |
| Channel not found | Skip channel, log warning, continue |
| Temporary (5xx) | Retry up to 3 times with backoff |

### Classification Errors

| Error | Handling |
|-------|----------|
| LLM timeout | Retry once, then mark observations as `needs_review` |
| Invalid response | Log error, mark observations as `needs_review` |
| Rate limit | Queue and retry with backoff |

### Task Failures

| Scenario | Handling |
|----------|----------|
| Worker crash mid-task | Celery `task_acks_late` ensures retry |
| Redis connection lost | Celery auto-reconnects |
| Repeated failures | Alert via logging, manual intervention |

---

## Phase 2 (Future)

### Actions & Drafting

```
AgentTask table (new)
├── Task queue for agent actions
├── Approval workflow
└── Execution tracking

Capabilities:
├── slack_drafter - Generate reply drafts
├── slack_sender - Send approved messages
└── Approval UI in frontend
```

### Learning Improvements

```
├── Pattern extraction from examples (LLM-based)
├── Automatic re-learning triggers
├── Confidence calibration
└── Progressive autonomy based on accuracy
```

### Digest Enhancements

```
├── Scheduled email digests
├── Push notifications for very_interesting
├── Thread expansion UI
└── Cross-day digest summaries
```

### Multi-Platform

```
├── Email observer
├── Calendar observer
├── Cross-platform preferences (universal)
└── Unified multi-source digest
```

---

## Implementation Checklist

### Infrastructure
- [ ] Add Redis to Render (or Upstash)
- [ ] Configure Celery app
- [ ] Deploy Celery worker + beat processes
- [ ] Add environment variables

### Database
- [ ] Create migration for 4 new tables
- [ ] Add indexes
- [ ] Test cascade deletes

### Backend - Observer
- [ ] `SlackObserver` class
- [ ] Message text extraction (handle mentions, links)
- [ ] Checkpoint management
- [ ] Slack API error handling

### Backend - Classification
- [ ] `Classifier` class
- [ ] Prompt templates
- [ ] Batch processing (max 15 messages)
- [ ] Confidence thresholds

### Backend - Services
- [ ] `DigestService`
- [ ] `FeedbackService`
- [ ] Preference management

### Backend - API
- [ ] `/agent/capabilities` endpoints
- [ ] `/agent/digest` endpoint
- [ ] `/agent/observations/{id}/feedback` endpoint
- [ ] `/agent/preferences` endpoints

### Backend - Tasks
- [ ] `observe_all_clones` task
- [ ] `observe_and_classify_for_clone` task
- [ ] Error handling and retries

### Frontend
- [ ] Agent dashboard page
- [ ] Slack setup wizard
- [ ] Digest page
- [ ] Observation cards with feedback
- [ ] Error banner component

### Testing
- [ ] Unit tests for classifier
- [ ] Integration tests for observation flow
- [ ] E2E test for setup → observe → digest → feedback

### Deployment
- [ ] Update render.yaml
- [ ] Environment variable setup
- [ ] Monitoring/alerting setup

---

## Appendix: Slack Message Text Extraction

Slack messages contain rich formatting that needs normalization:

```python
def extract_text(message: dict) -> str:
    """Extract plain text from Slack message"""
    text = message.get("text", "")

    # Resolve user mentions: <@U123> → @username
    # Requires user lookup or just use @user
    text = re.sub(r'<@(\w+)>', r'@user', text)

    # Resolve channel mentions: <#C123|channel-name> → #channel-name
    text = re.sub(r'<#\w+\|([^>]+)>', r'#\1', text)

    # Clean link formatting: <url|display> → display, <url> → url
    text = re.sub(r'<([^|>]+)\|([^>]+)>', r'\2', text)
    text = re.sub(r'<([^>]+)>', r'\1', text)

    # Remove emoji shortcodes or keep them (they can be meaningful)
    # text = re.sub(r':[\w+-]+:', '', text)  # Optional

    return text.strip()
```

Messages to skip (pre-filter before classification):

```python
SKIP_SUBTYPES = [
    "channel_join",
    "channel_leave",
    "channel_topic",
    "channel_purpose",
    "channel_name",
    "bot_add",
    "bot_remove",
]

def should_process(message: dict) -> bool:
    if message.get("subtype") in SKIP_SUBTYPES:
        return False
    if not message.get("text", "").strip():
        return False
    return True
```
