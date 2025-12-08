# Multi-Integration Training System Implementation Plan

## Overview

This plan outlines the implementation of 7+ integrations (Gmail, Google Drive, Slack, X/Twitter, Substack, LinkedIn, Fathom) with OAuth authentication, credential storage, continuous syncing, and data ingestion into vector DB.

## Architecture Decision: MCP vs Traditional Approach

**Recommendation: Hybrid Approach (Traditional Backend + MCP for Read Operations)**

**Why not pure MCP:**
- MCP is designed for on-demand AI tool access, not continuous background syncing
- Credential management and OAuth flows require persistent backend services
- Need for scheduled jobs, webhooks, and state management
- Vector DB indexing requires batch processing, not real-time queries

**Hybrid approach:**
- **Backend API Server** (FastAPI): Handle OAuth, credential storage, sync orchestration
- **Background Workers** (AWS EventBridge + Lambda): Continuous syncing and ingestion
- **MCP Servers** (Optional): For real-time read operations during conversations
- **Ingestion Pipeline**: Existing pipeline extended for new integrations

## Additional Integrations to Recommend

1. **Notion** - Personal knowledge base, notes, documents
2. **GitHub/GitLab** - Code repositories, commit messages, PR discussions
3. **Calendar (Google Calendar)** - Meeting notes, event descriptions
4. **Discord** - Community interactions (if applicable)
5. **Medium** - Published articles (similar to Substack)
6. **YouTube** - Video transcripts (if creator)

## Implementation Architecture

### 1. Backend API Server (FastAPI)

**File: `src/api/server.py`** - FastAPI application
- OAuth callback endpoints for each integration
- Integration management endpoints (connect, disconnect, sync, status)
- Webhook endpoints for real-time updates
- Health checks and monitoring
- Deploy to AWS (ECS Fargate or EC2) behind API Gateway

**Dependencies to add:**
- `fastapi==0.109.0`
- `uvicorn[standard]==0.27.0`
- `sqlalchemy==2.0.25` (for credential storage)
- `alembic==1.13.1` (database migrations)
- `psycopg2-binary==2.9.9` (PostgreSQL driver)

### 2. Database Schema for Integration State

**File: `src/database/models.py`** - SQLAlchemy models

```python
class Integration:
    id: UUID
    user_id: str  # From Clerk
    type: str  # gmail, google_drive, slack, x, substack, linkedin, fathom
    status: str  # connected, disconnected, error
    credentials: JSON  # Encrypted OAuth tokens
    last_sync_at: datetime
    last_sync_status: str
    sync_settings: JSON  # Per-integration config
    created_at: datetime
    updated_at: datetime

class SyncJob:
    id: UUID
    integration_id: UUID
    status: str  # pending, running, completed, failed
    started_at: datetime
    completed_at: datetime
    items_processed: int
    error_message: str
```

**Database: PostgreSQL (RDS)**
- Use RDS PostgreSQL for production
- Connection pooling with SQLAlchemy
- Automated backups enabled
- Multi-AZ for high availability

### 3. OAuth & Credential Management

**File: `src/integrations/auth/oauth_manager.py`**
- OAuth 2.0 flow handlers for each provider
- Token refresh logic
- Encrypted credential storage (use AWS KMS or similar)
- Token expiration handling

**Per-integration OAuth requirements:**
- **Gmail**: Google OAuth (gmail.readonly, gmail.send, gmail.modify)
- **Google Drive**: Google OAuth (drive.readonly, drive.file)
- **Slack**: OAuth (already partially implemented)
- **X/Twitter**: OAuth 2.0 (tweet.read, users.read)
- **Substack**: OAuth or API key (check Substack API)
- **LinkedIn**: OAuth 2.0 (r_liteprofile, r_emailaddress, w_member_social)
- **Fathom**: API key or OAuth (check Fathom API)

### 4. Integration Ingesters (Extend Existing Pattern)

**New files to create:**
- `src/ingestion/gmail_ingester.py` - Gmail API client, email fetching
- `src/ingestion/google_drive_ingester.py` - Drive API, file listing/downloading
- `src/ingestion/x_ingester.py` - Twitter API v2, tweet fetching
- `src/ingestion/substack_ingester.py` - Substack API, article fetching
- `src/ingestion/linkedin_ingester.py` - LinkedIn API, profile & posts
- `src/ingestion/fathom_ingester.py` - Fathom API, transcript fetching

**Extend existing:**
- `src/ingestion/slack_ingester.py` - Add webhook support for real-time updates
- `src/ingestion/email_ingester.py` - Enhance for Gmail-specific features

**Pattern to follow:**
```python
class GmailIngester:
    def __init__(self, credentials: dict):
        # Initialize API client with OAuth tokens
        
    def fetch_emails(self, since: datetime, limit: int) -> List[Dict]:
        # Fetch emails from Gmail API
        
    def ingest_emails(self, emails: List[Dict]) -> List[Dict]:
        # Format, chunk, return chunks with metadata
```

### 5. Background Sync System (AWS EventBridge + Lambda)

**Architecture:**
- **EventBridge Rules**: Scheduled cron expressions for periodic syncs (e.g., every 6 hours)
- **Lambda Functions**: One per integration type (`sync_gmail`, `sync_google_drive`, etc.)
- **SQS Queues**: For webhook-triggered syncs (decouple webhook reception from processing)
- **DLQ**: Dead letter queues for failed syncs

**Files to create:**
- `deployment/lambda_sync_gmail.py` - Gmail sync Lambda
- `deployment/lambda_sync_google_drive.py` - Drive sync Lambda
- `deployment/lambda_sync_x.py` - X/Twitter sync Lambda
- `deployment/lambda_sync_substack.py` - Substack sync Lambda
- `deployment/lambda_sync_linkedin.py` - LinkedIn sync Lambda
- `deployment/lambda_sync_fathom.py` - Fathom sync Lambda
- `src/workers/sync_orchestrator.py` - Shared sync logic

**Sync Strategy:**
- **Initial sync**: Fetch all historical data (with pagination, can take hours)
- **Incremental sync**: Only fetch new items since last_sync_at
- **Webhook sync**: Real-time updates via SQS → Lambda
- **Rate limiting**: Respect API rate limits, implement exponential backoff
- **State tracking**: Store sync state in PostgreSQL (last_sync_at, cursor positions)

### 6. Webhook Handlers

**File: `src/api/webhooks.py`**
- Gmail push notifications
- Google Drive change notifications
- Slack events (already partially implemented)
- LinkedIn webhooks (if available)

### 7. Update Ingestion Pipeline

**File: `src/ingestion/pipeline.py`** - Extend with new methods:
```python
def ingest_gmail(self, since: datetime, limit: int) -> int
def ingest_google_drive(self, folder_id: str = None) -> int
def ingest_x_posts(self, user_id: str, since: datetime) -> int
def ingest_substack(self, publication_id: str) -> int
def ingest_linkedin(self, profile_fields: List[str]) -> int
def ingest_fathom(self, meeting_ids: List[str]) -> int
```

## Implementation Steps

### Phase 1: Foundation (Week 1-2)
1. Set up FastAPI backend server (`src/api/server.py`)
2. Create PostgreSQL database (RDS instance or local for dev)
3. Create database models and Alembic migrations (`src/database/models.py`)
4. Implement OAuth manager base class (`src/integrations/auth/oauth_manager.py`)
5. Set up credential encryption (AWS KMS for production, local key for dev)
6. Create integration registry pattern (`src/integrations/registry.py`)
7. Set up AWS EventBridge rules and Lambda function templates

### Phase 2: Core Integrations (Week 3-5)
1. **Gmail**: OAuth flow, email fetching, send/draft capabilities
2. **Google Drive**: OAuth flow, file listing, document download
3. **Slack**: Enhance existing with webhook support
4. **X/Twitter**: OAuth, tweet fetching, rate limit handling

### Phase 3: Content Integrations (Week 6-7)
1. **Substack**: API integration, article fetching
2. **LinkedIn**: OAuth, profile extraction, post fetching
3. **Fathom**: API integration, transcript fetching

### Phase 4: Sync Infrastructure (Week 8-9)
1. Background worker setup (EventBridge + Lambda)
2. Incremental sync logic
3. Webhook handlers
4. Error handling and retries

### Phase 5: Frontend Updates (Week 10)
1. Update integration cards with new types
2. Add OAuth callback handling
3. Sync status indicators
4. Error display and retry UI

## Challenges & Risks

### Technical Challenges

1. **OAuth Token Management**
   - **Risk**: Tokens expire, need refresh logic
   - **Solution**: Implement automatic token refresh, store refresh tokens securely

2. **API Rate Limits**
   - **Risk**: Hitting rate limits during bulk syncs
   - **Solution**: Implement exponential backoff, respect rate limit headers, queue-based processing

3. **Data Volume**
   - **Risk**: Large email/drive histories could be millions of items
   - **Solution**: Pagination, incremental syncs, prioritize recent data, allow user to set date ranges

4. **Real-time Sync Complexity**
   - **Risk**: Webhooks require persistent endpoints, complex state management
   - **Solution**: Use AWS API Gateway + Lambda for webhooks, or webhook proxy service (ngrok for dev)

5. **Credential Security**
   - **Risk**: Storing OAuth tokens in database
   - **Solution**: Encrypt at rest (AWS KMS), use least-privilege scopes, regular security audits

6. **LinkedIn API Limitations**
   - **Risk**: LinkedIn API is restrictive, may not allow full post history
   - **Solution**: Use LinkedIn API v2, check available endpoints, may need manual export as fallback

7. **X/Twitter API Costs**
   - **Risk**: Twitter API v2 has usage limits, may require paid tier
   - **Solution**: Check API tier limits, implement efficient pagination, consider caching

### Business/Product Risks

1. **User Privacy Concerns**
   - **Risk**: Users may be uncomfortable granting broad access
   - **Solution**: Clear permissions explanation, granular scope requests, data retention policies

2. **Integration Maintenance**
   - **Risk**: APIs change, integrations break
   - **Solution**: Version API clients, monitor API changelogs, implement health checks

3. **Cost Scaling**
   - **Risk**: Embedding generation costs scale with data volume
   - **Solution**: Implement data deduplication, smart chunking, allow users to limit sync scope

## What's Possible vs Impossible

### ✅ Fully Possible
- Gmail (read, send, draft) - Well-documented API
- Google Drive (read, monitor changes) - Robust API
- Slack (all channels) - Already partially implemented
- X/Twitter (read posts) - API v2 supports this
- Substack (read articles) - If API available or RSS parsing
- Fathom (transcripts) - If API provides access

### ⚠️ Partially Possible / Limitations
- **LinkedIn**: API restrictions may limit historical post access. Profile extraction is possible, but full post history may require manual export.
- **X/Twitter**: Free tier has strict rate limits. May need paid API access for production use.
- **Substack**: May need to parse RSS feeds if official API is limited.

### ❌ Not Possible (Without Workarounds)
- **Gmail "all future inbox"**: Requires IMAP IDLE or Gmail Push notifications (possible but complex)
- **LinkedIn Full History**: API doesn't provide unlimited historical access
- **X/Twitter**: Free tier very limited, may need paid access

## Recommended Tech Stack Additions

```python
# requirements.txt additions
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9  # PostgreSQL driver
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-api-python-client==2.108.0
tweepy==4.14.0  # Twitter API v2
linkedin-api==2.0.0  # LinkedIn (unofficial, may need alternative)
python-jose[cryptography]==3.3.0  # JWT handling
cryptography==42.0.2  # Credential encryption
boto3==1.34.34  # Already present, for KMS
feedparser==6.0.10  # For Substack RSS if needed
```

## Database Migration Strategy

1. Use PostgreSQL from the start (local Docker container for dev, RDS for production)
2. Use Alembic for migrations (`alembic init`, then create migrations)
3. Connection string via environment variable: `DATABASE_URL=postgresql://user:pass@host/db`
4. Use connection pooling (SQLAlchemy engine with pool_size)

## Monitoring & Observability

- Integration health checks (FastAPI `/health` endpoint)
- Sync job status dashboard (query PostgreSQL SyncJob table)
- API rate limit monitoring (CloudWatch metrics from Lambda)
- Error tracking (CloudWatch Logs + optional Sentry)
- Cost tracking (CloudWatch for Lambda invocations, OpenAI usage tracking)
- Dead letter queue monitoring (SQS DLQ alerts)

## AWS Infrastructure Components

1. **RDS PostgreSQL**: Database for credentials and sync state
2. **API Gateway**: Front FastAPI server (or ECS Fargate with ALB)
3. **Lambda Functions**: One per integration sync type
4. **EventBridge**: Scheduled rules for periodic syncs
5. **SQS Queues**: Webhook processing queues + DLQs
6. **KMS**: Encrypt OAuth tokens at rest
7. **Secrets Manager**: Store database credentials, API keys
8. **CloudWatch**: Logs, metrics, alarms

## Key Files to Create/Modify

### New Files
- `src/api/server.py` - FastAPI application
- `src/api/webhooks.py` - Webhook handlers
- `src/database/models.py` - SQLAlchemy models
- `src/database/db.py` - Database connection and session management
- `src/integrations/auth/oauth_manager.py` - OAuth flow handlers
- `src/integrations/registry.py` - Integration registry
- `src/ingestion/gmail_ingester.py` - Gmail ingester
- `src/ingestion/google_drive_ingester.py` - Google Drive ingester
- `src/ingestion/x_ingester.py` - X/Twitter ingester
- `src/ingestion/substack_ingester.py` - Substack ingester
- `src/ingestion/linkedin_ingester.py` - LinkedIn ingester
- `src/ingestion/fathom_ingester.py` - Fathom ingester
- `src/workers/sync_orchestrator.py` - Shared sync logic
- `deployment/lambda_sync_*.py` - Lambda functions for each integration
- `alembic/env.py` - Alembic configuration
- `alembic/versions/*.py` - Database migrations

### Files to Modify
- `src/ingestion/pipeline.py` - Add new ingestion methods
- `src/ingestion/slack_ingester.py` - Add webhook support
- `src/ingestion/email_ingester.py` - Enhance for Gmail
- `src/config/settings.py` - Add new configuration options
- `requirements.txt` - Add new dependencies
- `frontend/src/types/index.ts` - Update Integration type if needed
- `frontend/src/components/features/IntegrationCard.tsx` - Add new integration types

## Next Steps

1. Review and approve this plan
2. Set up development environment (PostgreSQL, AWS credentials)
3. Begin Phase 1 implementation
4. Test OAuth flows with one integration first (recommend Gmail or Google Drive)
5. Iterate and refine based on learnings
