# Database Migration Best Practices

## 🛡️ Safety Rules

### 1. NEVER Drop Tables in Regular Migrations

❌ **BAD:**
```python
def upgrade():
    op.drop_table('users')  # DESTROYS DATA!
```

✅ **GOOD:**
```python
def upgrade():
    # Rename column instead of recreating table
    op.alter_column('users', 'old_name', new_column_name='new_name')
```

### 2. Use ALTER, Not DROP + CREATE

When changing schema:
- Use `ALTER TABLE` to modify existing structures
- Use `ALTER COLUMN` to change column types
- Use `ADD COLUMN` with defaults for new fields
- Use `DROP COLUMN` only for truly unused columns (after deprecation period)

### 3. Data Migration Pattern

When restructuring data:

```python
def upgrade():
    # Step 1: Add new columns
    op.add_column('users', sa.Column('new_field', sa.String(), nullable=True))

    # Step 2: Migrate data
    connection = op.get_bind()
    connection.execute(
        "UPDATE users SET new_field = old_field WHERE old_field IS NOT NULL"
    )

    # Step 3: Make NOT NULL (if needed) after data is migrated
    op.alter_column('users', 'new_field', nullable=False)

    # Step 4: Drop old column (only after verifying new column works)
    # Consider doing this in a SEPARATE migration after verification
    # op.drop_column('users', 'old_field')
```

### 4. Production Safeguards

Add environment checks for risky operations:

```python
import os

def upgrade():
    env = os.getenv('ENVIRONMENT', 'development')

    if env == 'production':
        # Extra validation for production
        # Or block certain operations entirely
        raise Exception("Review this migration before running in production!")

    # ... migration code
```

### 5. Testing Migrations

Before deploying:

```bash
# 1. Test upgrade
alembic upgrade head

# 2. Test downgrade (verify it's reversible)
alembic downgrade -1

# 3. Test upgrade again
alembic upgrade head

# 4. Verify data integrity
python scripts/verify_schema.py
```

### 6. Review SQL Before Running

```bash
# Generate SQL without executing
alembic upgrade head --sql > migration.sql

# Review the SQL, then apply manually if needed
psql $DATABASE_URL < migration.sql
```

## 📋 Migration Checklist

Before creating a migration:

- [ ] Can this be done with ALTER instead of DROP?
- [ ] Is there a data migration strategy?
- [ ] Are there proper defaults for new columns?
- [ ] Is the migration reversible (downgrade works)?
- [ ] Have you tested on a copy of production data?
- [ ] Are there safeguards for production?
- [ ] Is there a rollback plan?

## 🚨 The 001_initial_clean_schema.py Exception

The `001_initial_clean_schema.py` migration is a **one-time reset migration** that should:
- Only run during initial setup
- NEVER run on production with real data
- Be protected by `ALLOW_DESTRUCTIVE_MIGRATIONS` flag

**Future migrations should NOT follow this pattern!**

## 📚 Common Patterns

### Adding a Column
```python
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))

def downgrade():
    op.drop_column('users', 'phone')
```

### Renaming a Column
```python
def upgrade():
    op.alter_column('users', 'name', new_column_name='full_name')

def downgrade():
    op.alter_column('users', 'full_name', new_column_name='name')
```

### Adding an ENUM Value
```python
def upgrade():
    # Postgres requires this approach
    op.execute("ALTER TYPE user_status ADD VALUE 'suspended'")

def downgrade():
    # Removing enum values is complex - consider migration strategy
    pass
```

### Creating an Index
```python
def upgrade():
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email')
```

## 🔍 Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- Local testing: See `docs/LOCAL_TESTING.md`
