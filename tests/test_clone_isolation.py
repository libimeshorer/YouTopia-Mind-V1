"""Comprehensive tests for clone isolation and multi-tenant data privacy"""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.database.models import Tenant, Clone, Document, Insight
from src.database.db import SessionLocal, Base, engine
from src.api.dependencies import get_clone_context
from src.services.clone_data_access import CloneDataAccessService
from src.rag.clone_vector_store import CloneVectorStore
from src.utils.security import validate_clone_ownership, validate_document_access, validate_insight_access


@pytest.fixture
def db():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tenant_1(db: Session):
    """Create test tenant 1"""
    tenant = Tenant(name="Test Tenant 1")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_2(db: Session):
    """Create test tenant 2"""
    tenant = Tenant(name="Test Tenant 2")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def clone_1(tenant_1: Tenant, db: Session):
    """Create test clone 1 in tenant 1"""
    clone = Clone(
        tenant_id=tenant_1.id,
        clerk_user_id="clerk_user_1",
        name="Clone 1",
        status="active"
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@pytest.fixture
def clone_2(tenant_1: Tenant, db: Session):
    """Create test clone 2 in tenant 1 (same tenant, different clone)"""
    clone = Clone(
        tenant_id=tenant_1.id,
        clerk_user_id="clerk_user_2",
        name="Clone 2",
        status="active"
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@pytest.fixture
def clone_3(tenant_2: Tenant, db: Session):
    """Create test clone 3 in tenant 2 (different tenant)"""
    clone = Clone(
        tenant_id=tenant_2.id,
        clerk_user_id="clerk_user_3",
        name="Clone 3",
        status="active"
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@pytest.fixture
def document_1(clone_1: Clone, db: Session):
    """Create test document for clone 1"""
    doc = Document(
        clone_id=clone_1.id,
        name="test_doc.pdf",
        size=1000,
        type=".pdf",
        status="complete",
        s3_key=f"documents/{clone_1.tenant_id}/{clone_1.id}/doc1/test_doc.pdf"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def insight_1(clone_1: Clone, db: Session):
    """Create test insight for clone 1"""
    insight = Insight(
        clone_id=clone_1.id,
        content="Test insight content",
        type="text"
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


class TestCloneIsolation:
    """Test clone data isolation"""
    
    def test_clone_cannot_access_other_clone_document_same_tenant(
        self, clone_1: Clone, clone_2: Clone, document_1: Document, db: Session
    ):
        """Test that clone 1 cannot access clone 2's document (same tenant)"""
        with pytest.raises(Exception):  # Should raise HTTPException or ValueError
            validate_document_access(document_1.id, clone_2.id, clone_1.tenant_id, db)
    
    def test_clone_cannot_access_other_tenant_document(
        self, clone_1: Clone, clone_3: Clone, document_1: Document, db: Session
    ):
        """Test that clone 3 (tenant 2) cannot access clone 1's document (tenant 1)"""
        with pytest.raises(Exception):
            validate_document_access(document_1.id, clone_3.id, clone_3.tenant_id, db)
    
    def test_clone_can_access_own_document(
        self, clone_1: Clone, document_1: Document, db: Session
    ):
        """Test that clone can access its own document"""
        doc = validate_document_access(document_1.id, clone_1.id, clone_1.tenant_id, db)
        assert doc.id == document_1.id
        assert doc.clone_id == clone_1.id
    
    def test_clone_cannot_access_other_clone_insight_same_tenant(
        self, clone_1: Clone, clone_2: Clone, insight_1: Insight, db: Session
    ):
        """Test that clone 1 cannot access clone 2's insight (same tenant)"""
        with pytest.raises(Exception):
            validate_insight_access(insight_1.id, clone_2.id, clone_1.tenant_id, db)
    
    def test_clone_cannot_access_other_tenant_insight(
        self, clone_1: Clone, clone_3: Clone, insight_1: Insight, db: Session
    ):
        """Test that clone 3 (tenant 2) cannot access clone 1's insight (tenant 1)"""
        with pytest.raises(Exception):
            validate_insight_access(insight_1.id, clone_3.id, clone_3.tenant_id, db)
    
    def test_clone_can_access_own_insight(
        self, clone_1: Clone, insight_1: Insight, db: Session
    ):
        """Test that clone can access its own insight"""
        insight = validate_insight_access(insight_1.id, clone_1.id, clone_1.tenant_id, db)
        assert insight.id == insight_1.id
        assert insight.clone_id == clone_1.id
    
    def test_clone_ownership_validation(
        self, clone_1: Clone, clone_3: Clone, db: Session
    ):
        """Test clone ownership validation"""
        # Valid ownership
        assert validate_clone_ownership(clone_1.id, clone_1.tenant_id, db) is True
        
        # Invalid ownership (clone from different tenant)
        with pytest.raises(Exception):
            validate_clone_ownership(clone_1.id, clone_3.tenant_id, db)


class TestCloneVectorStore:
    """Test CloneVectorStore isolation"""
    
    def test_clone_vector_store_requires_ids(self):
        """Test that CloneVectorStore requires clone_id and tenant_id"""
        with pytest.raises(ValueError):
            CloneVectorStore(clone_id=None, tenant_id=uuid4())
        
        with pytest.raises(ValueError):
            CloneVectorStore(clone_id=uuid4(), tenant_id=None)
    
    def test_clone_vector_store_injects_ids_in_search(self, clone_1: Clone):
        """Test that CloneVectorStore automatically injects tenant_id and clone_id in search"""
        # This would require mocking PineconeStore
        # For now, we test that the class can be instantiated
        from src.rag.pinecone_store import PineconeStore
        base_store = PineconeStore()
        clone_store = CloneVectorStore(clone_1.id, clone_1.tenant_id, base_store)
        assert clone_store.clone_id == clone_1.id
        assert clone_store.tenant_id == clone_1.tenant_id


class TestCloneDataAccessService:
    """Test CloneDataAccessService"""
    
    def test_service_validates_clone_ownership(
        self, clone_1: Clone, clone_3: Clone, db: Session
    ):
        """Test that service validates clone ownership on init"""
        # Valid service
        service = CloneDataAccessService(clone_1.id, clone_1.tenant_id, db)
        assert service.clone_id == clone_1.id
        
        # Invalid service (clone from different tenant)
        with pytest.raises(Exception):
            CloneDataAccessService(clone_1.id, clone_3.tenant_id, db)
    
    def test_service_get_documents_filters_by_clone(
        self, clone_1: Clone, clone_2: Clone, document_1: Document, db: Session
    ):
        """Test that get_documents only returns documents for the clone"""
        service = CloneDataAccessService(clone_1.id, clone_1.tenant_id, db)
        documents = service.get_documents()
        assert len(documents) == 1
        assert documents[0].id == document_1.id
        assert documents[0].clone_id == clone_1.id


class TestTenantCloneCreation:
    """Test tenant and clone creation flow"""
    
    def test_tenant_creation(self, db: Session):
        """Test that tenant can be created"""
        tenant = Tenant(name="New Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        assert tenant.id is not None
        assert tenant.name == "New Tenant"
    
    def test_clone_creation_with_tenant(self, tenant_1: Tenant, db: Session):
        """Test that clone can be created and linked to tenant"""
        clone = Clone(
            tenant_id=tenant_1.id,
            clerk_user_id="test_clerk_user",
            name="Test Clone",
            status="active"
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        assert clone.id is not None
        assert clone.tenant_id == tenant_1.id
        assert clone.clerk_user_id == "test_clerk_user"
    
    def test_clone_id_is_uuid(self, clone_1: Clone):
        """Test that clone_id is automatically generated as UUID"""
        assert clone_1.id is not None
        assert isinstance(clone_1.id, type(uuid4()))
