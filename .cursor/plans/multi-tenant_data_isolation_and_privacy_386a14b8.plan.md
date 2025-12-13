---
name: Multi-Tenant Data Isolation and Privacy
overview: Implement comprehensive multi-tenant data isolation strategy across PostgreSQL, Pinecone (vector store), and S3 (file storage) to ensure each user's data is stored separately, privately, and securely with defense-in-depth security measures.
todos:
  - id: enforce_rag_user_filtering
    content: Update RAGRetriever and PromptBuilder to require and enforce user_id filtering in all vector searches
    status: pending
  - id: create_user_scoped_wrapper
    content: Create UserScopedVectorStore wrapper that automatically filters by user_id for all operations
    status: pending
  - id: validate_pinecone_operations
    content: Add user_id validation to all Pinecone operations (search, add, delete)
    status: pending
  - id: update_ingestion_pipeline
    content: Ensure all ingestion paths (documents, Slack, email) include and validate user_id in metadata
    status: pending
  - id: s3_bucket_policies
    content: Implement S3 bucket policies restricting access to user-specific prefixes
    status: pending
  - id: validate_presigned_urls
    content: Add user ownership validation before generating S3 presigned URLs
    status: pending
  - id: create_security_middleware
    content: Create user context middleware and security helpers for consistent filtering
    status: pending
  - id: privacy_tests
    content: Create comprehensive tests verifying users cannot access other users data
    status: pending
  - id: security_audit
    content: Audit all API endpoints and data operations for proper user filtering
    status: pending
---

# Multi-Tenant Data Isolation and Privacy Plan

## Current State Analysis

### ✅ What's Already Working

1. **PostgreSQL Database**: 

- User isolation at SQL level with foreign keys
- All models have `user_id` foreign keys
- API endpoints filter by `user.id` in queries
- Cascade deletes configured

2. **S3 File Storage**:

- User-scoped paths: `documents/{user_id}/{doc_id}/{filename}`
- User-scoped paths for insights: `insights/{user_id}/{insight_id}/...`
- Metadata includes user_id in database

### ❌ Critical Privacy Gaps

1. **Pinecone Vector Store**:

- Single shared index for all users
- Metadata includes `user_id` but filtering is NOT enforced
- RAG queries in `PromptBuilder` don't filter by `user_id`
- Risk of cross-user data leakage
- No infrastructure-level isolation

2. **S3 Access Control**:

- No bucket policies restricting access
- Presigned URLs don't validate user ownership
- No IAM policies for per-user access
- Anyone with a valid S3 key could access files

3. **Application-Level Filtering**:

- No consistent pattern for enforcing user filtering
- Manual filtering required everywhere (error-prone)
- RAG operations don't automatically filter by user

## Recommended Multi-Tenant Strategy

### Approach: Hybrid Multi-Tenancy with Defense-in-Depth

We'll use a combination of:

1. **Application-level filtering** (primary defense)
2. **Metadata-based isolation** (Pinecone)
3. **Infrastructure-level access controls** (S3, IAM)
4. **Middleware/helpers** to enforce filtering consistently

### Why This Approach?

**Option 1: Per-User Pinecone Indexes** ❌

- Pros: Complete isolation
- Cons: Expensive ($70/month per index), complex management, doesn't scale well

**Option 2: Pinecone Namespaces** ⚠️

- Pros: Good isolation, single index
- Cons: Namespaces are per-index partition, still need careful management

**Option 3: Metadata Filtering + Strict Enforcement** ✅ **RECOMMENDED**

- Pros: Cost-effective, scalable, leverages existing metadata
- Cons: Requires consistent application-level enforcement
- Mitigation: Create middleware/helpers to enforce filtering automatically

## Implementation Plan

### Phase 1: Enforce User Filtering in All Queries

#### 1.1 Update RAG Retriever to Require User Context

- Modify `RAGRetriever` to accept `user_id` parameter
- Auto-inject `filter_metadata={"user_id": user_id}` in all searches
- Update `PromptBuilder` to accept and pass `user_id`
- Update `MessageProcessor` to pass `user_id` from context

**Files to modify:**

- `src/rag/retriever.py`: Add user_id parameter and auto-filter
- `src/llm/prompt_builder.py`: Accept user_id and pass to retriever
- `src/bot/message_processor.py`: Extract and pass user_id

#### 1.2 Create User-Scoped Vector Store Wrapper

- Create `UserScopedVectorStore` wrapper that automatically filters by user_id
- Ensures no query can execute without user filtering
- Use in all vector operations

**Files to create:**

- `src/rag/user_scoped_vector_store.py`: Wrapper enforcing user isolation

#### 1.3 Add User Validation to All Pinecone Operations

- Update `PineconeStore.search()` to validate filter_metadata includes user_id
- Update `PineconeStore.add_texts()` to require user_id in metadata
- Update `PineconeStore.delete()` to filter by user_id

**Files to modify:**

- `src/rag/pinecone_store.py`: Add user_id validation

#### 1.4 Update Document Ingestion Pipeline

- Ensure all chunks include `user_id` in metadata
- Add validation step before storing vectors
- Update all ingestion paths (documents, Slack, email)

**Files to modify:**

- `src/api/routers/documents.py`: Verify user_id in metadata
- `src/ingestion/pipeline.py`: Ensure user_id propagation
- `src/ingestion/document_ingester.py`: Validate metadata

### Phase 2: S3 Access Control and Security

#### 2.1 Implement S3 Bucket Policies

- Create bucket policy restricting access to user-specific prefixes
- Only allow access to `documents/{user_id}/*` for authenticated users
- Deny public access to all objects

**Files to create:**

- `deployment/s3_bucket_policy.json`: Bucket policy template

#### 2.2 Add User Validation to Presigned URLs

- Validate user ownership before generating presigned URLs
- Ensure S3 keys match authenticated user's ID
- Add expiration (1 hour) to all presigned URLs

**Files to modify:**

- `src/api/routers/documents.py`: Validate user ownership in preview endpoint
- `src/api/routers/insights.py`: Validate user ownership for audio URLs

#### 2.3 Implement IAM User Policies (Optional, Advanced)

- Create IAM roles/policies for per-user access patterns
- Use STS (Security Token Service) for temporary credentials
- Only if strictest isolation required (adds complexity)

### Phase 3: Database Security Enhancements

#### 3.1 Add Row-Level Security (PostgreSQL RLS) - Optional

- Enable RLS on all tables
- Create policies filtering by user_id automatically
- Adds defense-in-depth at database level

**Files to create:**

- `alembic/versions/xxx_add_rls_policies.py`: Migration for RLS

#### 3.2 Audit All Database Queries

- Ensure all queries include `user_id` filter
- Add database query middleware to enforce filtering
- Log any queries missing user_id filter

**Files to modify:**

- `src/database/db.py`: Add query auditing/logging
- Review all API routers for proper filtering

### Phase 4: Application-Level Security Middleware

#### 4.1 Create User Context Middleware

- FastAPI dependency that ensures user context is always available
- Automatically inject user_id into service layer
- Prevent any operation without user context

**Files to create:**

- `src/api/middleware/user_context.py`: User context dependency

#### 4.2 Create Security Helpers

- Helper functions for user-scoped operations
- Consistent patterns for filtering
- Type-safe user_id handling

**Files to create:**

- `src/utils/security.py`: Security helpers and validators

### Phase 5: Testing and Validation

#### 5.1 Create Privacy Tests

- Test that users cannot access other users' data
- Test Pinecone filtering works correctly
- Test S3 access restrictions
- Test RAG queries return only user's data

**Files to create:**

- `tests/test_multi_tenant_isolation.py`: Comprehensive isolation tests

#### 5.2 Security Audit

- Review all API endpoints for proper user filtering
- Review all vector store operations
- Review all S3 operations
- Document security assumptions

## File Changes Summary

### New Files

- `src/rag/user_scoped_vector_store.py` - User-scoped vector store wrapper
- `src/api/middleware/user_context.py` - User context middleware
- `src/utils/security.py` - Security helpers
- `tests/test_multi_tenant_isolation.py` - Isolation tests
- `deployment/s3_bucket_policy.json` - S3 bucket policy

### Files to Modify

- `src/rag/retriever.py` - Add user_id filtering
- `src/rag/pinecone_store.py` - Add user_id validation
- `src/llm/prompt_builder.py` - Accept and use user_id
- `src/bot/message_processor.py` - Pass user_id
- `src/api/routers/documents.py` - Validate user ownership
- `src/api/routers/insights.py` - Validate user ownership
- `src/ingestion/pipeline.py` - Ensure user_id propagation

## Security Best Practices to Implement

1. **Principle of Least Privilege**: Only access data for authenticated user
2. **Defense in Depth**: Multiple layers of security (app, database, infrastructure)
3. **Fail Secure**: Default to denying access if user context missing
4. **Audit Logging**: Log all data access for security monitoring
5. **Input Validation**: Validate user_id in all operations
6. **Error Handling**: Don't leak information about other users' data existence

## Scaling Considerations

### Current Approach (Metadata Filtering)

- ✅ Scales to thousands of users in single Pinecone index
- ✅ Cost-effective (single index)
- ✅ Easy to manage

### Future Considerations

If you grow beyond 10K+ users with very high query volume:

- Consider Pinecone namespaces for logical separation
- Consider per-organization indexes for enterprise customers
- Consider database sharding if PostgreSQL becomes bottleneck

## Cost Implications

- **Current**: Single Pinecone index (~$70/month base)
- **Per-User Indexes**: $70/user/month (prohibitively expensive)
- **Recommended**: Single index with filtering (same cost, better isolation)

## Compliance Considerations

- GDPR: Right to deletion requires deleting all user vectors
- SOC 2: Audit trail of all data access
- HIPAA (if applicable): Encryption at rest and in transit

## Migration Path

1. Phase 1 & 2 can be implemented immediately (high priority)
2. Phase 3 is optional enhancement
3. Phase 4 adds extra safety layers
4. Phase 5 validates everything works

No data migration required - existing data already has user_id in metadata, just need to enforce filtering.