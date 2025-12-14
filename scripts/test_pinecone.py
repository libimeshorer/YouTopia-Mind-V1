#!/usr/bin/env python3
"""
Pinecone Connection Test Script

Tests Pinecone connection, index creation, and vector operations.

Usage:
  python scripts/test_pinecone.py                    # Uses youtopia-dev by default
  python scripts/test_pinecone.py --index youtopia-prod  # Test specific index
  
Environment:
  PINECONE_INDEX_NAME: Override via environment variable (takes precedence)
"""

import sys
import os
import time
import argparse
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pinecone_store import PineconeStore
from src.rag.embeddings import EmbeddingService
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def test_settings():
    """Test 1: Verify settings are loaded correctly"""
    print_header("Test 1: Settings Configuration")
    
    try:
        print_info(f"Pinecone API Key: {'*' * 20}...{settings.pinecone_api_key[-4:] if len(settings.pinecone_api_key) > 4 else '***'}")
        print_info(f"Pinecone Index Name: {settings.pinecone_index_name}")
        print_info(f"OpenAI API Key: {'*' * 20}...{settings.openai_api_key[-4:] if len(settings.openai_api_key) > 4 else '***'}")
        print_info(f"Embedding Model: {settings.openai_embedding_model}")
        
        if not settings.pinecone_api_key:
            print_error("PINECONE_API_KEY is not set!")
            return False
        
        if not settings.openai_api_key:
            print_error("OPENAI_API_KEY is not set!")
            return False
        
        print_success("Settings loaded successfully")
        return True
    except Exception as e:
        print_error(f"Failed to load settings: {str(e)}")
        return False


def test_embedding_service():
    """Test 2: Test embedding generation"""
    print_header("Test 2: Embedding Service")
    
    try:
        embedding_service = EmbeddingService()
        dimension = embedding_service.get_embedding_dimension()
        print_info(f"Expected dimension: {dimension}")
        
        # Test single embedding
        test_text = "This is a test document for Pinecone connection testing."
        print_info(f"Generating embedding for: '{test_text[:50]}...'")
        
        embedding = embedding_service.embed_text(test_text)
        
        if not embedding:
            print_error("Embedding generation returned empty result")
            return False, None
        
        if len(embedding) != dimension:
            print_error(f"Embedding dimension mismatch! Expected {dimension}, got {len(embedding)}")
            return False, None
        
        print_success(f"Embedding generated successfully (dimension: {len(embedding)})")
        
        # Test batch embeddings
        test_texts = [
            "First test document",
            "Second test document",
            "Third test document"
        ]
        print_info(f"Generating batch embeddings for {len(test_texts)} texts...")
        
        embeddings = embedding_service.embed_texts(test_texts)
        
        if len(embeddings) != len(test_texts):
            print_error(f"Batch embedding count mismatch! Expected {len(test_texts)}, got {len(embeddings)}")
            return False, None
        
        print_success(f"Batch embeddings generated successfully")
        
        return True, dimension
    except Exception as e:
        print_error(f"Embedding service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_pinecone_connection():
    """Test 3: Test Pinecone client connection"""
    print_header("Test 3: Pinecone Client Connection")
    
    try:
        from pinecone import Pinecone
        
        pc = Pinecone(api_key=settings.pinecone_api_key)
        print_info("Pinecone client initialized")
        
        # List indexes
        print_info("Listing existing indexes...")
        indexes = list(pc.list_indexes())
        
        print_info(f"Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f"  - {idx.name}")
        
        print_success("Pinecone connection successful")
        return True, pc
    except Exception as e:
        print_error(f"Pinecone connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_index_creation(pc, dimension: int):
    """Test 4: Test index creation/access"""
    print_header("Test 4: Index Creation/Access")
    
    try:
        index_name = settings.pinecone_index_name
        print_info(f"Target index name: {index_name}")
        
        # Check if index exists
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        
        if index_name in existing_indexes:
            print_info(f"Index '{index_name}' already exists")
            print_info("Connecting to existing index...")
            index = pc.Index(index_name)
            
            # Get index stats
            stats = index.describe_index_stats()
            print_info(f"Index stats:")
            print(f"  - Total vectors: {stats.total_vector_count}")
            print(f"  - Dimension: {stats.dimension}")
            print(f"  - Index fullness: {stats.index_fullness if hasattr(stats, 'index_fullness') else 'N/A'}")
            
            if stats.dimension != dimension:
                print_warning(f"Index dimension ({stats.dimension}) doesn't match expected ({dimension})")
                print_warning("This may cause issues with embeddings!")
            
            print_success(f"Successfully connected to index '{index_name}'")
            return True, index
        else:
            print_info(f"Index '{index_name}' does not exist")
            print_info(f"Creating new index with dimension {dimension}...")
            
            from pinecone import ServerlessSpec
            
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            print_info("Waiting for index to be ready...")
            # Wait for index to be ready (can take a few seconds)
            max_wait = 30
            waited = 0
            while waited < max_wait:
                try:
                    index = pc.Index(index_name)
                    stats = index.describe_index_stats()
                    print_success(f"Index '{index_name}' created and ready!")
                    print_info(f"Index dimension: {stats.dimension}")
                    return True, index
                except Exception:
                    time.sleep(2)
                    waited += 2
                    print_info(f"Waiting... ({waited}s)")
            
            print_error("Index creation timed out")
            return False, None
            
    except Exception as e:
        print_error(f"Index creation/access failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_vector_operations(pinecone_store: PineconeStore):
    """Test 5: Test vector operations (upsert, query, delete) WITHOUT namespace"""
    print_header("Test 5: Vector Operations (Without Namespace)")
    
    print_info("Note: This test intentionally uses PineconeStore without namespaces")
    print_info("Namespace warnings are expected and demonstrate the design guidance")
    print_info("See Test 7 for namespace usage and Test 8 for CloneVectorStore\n")
    
    test_texts = [
        "Python is a high-level programming language",
        "FastAPI is a modern web framework for building APIs",
        "Pinecone is a vector database for machine learning applications",
        "OpenAI provides powerful language models and embeddings",
        "Vector databases enable semantic search capabilities"
    ]
    
    test_metadata = [
        {"source": "test", "type": "programming"},
        {"source": "test", "type": "framework"},
        {"source": "test", "type": "database"},
        {"source": "test", "type": "ai"},
        {"source": "test", "type": "search"}
    ]
    
    try:
        # Test upsert
        print_info(f"Upserting {len(test_texts)} test vectors...")
        vector_ids = pinecone_store.add_texts(
            texts=test_texts,
            metadatas=test_metadata
        )
        
        if not vector_ids or len(vector_ids) != len(test_texts):
            print_error(f"Upsert failed! Expected {len(test_texts)} IDs, got {len(vector_ids) if vector_ids else 0}")
            return False
        
        print_success(f"Successfully upserted {len(vector_ids)} vectors")
        print_info(f"Vector IDs: {vector_ids[:3]}..." if len(vector_ids) > 3 else f"Vector IDs: {vector_ids}")
        
        # Wait a moment for indexing
        print_info("Waiting for vectors to be indexed...")
        time.sleep(2)
        
        # Test query
        query_text = "What is a vector database?"
        print_info(f"Querying with: '{query_text}'")
        
        results = pinecone_store.search(query_text, n_results=3)
        
        if not results:
            print_error("Query returned no results")
            return False
        
        print_success(f"Query returned {len(results)} results:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. Score: {1 - result.get('distance', 0):.4f}")
            print(f"     Text: {result.get('text', '')[:60]}...")
            print(f"     Metadata: {result.get('metadata', {})}")
        
        # Test metadata filtering
        print_info("Testing metadata filtering...")
        filtered_results = pinecone_store.search(
            query_text,
            n_results=3,
            filter_metadata={"type": "database"}
        )
        
        if filtered_results:
            print_success(f"Filtered query returned {len(filtered_results)} results")
            for result in filtered_results:
                if result.get('metadata', {}).get('type') != 'database':
                    print_warning(f"Filter may not be working correctly")
        else:
            print_warning("No results with filter (this may be normal)")
        
        # Test collection count
        count = pinecone_store.get_collection_count()
        print_info(f"Total vectors in index: {count}")
        
        # Test delete
        print_info(f"Deleting test vectors...")
        delete_success = pinecone_store.delete(ids=vector_ids)
        
        if delete_success:
            print_success(f"Successfully deleted {len(vector_ids)} vectors")
        else:
            print_error("Failed to delete vectors")
            return False
        
        # Verify deletion
        time.sleep(1)
        new_count = pinecone_store.get_collection_count()
        print_info(f"Vectors after deletion: {new_count}")
        
        if new_count < count:
            print_success("Deletion verified (vector count decreased)")
        else:
            print_warning("Vector count didn't decrease (may take time to update)")
        
        return True
        
    except Exception as e:
        print_error(f"Vector operations test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_pinecone_store_integration():
    """Test 6: Test full PineconeStore integration"""
    print_header("Test 6: PineconeStore Integration")
    
    try:
        print_info("Initializing PineconeStore...")
        pinecone_store = PineconeStore()
        
        print_success("PineconeStore initialized successfully")
        print_info(f"Index name: {pinecone_store.index_name}")
        print_info(f"Embedding dimension: {pinecone_store.dimension}")
        
        return True, pinecone_store
    except Exception as e:
        print_error(f"PineconeStore initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_vector_operations_with_namespace(pinecone_store: PineconeStore):
    """Test 7: Test vector operations WITH namespace"""
    print_header("Test 7: Vector Operations (With Namespace)")
    
    test_namespace = "test-tenant-clone-123"
    
    test_texts = [
        "Python is a high-level programming language",
        "FastAPI is a modern web framework for building APIs",
        "Pinecone is a vector database for machine learning applications",
    ]
    
    test_metadata = [
        {"source": "test", "type": "programming", "tenant_id": "tenant-123", "clone_id": "clone-123"},
        {"source": "test", "type": "framework", "tenant_id": "tenant-123", "clone_id": "clone-123"},
        {"source": "test", "type": "database", "tenant_id": "tenant-123", "clone_id": "clone-123"},
    ]
    
    try:
        # Test upsert with namespace
        print_info(f"Upserting {len(test_texts)} test vectors with namespace '{test_namespace}'...")
        vector_ids = pinecone_store.add_texts(
            texts=test_texts,
            metadatas=test_metadata,
            namespace=test_namespace
        )
        
        if not vector_ids or len(vector_ids) != len(test_texts):
            print_error(f"Upsert failed! Expected {len(test_texts)} IDs, got {len(vector_ids) if vector_ids else 0}")
            return False
        
        print_success(f"Successfully upserted {len(vector_ids)} vectors to namespace")
        print_info(f"Vector IDs: {vector_ids[:2]}..." if len(vector_ids) > 2 else f"Vector IDs: {vector_ids}")
        
        # Wait for indexing
        print_info("Waiting for vectors to be indexed...")
        time.sleep(2)
        
        # Test query with namespace
        query_text = "What is a programming language?"
        print_info(f"Querying with namespace: '{query_text}'")
        
        results = pinecone_store.search(query_text, n_results=2, namespace=test_namespace)
        
        if not results:
            print_error("Query returned no results")
            return False
        
        print_success(f"Query returned {len(results)} results from namespace:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Score: {1 - result.get('distance', 0):.4f}")
            print(f"     Text: {result.get('text', '')[:60]}...")
            print(f"     Metadata: {result.get('metadata', {})}")
        
        # Test namespace isolation
        print_info("Testing namespace isolation...")
        results_wrong_ns = pinecone_store.search(
            query_text, 
            n_results=2, 
            namespace="different-namespace-456"
        )
        
        if len(results_wrong_ns) == 0:
            print_success("✓ Namespace isolation confirmed (no results in different namespace)")
        else:
            print_warning(f"Found {len(results_wrong_ns)} results in different namespace")
        
        # Test metadata filtering within namespace
        print_info("Testing metadata filtering within namespace...")
        filtered_results = pinecone_store.search(
            query_text,
            n_results=3,
            filter_metadata={"type": "programming"},
            namespace=test_namespace
        )
        
        if filtered_results:
            print_success(f"Filtered query returned {len(filtered_results)} results")
            for result in filtered_results:
                if result.get('metadata', {}).get('type') != 'programming':
                    print_warning("Filter may not be working correctly")
                else:
                    print_info(f"  ✓ Correct filter: type={result.get('metadata', {}).get('type')}")
        else:
            print_warning("No results with filter (this may be normal)")
        
        # Cleanup
        print_info(f"Deleting test vectors from namespace...")
        delete_success = pinecone_store.delete(ids=vector_ids, namespace=test_namespace)
        
        if delete_success:
            print_success(f"Successfully deleted {len(vector_ids)} vectors from namespace")
        else:
            print_error("Failed to delete vectors")
            return False
        
        # Verify deletion
        time.sleep(1)
        verify_results = pinecone_store.search(query_text, n_results=2, namespace=test_namespace)
        if len(verify_results) == 0:
            print_success("Deletion verified (no results in namespace)")
        else:
            print_warning(f"Still found {len(verify_results)} results after deletion (may take time to update)")
        
        return True
        
    except Exception as e:
        print_error(f"Namespace vector operations test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_clone_vector_store():
    """Test 8: Test CloneVectorStore (with automatic namespace management)"""
    print_header("Test 8: CloneVectorStore (Multi-Tenant Architecture)")
    
    try:
        from uuid import uuid4
        from src.rag.clone_vector_store import CloneVectorStore
        
        # Create test tenant and clone IDs
        tenant_id = uuid4()
        clone_id = uuid4()
        
        print_info(f"Creating CloneVectorStore for tenant: {tenant_id}")
        print_info(f"Clone ID: {clone_id}")
        
        # Initialize CloneVectorStore (automatically manages namespace)
        clone_store = CloneVectorStore(
            tenant_id=tenant_id,
            clone_id=clone_id
        )
        
        print_success("CloneVectorStore initialized")
        print_info(f"Auto-generated namespace: {clone_store.namespace}")
        
        # Add texts (no namespace parameter needed - handled automatically!)
        test_texts = [
            "This is tenant-specific data for the AI clone",
            "Another document that belongs to this specific clone",
            "Multi-tenant isolation is critical for security",
        ]
        
        test_metadata = [
            {"source": "test", "type": "doc", "category": "security"},
            {"source": "test", "type": "doc", "category": "data"},
            {"source": "test", "type": "doc", "category": "architecture"},
        ]
        
        print_info(f"Adding {len(test_texts)} texts to clone (namespace auto-managed)...")
        vector_ids = clone_store.add_texts(
            texts=test_texts,
            metadatas=test_metadata
        )
        
        if not vector_ids or len(vector_ids) != len(test_texts):
            print_error(f"Add texts failed! Expected {len(test_texts)} IDs, got {len(vector_ids) if vector_ids else 0}")
            return False
        
        print_success(f"Added {len(vector_ids)} vectors (namespace: {clone_store.namespace})")
        print_info(f"Vector IDs: {vector_ids[:2]}..." if len(vector_ids) > 2 else f"Vector IDs: {vector_ids}")
        
        # Wait for indexing
        print_info("Waiting for vectors to be indexed...")
        time.sleep(2)
        
        # Search (no namespace parameter needed - handled automatically!)
        query_text = "tenant data security"
        print_info(f"Searching within clone: '{query_text}'")
        
        results = clone_store.search(query_text, n_results=2)
        
        if not results:
            print_error("Search returned no results")
            return False
        
        print_success(f"Found {len(results)} results in clone namespace:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Score: {1 - result.get('distance', 0):.4f}")
            print(f"     Text: {result.get('text', '')[:60]}...")
            metadata = result.get('metadata', {})
            print(f"     Tenant ID: {metadata.get('tenant_id', 'N/A')}")
            print(f"     Clone ID: {metadata.get('clone_id', 'N/A')}")
        
        # Test isolation - create another clone for the SAME tenant
        print_info("\nTesting namespace isolation with different clone (same tenant)...")
        other_clone_id = uuid4()
        other_clone_store = CloneVectorStore(
            tenant_id=tenant_id,  # Same tenant
            clone_id=other_clone_id  # Different clone
        )
        
        print_info(f"Other clone namespace: {other_clone_store.namespace}")
        
        # Search in other clone (should return nothing due to namespace isolation)
        other_results = other_clone_store.search(query_text, n_results=2)
        
        if len(other_results) == 0:
            print_success("✓ Namespace isolation verified (other clone sees no data)")
        else:
            print_error(f"❌ Isolation FAILED! Found {len(other_results)} results in other clone's namespace")
            return False
        
        # Test with additional metadata filtering
        print_info("\nTesting metadata filtering within clone namespace...")
        filtered_results = clone_store.search(
            query_text,
            n_results=3,
            filter_metadata={"category": "security"}
        )
        
        if filtered_results:
            print_success(f"Filtered search returned {len(filtered_results)} results")
            for result in filtered_results:
                category = result.get('metadata', {}).get('category')
                if category == 'security':
                    print_info(f"  ✓ Correct filter: category={category}")
                else:
                    print_warning(f"  ⚠ Filter mismatch: category={category}")
        
        # Cleanup
        print_info("\nCleaning up test data...")
        delete_success = clone_store.delete(ids=vector_ids)
        
        if delete_success:
            print_success(f"Successfully deleted {len(vector_ids)} vectors from clone namespace")
        else:
            print_error("Failed to delete vectors")
            return False
        
        # Verify deletion
        time.sleep(1)
        verify_results = clone_store.search(query_text, n_results=2)
        if len(verify_results) == 0:
            print_success("Deletion verified (no results in clone namespace)")
        else:
            print_warning(f"Still found {len(verify_results)} results after deletion (may take time to update)")
        
        print_success("\nCloneVectorStore test completed successfully!")
        return True
        
    except Exception as e:
        print_error(f"CloneVectorStore test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Pinecone connection test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_pinecone.py                         # Uses youtopia-dev (default)
  python scripts/test_pinecone.py --index youtopia-prod   # Test production index
  
Note: Environment variable PINECONE_INDEX_NAME takes precedence if set.
        """
    )
    
    parser.add_argument(
        '--index',
        default='youtopia-dev',
        help='Pinecone index name to test (default: youtopia-dev)'
    )
    
    return parser.parse_args()


def main():
    """Run all Pinecone connection tests"""
    # Default to development environment if not set (safety)
    if not os.getenv("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "development"
    
    # Parse arguments
    args = parse_args()
    
    # Override index name if not set in environment
    original_index_name = settings.pinecone_index_name
    if 'PINECONE_INDEX_NAME' not in os.environ:
        # Temporarily override the index name
        settings.pinecone_index_name = args.index
        print_info(f"Using index: {args.index} (default for dev testing)")
    else:
        print_info(f"Using index from environment: {settings.pinecone_index_name}")
    
    # Log environment for safety
    env = os.getenv("ENVIRONMENT", "development")
    print_info(f"Environment: {env}")
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Pinecone Connection Test Suite                       ║")
    print("║     Tests: Settings, Embeddings, Connection, Index,      ║")
    print("║            Store, Operations, Namespaces, Multi-Tenant   ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    results = {}
    
    # Test 1: Settings
    results['settings'] = test_settings()
    if not results['settings']:
        print_error("\n❌ Settings test failed. Please check your .env.local file.")
        return 1
    
    # Test 2: Embedding Service
    results['embeddings'], dimension = test_embedding_service()
    if not results['embeddings'] or dimension is None:
        print_error("\n❌ Embedding service test failed.")
        return 1
    
    # Test 3: Pinecone Connection
    results['connection'], pc = test_pinecone_connection()
    if not results['connection'] or pc is None:
        print_error("\n❌ Pinecone connection test failed.")
        return 1
    
    # Test 4: Index Creation/Access
    results['index'], index = test_index_creation(pc, dimension)
    if not results['index'] or index is None:
        print_error("\n❌ Index creation/access test failed.")
        return 1
    
    # Test 5: PineconeStore Integration
    results['store'], pinecone_store = test_pinecone_store_integration()
    if not results['store'] or pinecone_store is None:
        print_error("\n❌ PineconeStore integration test failed.")
        return 1
    
    # Test 6: Vector Operations (without namespace - basic test)
    results['operations'] = test_vector_operations(pinecone_store)
    if not results['operations']:
        print_error("\n❌ Vector operations test failed.")
        return 1
    
    # Test 7: Vector Operations WITH Namespace
    results['operations_with_namespace'] = test_vector_operations_with_namespace(pinecone_store)
    if not results['operations_with_namespace']:
        print_error("\n❌ Vector operations with namespace test failed.")
        return 1
    
    # Test 8: CloneVectorStore (Production Multi-Tenant Architecture)
    results['clone_vector_store'] = test_clone_vector_store()
    if not results['clone_vector_store']:
        print_error("\n❌ CloneVectorStore test failed.")
        return 1
    
    # Summary
    print_header("Test Summary")
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if passed else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"  {test_name.upper():20} {status}")
    
    if all_passed:
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✓ All Pinecone Tests Passed!                            ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 0
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✗ Some Tests Failed                                    ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


