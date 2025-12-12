# Migration Guide: User Model to Clone/Tenant Model

## Overview

This guide documents the migration from a single `User` model to a multi-tenant architecture with `Tenant` and `Clone` models. This enables enterprise support where multiple clones (people) can belong to a single tenant (company).

## What Changed

### Database Schema

1. **New Tables:**
   - `tenants` - Represents companies/organizations
   - `clones` - Represents individuals within organizations

2. **Updated Tables:**
   - All tables now use `clone_id` instead of `user_id`
   - `user_id` columns are kept for backward compatibility during migration (nullable)

### Backend Changes

1. **Authentication:**
   - `get_current_user()` → `get_clone_context()` 
   - Automatically creates Tenant and Clone on first signup (1:1 for solopreneurs)
   - TODO: Update for enterprise multi-clone tenants

2. **Data Access:**
   - All API endpoints now use `clone_id` for filtering
   - `CloneDataAccessService` validates access before any data operation
   - `CloneVectorStore` automatically uses clone-specific namespaces for all vector operations

3. **Vector Store:**
   - Pinecone now uses namespaces for isolation (one namespace per clone: `{tenant_id}_{clone_id}`)
   - All operations automatically scoped to clone's namespace
   - Infrastructure-level isolation - impossible to access other clones' data

4. **S3 Storage:**
   - Paths updated: `documents/{tenant_id}/{clone_id}/...`
   - Ownership validation before generating presigned URLs

## Migration Steps

### 1. Run Database Migration

```bash
# Apply Alembic migration
alembic upgrade head
```

This will:
- Create `tenants` and `clones` tables
- Add `clone_id` columns to existing tables (nullable)
- Create indexes and foreign keys

### 2. Run Data Migration Script

```bash
# Migrate existing User data to Clone/Tenant structure
python scripts/migrate_to_clone_model.py
```

This script will:
- Create a Tenant for each existing User (1:1 relationship)
- Create a Clone for each User
- Update all foreign keys from `user_id` to `clone_id`
- Migrate S3 paths (if applicable)
- Note: Pinecone namespace migration - new vectors will use namespaces automatically. Existing vectors may need re-ingestion.

### 3. Verify Migration

```bash
# Run tests
pytest tests/test_clone_isolation.py -v
```

### 4. Update Application Code

The backend code has already been updated. No frontend changes are required since:
- Authentication is handled via JWT tokens
- Backend extracts `clone_id` from token automatically
- API endpoints remain the same

## Current Implementation: 1:1 Tenant per Clone

**Initial Implementation (Solopreneurs):**
- Each clone gets their own tenant (1:1 relationship)
- When a clone signs up, a new Tenant is automatically created
- Supports solopreneurs who are the only clone in their company

**Future Implementation (Enterprise):**
- TODO: Extract `org_id` from Clerk JWT token
- TODO: Group multiple clones under the same tenant based on organization
- TODO: Create tenant management/admin flow

## Security Features

1. **Mandatory ID Verification:**
   - Every operation requires `clone_id` and `tenant_id`
   - Missing IDs cause operations to fail

2. **Defense in Depth:**
   - API layer: Validates clone context
   - Service layer: `CloneDataAccessService` validates access
   - Database layer: Foreign keys enforce relationships
   - Vector store: `CloneVectorStore` auto-filters
   - S3: Path validation ensures ownership

3. **Fail Secure:**
   - Default to denying access if IDs are missing or invalid
   - All validators raise exceptions on failure

## Testing

Comprehensive isolation tests verify:
- Clones cannot access other clones' data (same tenant)
- Clones cannot access other tenants' data
- Vector store queries are properly isolated via namespaces
- S3 access is properly restricted
- Tenant and Clone creation works correctly
- Namespace isolation prevents cross-clone data access

## Rollback

If you need to rollback:

```bash
# Rollback database migration
alembic downgrade -1
```

Note: Data migration script does not have automatic rollback. You would need to manually restore from backup.

## Troubleshooting

### Issue: Migration fails with "Clone already exists"
- Solution: The migration script skips users that already have clones. This is expected.

### Issue: Pinecone vectors in default namespace
- Solution: Old vectors may be in the default namespace. New vectors will automatically use clone-specific namespaces. Consider re-ingesting documents to move them to the correct namespace, or manually migrate them.

### Issue: S3 paths don't match new structure
- Solution: The migration script attempts to migrate S3 paths, but you may need to manually copy objects if the script fails.

## Next Steps

1. ✅ Run database migration
2. ✅ Run data migration script
3. ✅ Test the implementation
4. ⏳ Monitor for any issues
5. ⏳ Update tenant creation logic when onboarding enterprise customers

## Support

For issues or questions, refer to:
- Plan document: `.cursor/plans/multi-tenant_clone_isolation_b1682265.plan.md`
- Test file: `tests/test_clone_isolation.py`
- Migration script: `scripts/migrate_to_clone_model.py`
