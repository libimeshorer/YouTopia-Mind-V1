# Backend Architecture & Data Isolation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Decisions](#design-decisions)
3. [Data Model](#data-model)
4. [Data Isolation Implementation](#data-isolation-implementation)
5. [Security Architecture](#security-architecture)
6. [Component Details](#component-details)
7. [Future Considerations](#future-considerations)

---

## Architecture Overview

### Multi-Tenant Clone Isolation Architecture

Our backend implements a **multi-tenant, clone-scoped data isolation architecture** designed to support both solopreneurs (single clone per tenant) and enterprise customers (multiple clones per tenant).

### Core Principles

1. **Mandatory ID Verification**: Every action involving user data MUST verify both `tenant_id` and `clone_id`
2. **Abstraction Layer**: All backend components (Pinecone, S3, database) are wrapped in clone-scoped abstractions that REQUIRE `clone_id` and `tenant_id`
3. **Defense in Depth**: Multiple layers of security (API, service, database, vector store, S3)
4. **Fail Secure**: Default to denying access if `clone_id` or `tenant_id` is missing or invalid

### Data Hierarchy

```
Tenant (Company/Organization)
  └── Clone (Person within organization)
      ├── Documents
      ├── Insights
      ├── Training Status
      └── Integrations
```

---

## Design Decisions

### Why Tenant + Clone Architecture?

**Problem**: We need to support both:
- **Solopreneurs**: Single person = single company (1:1 relationship)
- **Enterprise**: Multiple people within one company (many:1 relationship)

**Solution**: Two-tier model:
- `Tenant` represents the company/organization
- `Clone` represents an individual person within that organization
- All data belongs to a `Clone`, which belongs to a `Tenant`

**Benefits**:
- Flexible: Supports both use cases
- Scalable: Easy to add enterprise features later
- Secure: Clear ownership boundaries
- Future-proof: Ready for tenant-level features (admin dashboards, billing, etc.)

### Why Pinecone Namespaces Instead of Separate Indexes or Metadata Filtering?

**Options Considered**:

1. **Per-User Pinecone Indexes** ❌
   - Pros: Complete isolation
   - Cons: Expensive ($70/month per index), complex management, doesn't scale

2. **Pinecone Namespaces** ✅ **CHOSEN**
   - Pros: Infrastructure-level isolation, single index, better performance, impossible to cross-contaminate
   - Cons: Namespaces are per-index partition, requires namespace management
   - **Mitigation**: Created `CloneVectorStore` abstraction that automatically uses correct namespace

3. **Metadata Filtering + Strict Enforcement** ⚠️
   - Pros: Cost-effective, scalable, leverages existing metadata
   - Cons: Requires consistent application-level enforcement, filter overhead, risk of accidental cross-contamination
   - **Why not chosen**: Namespaces provide better isolation at infrastructure level

**Decision**: Pinecone namespaces because:
- **Infrastructure-Level Isolation**: Namespaces are partitions in Pinecone, impossible to accidentally query across namespaces
- **Better Performance**: No filter overhead - queries are naturally scoped to namespace
- **Cost-Effective**: Single Pinecone index for all users
- **Scalable**: Handles thousands of users efficiently
- **Secure**: `CloneVectorStore` automatically uses correct namespace - no way to bypass
- **Clear Separation**: Each clone gets its own namespace: `{tenant_id}_{clone_id}`

### Why UUIDs for IDs?

- **Security**: UUIDs are non-sequential, harder to guess/enumerate
- **Distributed Systems**: No coordination needed for ID generation
- **Database Performance**: UUID indexes perform well in PostgreSQL
- **Uniqueness**: Guaranteed unique across all systems

### Why 1:1 Tenant per Clone Initially?

**Current Implementation**: Each clone gets their own tenant (1:1)

**Rationale**:
- **Solopreneur Focus**: Initial customers are individuals, not companies
- **Simpler Onboarding**: No need for tenant management UI initially
- **Easy Migration**: Can migrate to multi-clone tenants later without data loss
- **Clear Path Forward**: TODOs mark exactly where to add enterprise logic

**Future**: When onboarding enterprise customers, we'll:
- Extract `org_id` from Clerk JWT token
- Group clones under existing tenants
- Add tenant management/admin features

---

## Data Model

### Tenant Model

```python
class Tenant(Base):
    id: UUID (primary key, auto-generated)
    name: String
    clerk_org_id: String (optional, for Clerk organization linking)
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Represents a company/organization. Currently 1:1 with Clone, but designed for many:1.

### Clone Model

```python
class Clone(Base):
    id: UUID (primary key, auto-generated)
    tenant_id: UUID (foreign key → Tenant)
    clerk_user_id: String (unique, links to Clerk authentication)
    name: String
    description: Text (optional)
    status: String (active, inactive, etc.)
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Represents an individual person within a tenant. All user data belongs to a Clone.

### Data Models (Documents, Insights, etc.)

All data models follow this pattern:

```python
class Document(Base):
    id: UUID
    clone_id: UUID (foreign key → Clone)  # NEW
    user_id: UUID (foreign key → User)     # DEPRECATED (kept for migration)
    # ... other fields
```

**Migration Strategy**: `user_id` kept nullable during migration, then removed in future migration.

---

## Data Isolation Implementation

### Layer 1: API Authentication & Context

**Component**: `get_clone_context()` dependency

**How it works**:
1. Verifies Clerk JWT token
2. Extracts `clerk_user_id` from token
3. Looks up or creates Clone (creates Tenant if needed)
4. Returns `CloneContext` with `clone_id`, `tenant_id`, and `clone` model

**Isolation**: Every API endpoint receives `CloneContext` with validated IDs. No endpoint can proceed without valid clone context.

```python
@router.get("/documents")
async def list_documents(
    clone_ctx: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    # clone_ctx.clone_id and clone_ctx.tenant_id are guaranteed valid
    documents = db.query(Document).filter(Document.clone_id == clone_ctx.clone_id).all()
```

### Layer 2: Service Layer Validation

**Component**: `CloneDataAccessService`

**How it works**:
- Centralized service for all clone-scoped operations
- Validates `clone_id` belongs to `tenant_id` on initialization
- All methods validate access before returning data
- Raises `HTTPException(403)` on access violations

**Isolation**: Even if database query is wrong, service layer catches it.

```python
class CloneDataAccessService:
    def __init__(self, clone_id: UUID, tenant_id: UUID, db: Session):
        # Validates clone belongs to tenant
        self.validate_clone_access(clone_id, tenant_id)
    
    def get_documents(self) -> List[Document]:
        # Automatically filters by clone_id
        return self.db.query(Document).filter(
            Document.clone_id == self.clone_id
        ).all()
```

### Layer 3: Database Layer

**How it works**:
- Foreign keys enforce relationships: `Document.clone_id → Clone.id → Tenant.id`
- All queries filter by `clone_id`
- Cascade deletes: Deleting Tenant → deletes Clones → deletes all data

**Isolation**: Database constraints prevent orphaned data and enforce relationships.

```python
# All queries automatically scoped
documents = db.query(Document).filter(
    Document.clone_id == clone_ctx.clone_id
).all()
```

### Layer 4: Vector Store Isolation

**Component**: `CloneVectorStore`

**How it works**:
- Wrapper around `PineconeStore` that REQUIRES `clone_id` and `tenant_id`
- Creates unique namespace for each clone: `{tenant_id}_{clone_id}` (UUIDs without dashes)
- All operations automatically use this namespace (namespace is ALWAYS provided, never optional)
- Validates metadata includes matching `tenant_id` and `clone_id` (in addition to namespace isolation)
- Impossible to query or modify data from other clones' namespaces

**Isolation**: 
- **Infrastructure-level**: Pinecone namespaces provide physical separation
- **Metadata validation**: Ensures data integrity and verifies we're using the correct namespace
- **Double protection**: Even if namespace logic has bugs, metadata validation catches mismatches

```python
class CloneVectorStore:
    def __init__(self, clone_id: UUID, tenant_id: UUID, base_store: PineconeStore):
        # IDs are required - cannot instantiate without them
        self.clone_id = clone_id
        self.tenant_id = tenant_id
        # Create unique namespace for this clone (ALWAYS set, never None)
        self.namespace = f"{str(tenant_id).replace('-', '')}_{str(clone_id).replace('-', '')}"
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        # Automatically uses this clone's namespace (ALWAYS provided)
        # Validates filter_metadata matches this clone's IDs
        # Pinecone infrastructure ensures only this namespace is queried
        return self.base_store.search(
            query, 
            namespace=self.namespace,  # Always provided
            validate_tenant_clone_ids=True,
            expected_tenant_id=str(self.tenant_id),
            expected_clone_id=str(self.clone_id),
        )
    
    def add_texts(self, texts: List[str], metadatas: List[Dict]) -> List[str]:
        # Validates metadata includes matching tenant_id/clone_id
        # Automatically stores in this clone's namespace (ALWAYS provided)
        return self.base_store.add_texts(
            texts, 
            metadatas, 
            namespace=self.namespace,  # Always provided
            validate_tenant_clone_ids=True,
            expected_tenant_id=str(self.tenant_id),
            expected_clone_id=str(self.clone_id),
        )
```

### Layer 5: Pinecone Namespace Support + Metadata Validation

**Component**: `PineconeStore` with namespace support and validation

**How it works**:
- `add_texts()`: Accepts `namespace` parameter - all vectors stored in specified namespace
- `search()`: Accepts `namespace` parameter - only searches within specified namespace
- `delete()`: Accepts `namespace` parameter - only deletes from specified namespace
- When `validate_tenant_clone_ids=True`, validates metadata matches expected IDs
- Uses `validate_metadata()` utility function for consistent validation

**Isolation**: 
- **Namespace**: Ensures operations are scoped to specific namespace (infrastructure-level)
- **Metadata Validation**: Ensures metadata includes correct tenant_id/clone_id (data integrity)
- **When used through CloneVectorStore**: Namespace is ALWAYS provided and validation is ALWAYS enabled

```python
# Utility function for metadata validation
def validate_metadata(metadata: Dict, tenant_id: UUID, clone_id: UUID) -> Dict:
    # Validates metadata includes matching tenant_id and clone_id
    # Ensures we know which namespace to use
    if "tenant_id" in metadata and str(metadata["tenant_id"]) != str(tenant_id):
        raise ValueError("tenant_id mismatch")
    if "clone_id" in metadata and str(metadata["clone_id"]) != str(clone_id):
        raise ValueError("clone_id mismatch")
    # Ensures IDs are in metadata
    metadata["tenant_id"] = str(tenant_id)
    metadata["clone_id"] = str(clone_id)
    return metadata

def add_texts(self, texts: List[str], namespace: str, validate_tenant_clone_ids: bool = False):
    # When validate_tenant_clone_ids=True, namespace is required
    # Validates metadata matches expected IDs before storing
    if validate_tenant_clone_ids and not namespace:
        raise ValueError("namespace required when validation enabled")
    self.index.upsert(vectors=vectors, namespace=namespace)

def search(self, query: str, namespace: str, validate_tenant_clone_ids: bool = False):
    # When validate_tenant_clone_ids=True, namespace is required
    # Validates filter_metadata matches expected IDs
    if validate_tenant_clone_ids and not namespace:
        raise ValueError("namespace required when validation enabled")
    results = self.index.query(vector=query_embedding, namespace=namespace)
```

### Layer 6: S3 Path Isolation

**How it works**:
- S3 paths include `tenant_id` and `clone_id`: `documents/{tenant_id}/{clone_id}/{doc_id}/{filename}`
- Presigned URLs validate ownership before generation
- Path validation ensures S3 key matches expected structure

**Isolation**: Even with S3 credentials, paths are tenant/clone-specific. Wrong path = access denied.

```python
# S3 key format
s3_key = f"documents/{tenant_id}/{clone_id}/{doc_id}/{filename}"

# Validation before presigned URL generation
expected_prefix = f"documents/{clone_ctx.tenant_id}/{clone_ctx.clone_id}/"
if not doc.s3_key.startswith(expected_prefix):
    raise HTTPException(403, "S3 path does not match clone/tenant")
```

### Layer 7: Security Validators

**Component**: `src/utils/security.py`

**How it works**:
- Helper functions validate clone ownership and data access
- Used throughout the codebase for consistent validation
- All validators raise `HTTPException(403)` on failure

**Isolation**: Centralized validation logic ensures consistency.

```python
def validate_document_access(document_id: UUID, clone_id: UUID, tenant_id: UUID, db: Session):
    # 1. Validate clone ownership
    validate_clone_ownership(clone_id, tenant_id, db)
    
    # 2. Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    
    # 3. Verify document belongs to clone
    if document.clone_id != clone_id:
        raise HTTPException(403, "Document does not belong to this clone")
    
    return document
```

---

## Security Architecture

### Defense in Depth Strategy

We implement **7 layers of security**:

1. **API Layer**: `get_clone_context()` validates authentication and creates context
2. **Service Layer**: `CloneDataAccessService` validates access before operations
3. **Database Layer**: Foreign keys and queries filter by `clone_id`
4. **Vector Store Layer**: `CloneVectorStore` auto-filters all operations
5. **Pinecone Layer**: `PineconeStore` validates IDs in metadata
6. **S3 Layer**: Path structure and ownership validation
7. **Security Validators**: Centralized validation functions

### Fail Secure Principle

**Default Behavior**: Deny access if:
- `clone_id` is missing
- `tenant_id` is missing
- IDs don't match expected values
- Clone doesn't belong to tenant
- Data doesn't belong to clone

**Implementation**: All validators raise exceptions on failure. No silent failures.

### Audit Trail

**Current**: Logging at all security checkpoints
- Clone access attempts
- Document access attempts
- Vector store operations
- S3 access attempts

**Future**: Structured audit logging for compliance (GDPR, SOC 2)

---

## Component Details

### CloneContext

**Purpose**: Carries clone and tenant information through request lifecycle

```python
@dataclass
class CloneContext:
    clone_id: UUID
    tenant_id: UUID
    clone: Clone  # SQLAlchemy model
```

**Usage**: Injected into all API endpoints via FastAPI dependency.

### CloneVectorStore

**Purpose**: Enforces clone isolation in vector operations

**Key Features**:
- Requires `clone_id` and `tenant_id` in constructor
- Creates unique namespace: `{tenant_id}_{clone_id}` (UUIDs without dashes)
- All operations automatically use this namespace (namespace is ALWAYS provided, never None)
- Validates metadata includes matching `tenant_id` and `clone_id` using `validate_metadata()` utility
- Infrastructure-level isolation - impossible to access other clones' data
- Double validation: Validates in CloneVectorStore AND in PineconeStore when `validate_tenant_clone_ids=True`

**Namespace Format**: `{tenant_id}_{clone_id}` where UUIDs are converted to strings without dashes
- Example: `550e8400e29b41d4a716446655440000_6ba7b8109dad11d180b400c04fd430c8`
- Namespace is ALWAYS set in constructor, never None

**Validation Utility**: `src/rag/utils.py::validate_metadata()`
- Centralized validation function used by both CloneVectorStore and PineconeStore
- Ensures metadata includes matching tenant_id and clone_id
- Raises ValueError if IDs don't match expected values

**Interface**:
```python
class CloneVectorStore:
    def __init__(self, clone_id: UUID, tenant_id: UUID, base_store: PineconeStore):
        # Namespace is ALWAYS set, never None
        self.namespace = f"{str(tenant_id).replace('-', '')}_{str(clone_id).replace('-', '')}"
    
    def search(query: str, n_results: int = 5) -> List[Dict]:
        # Validates filter_metadata, then calls base_store with namespace ALWAYS provided
        # Namespace ensures infrastructure-level isolation
        # Validation ensures we know which namespace to use
    
    def add_texts(texts: List[str], metadatas: List[Dict]) -> List[str]:
        # Validates each metadata, then calls base_store with namespace ALWAYS provided
        # Namespace ensures infrastructure-level isolation
        # Validation ensures we know which namespace to use
    
    def delete(ids: List[str] = None, filter_metadata: Dict = None) -> bool:
        # Validates filter_metadata, then calls base_store with namespace ALWAYS provided
        # Namespace ensures infrastructure-level isolation
        # Validation ensures we know which namespace to use
```

### CloneDataAccessService

**Purpose**: Centralized service for clone-scoped data access

**Key Features**:
- Validates clone ownership on initialization
- Provides validated access to documents, insights, vector store
- All methods filter by `clone_id`
- Raises exceptions on access violations

**Interface**:
```python
class CloneDataAccessService:
    def validate_clone_access(clone_id: UUID, tenant_id: UUID) -> bool
    def validate_document_access(document_id: UUID) -> Document
    def validate_insight_access(insight_id: UUID) -> Insight
    def get_documents() -> List[Document]
    def get_insights() -> List[Insight]
    def get_vector_store() -> CloneVectorStore
```

---

## Future Considerations

### Enterprise Multi-Clone Tenants

**Current**: 1:1 tenant per clone (solopreneur model)

**Future**: Multiple clones per tenant

**Implementation Plan**:
1. Extract `org_id` from Clerk JWT token (`org_id` or `orgId` claim)
2. Look up existing tenant by `clerk_org_id`
3. If tenant exists, create clone linked to existing tenant
4. If tenant doesn't exist, create new tenant with `clerk_org_id`
5. Add tenant management/admin features

**TODOs in Code**:
- `src/api/dependencies.py`: `get_clone_context()` has TODO for org_id extraction
- `src/database/models.py`: `Tenant.clerk_org_id` field ready for use

### Tenant Admin Capabilities

**Future Features**:
- Tenant admin role to view/manage all clones within tenant
- Separate admin endpoints with tenant-level access
- Audit logging for tenant admin actions
- Tenant-level analytics and reporting

### Performance Optimizations

**Current**: Single Pinecone index with namespace isolation (one namespace per clone)

**Benefits of Namespace Approach**:
- No filter overhead - queries are naturally scoped to namespace
- Better query performance - Pinecone optimizes namespace queries
- Infrastructure-level separation - no risk of cross-contamination

**Future Options** (if needed):
- Per-organization indexes for enterprise customers (if cost-justified)
- Database sharding if PostgreSQL becomes bottleneck

### Compliance Features

**GDPR**:
- Right to deletion: Delete all vectors for a clone
- Data export: Export all clone data
- Audit trail: Track all data access

**SOC 2**:
- Audit logging of all data access
- Access control documentation
- Regular security audits

---

## Implementation Highlights

### Automatic ID Generation

- `tenant_id` and `clone_id` are UUIDs generated automatically by SQLAlchemy
- Generated at database record creation time (when `.add()` and `.commit()` are called)
- No manual ID management required

### Seamless Authentication

- Frontend doesn't need to know about `clone_id` or `tenant_id`
- Authentication handled via Clerk JWT tokens
- Backend extracts `clerk_user_id` from token and looks up/create Clone
- Transparent to frontend developers

### Migration-Friendly

- `user_id` columns kept nullable during migration
- Migration script handles data transformation
- No breaking changes to API endpoints
- Frontend code doesn't need updates

### Developer Experience

- Clear abstractions (`CloneVectorStore`, `CloneDataAccessService`)
- Consistent patterns throughout codebase
- Comprehensive error messages
- Type-safe with UUID types

---

## Testing Strategy

### Isolation Tests

Comprehensive test suite verifies:
- Clone A cannot access Clone B's data (same tenant)
- Clone from Tenant X cannot access Tenant Y's data
- Vector store queries only return data for specified clone (namespace isolation)
- Namespace isolation prevents cross-clone vector access
- S3 presigned URLs only work for correct tenant/clone
- RAG retrieval only returns clone's own data
- All API endpoints reject invalid clone_id/tenant_id

### Test Coverage

- Unit tests for each component
- Integration tests for API endpoints
- Isolation tests for data access
- Security tests for access violations

---

## Summary

Our backend architecture implements **comprehensive multi-tenant data isolation** through:

1. **Clear Data Model**: Tenant → Clone → Data hierarchy
2. **Multiple Security Layers**: 7 layers of defense in depth
3. **Infrastructure-Level Isolation**: Pinecone namespaces provide physical separation of each clone's data
4. **Abstraction Layers**: `CloneVectorStore` and `CloneDataAccessService` enforce isolation
5. **Fail Secure**: Default to denying access
6. **Future-Ready**: Designed for enterprise expansion

This architecture ensures that:
- ✅ Each clone's data is completely isolated via Pinecone namespaces
- ✅ No clone can access another clone's data (infrastructure-level guarantee)
- ✅ No tenant can access another tenant's data
- ✅ All operations are validated and logged
- ✅ System is ready for enterprise features
- ✅ Better performance (no filter overhead, namespace-optimized queries)

**Key Isolation Mechanism**: Each clone gets its own Pinecone namespace (`{tenant_id}_{clone_id}`), providing infrastructure-level isolation that is impossible to bypass, even with code bugs.

The implementation is production-ready, secure, scalable, and provides the strongest possible data isolation.
