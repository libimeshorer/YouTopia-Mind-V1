"""Test PostgreSQL connection on Render"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
from src.config.settings import settings
from src.database.db import Base, engine
from src.database.models import Tenant, Clone, Document, Insight, TrainingStatus, Integration
from src.utils.logging import get_logger
import uuid

logger = get_logger(__name__)


def test_basic_connection():
    """Test basic database connectivity"""
    print("\n" + "="*70)
    print("TEST 1: Basic Connection")
    print("="*70)
    
    try:
        # Try to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {version}")
            
            # Get current database name
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"   Database: {db_name}")
            
            # Get connection info
            result = conn.execute(text("SELECT inet_server_addr(), inet_server_port();"))
            server_info = result.fetchone()
            if server_info[0]:
                print(f"   Server: {server_info[0]}:{server_info[1]}")
            
            return True
    except OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_database_info():
    """Show database information"""
    print("\n" + "="*70)
    print("TEST 2: Database Information")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            # Check database size
            result = conn.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size;
            """))
            size = result.fetchone()[0]
            print(f"   Database size: {size}")
            
            # Check existing tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if tables:
                print(f"   Existing tables ({len(tables)}):")
                for table in tables:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM {table};
                    """))
                    count = result.fetchone()[0]
                    print(f"     - {table}: {count} rows")
            else:
                print("   No tables exist yet (will be created)")
            
            return True
    except Exception as e:
        print(f"❌ Error getting database info: {e}")
        return False


def test_create_tables():
    """Test creating all tables"""
    print("\n" + "="*70)
    print("TEST 3: Create Tables")
    print("="*70)
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"   Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"     - {table}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def test_crud_operations():
    """Test basic CRUD operations"""
    print("\n" + "="*70)
    print("TEST 4: CRUD Operations")
    print("="*70)
    
    from src.database.db import get_db_session
    
    session = None
    try:
        session = get_db_session()
        
        # CREATE: Insert test tenant
        test_tenant = Tenant(
            name="Test Tenant",
            clerk_org_id="org_test_123"
        )
        session.add(test_tenant)
        session.commit()
        print(f"✅ Created test tenant: {test_tenant.id}")
        
        # CREATE: Insert test clone
        test_clone = Clone(
            tenant_id=test_tenant.id,
            clerk_user_id="user_test_123",
            name="Test Clone",
            description="Test clone for connection testing",
            status="active"
        )
        session.add(test_clone)
        session.commit()
        print(f"✅ Created test clone: {test_clone.id}")
        
        # READ: Query the data back
        queried_tenant = session.query(Tenant).filter_by(id=test_tenant.id).first()
        assert queried_tenant.name == "Test Tenant"
        print(f"✅ Read tenant: {queried_tenant.name}")
        
        queried_clone = session.query(Clone).filter_by(id=test_clone.id).first()
        assert queried_clone.name == "Test Clone"
        print(f"✅ Read clone: {queried_clone.name}")
        
        # UPDATE: Modify the clone
        test_clone.description = "Updated description"
        session.commit()
        updated_clone = session.query(Clone).filter_by(id=test_clone.id).first()
        assert updated_clone.description == "Updated description"
        print(f"✅ Updated clone description")
        
        # DELETE: Remove test data
        session.delete(test_clone)
        session.delete(test_tenant)
        session.commit()
        print(f"✅ Deleted test data")
        
        # Verify deletion
        assert session.query(Tenant).filter_by(id=test_tenant.id).first() is None
        assert session.query(Clone).filter_by(id=test_clone.id).first() is None
        print(f"✅ Verified deletion")
        
        return True
    except Exception as e:
        print(f"❌ CRUD operation failed: {e}")
        if session:
            session.rollback()
        return False
    finally:
        if session:
            session.close()


def test_relationships():
    """Test model relationships"""
    print("\n" + "="*70)
    print("TEST 5: Model Relationships")
    print("="*70)
    
    from src.database.db import get_db_session
    
    session = None
    try:
        session = get_db_session()
        
        # Create tenant with clone and document
        tenant = Tenant(name="Relationship Test Tenant")
        session.add(tenant)
        session.flush()
        
        clone = Clone(
            tenant_id=tenant.id,
            clerk_user_id=f"user_rel_test_{uuid.uuid4().hex[:8]}",
            name="Relationship Test Clone"
        )
        session.add(clone)
        session.flush()
        
        document = Document(
            clone_id=clone.id,
            name="test_document.pdf",
            size=1024,
            type="application/pdf",
            status="pending",
            s3_key="test/key"
        )
        session.add(document)
        session.commit()
        
        # Test relationships
        queried_tenant = session.query(Tenant).filter_by(id=tenant.id).first()
        assert len(queried_tenant.clones) == 1
        assert queried_tenant.clones[0].name == "Relationship Test Clone"
        print(f"✅ Tenant -> Clone relationship works")
        
        queried_clone = session.query(Clone).filter_by(id=clone.id).first()
        assert queried_clone.tenant.name == "Relationship Test Tenant"
        assert len(queried_clone.documents) == 1
        print(f"✅ Clone -> Tenant and Clone -> Document relationships work")
        
        # Cleanup
        session.delete(document)
        session.delete(clone)
        session.delete(tenant)
        session.commit()
        print(f"✅ Cleaned up test data")
        
        return True
    except Exception as e:
        print(f"❌ Relationship test failed: {e}")
        if session:
            session.rollback()
        return False
    finally:
        if session:
            session.close()


def main():
    """Run all tests"""
    # Default to development if not explicitly set
    if not os.getenv("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "development"
        # Reload settings with new environment
        from src.config.settings import load_settings
        global settings
        settings = load_settings()
    
    is_production = settings.environment.lower() in ["production", "prod"]
    
    print("\n" + "="*70)
    print("RENDER POSTGRESQL CONNECTION TEST")
    print("="*70)
    print(f"Environment: {settings.environment}")
    print(f"Database URL: {settings.database_url[:50]}...")
    
    if is_production:
        print("\n⚠️  PRODUCTION MODE - Running READ-ONLY tests")
        print("   (No writes, creates, updates, or deletes)")
    else:
        print("\n✅ DEVELOPMENT MODE - Running FULL test suite")
    
    # Run tests based on environment
    results = {}
    
    # Always run read-only tests
    results["Basic Connection"] = test_basic_connection()
    results["Database Info"] = test_database_info()
    
    # Only run write tests in development
    if not is_production:
        results["Create Tables"] = test_create_tables()
        results["CRUD Operations"] = test_crud_operations()
        results["Relationships"] = test_relationships()
    else:
        print("\n" + "="*70)
        print("SKIPPING WRITE TESTS (Production Environment)")
        print("="*70)
        print("   ⏭️  Skipped: Create Tables")
        print("   ⏭️  Skipped: CRUD Operations")
        print("   ⏭️  Skipped: Relationships")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nPassed: {passed}/{total} tests")
    
    if passed == total:
        if is_production:
            print("\n🎉 Production database connection verified! (Read-only tests passed)")
        else:
            print("\n🎉 All tests passed! Your Render PostgreSQL connection is working perfectly!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
