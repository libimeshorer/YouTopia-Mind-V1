#!/usr/bin/env python3
"""
Production-Safe Pinecone Health Check

This script safely tests the production Pinecone index WITHOUT touching customer data.
It uses a dedicated test namespace that is completely isolated from customer namespaces.

SAFETY GUARANTEES:
1. Uses namespace "system-health-check" - will never match customer pattern
2. All operations are scoped to test namespace only
3. Cleans up all test data automatically
4. Read-only for customer data (only checks stats)

Usage:
  python scripts/test_pinecone_prod_safe.py                    # Uses current settings
  python scripts/test_pinecone_prod_safe.py --index youtopia-prod  # Explicit index
  
Environment:
  PINECONE_INDEX_NAME: Override via environment variable (takes precedence)
"""

import sys
import os
import time
import argparse
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pinecone_store import PineconeStore
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


# SAFETY: Test namespace that will never match customer namespace pattern
# Customer namespaces: "{tenant_uuid}_{clone_uuid}" (64 chars, all hex)
# Test namespace: human-readable, clearly a system test
TEST_NAMESPACE = "system-health-check-test"


def verify_environment():
    """Verify we're configured for the intended environment"""
    print_header("Environment Verification")
    
    index_name = settings.pinecone_index_name
    environment = settings.environment
    
    print_info(f"Index Name: {index_name}")
    print_info(f"Environment: {environment}")
    
    # Safety check for production
    if "prod" in index_name.lower() or environment.lower() == "production":
        print_warning("⚠️  PRODUCTION ENVIRONMENT DETECTED")
        print_info("This script uses isolated test namespace: {TEST_NAMESPACE}")
        print_info("Customer data namespaces are completely isolated and safe")
        print_info("")
        
        response = input(f"{Colors.YELLOW}Continue with production health check? (yes/no): {Colors.RESET}")
        if response.lower() != "yes":
            print_error("Aborted by user")
            return False
    
    print_success("Environment verified")
    return True


def test_connection_and_stats(store: PineconeStore):
    """Test 1: Connection and get index statistics (READ ONLY)"""
    print_header("Test 1: Connection & Index Statistics (Read-Only)")
    
    try:
        # Get overall index stats (safe, read-only)
        stats = store.index.describe_index_stats()
        
        print_info("Index Statistics:")
        print(f"  - Total vectors: {stats.total_vector_count}")
        print(f"  - Dimension: {stats.dimension}")
        print(f"  - Index fullness: {stats.index_fullness if hasattr(stats, 'index_fullness') else 'N/A'}")
        
        # Show namespace stats if available
        if hasattr(stats, 'namespaces') and stats.namespaces:
            print_info(f"Active namespaces: {len(stats.namespaces)}")
            # Don't list actual namespace names (customer privacy)
            print_info("(Namespace names hidden for customer privacy)")
        
        print_success("Connection and stats check passed")
        return True
        
    except Exception as e:
        print_error(f"Connection test failed: {str(e)}")
        return False


def test_write_read_delete_isolated():
    """Test 2: Write, Read, Delete in isolated test namespace (SAFE)"""
    print_header(f"Test 2: Write/Read/Delete in Isolated Namespace")
    
    print_info(f"Test namespace: '{TEST_NAMESPACE}'")
    print_info("This namespace is completely isolated from customer data")
    print_info("")
    
    try:
        # Initialize store
        store = PineconeStore()
        
        # Test data
        test_texts = [
            "Health check test document one",
            "Health check test document two",
        ]
        test_metadata = [
            {"source": "health_check", "test": True, "timestamp": time.time()},
            {"source": "health_check", "test": True, "timestamp": time.time()},
        ]
        
        # WRITE: Add test vectors to isolated namespace
        print_info("Step 1: Writing test vectors to isolated namespace...")
        vector_ids = store.add_texts(
            texts=test_texts,
            metadatas=test_metadata,
            namespace=TEST_NAMESPACE
        )
        
        if not vector_ids or len(vector_ids) != len(test_texts):
            print_error("Write operation failed")
            return False
        
        print_success(f"Written {len(vector_ids)} test vectors")
        
        # Wait for indexing
        print_info("Waiting for vectors to be indexed (2s)...")
        time.sleep(2)
        
        # READ: Query from isolated namespace
        print_info("Step 2: Reading from isolated namespace...")
        results = store.search(
            "health check test",
            n_results=2,
            namespace=TEST_NAMESPACE
        )
        
        if not results:
            print_error("Read operation failed - no results")
            return False
        
        print_success(f"Read {len(results)} vectors from isolated namespace")
        
        # Verify isolation: Query a different namespace (should return nothing)
        print_info("Step 3: Verifying namespace isolation...")
        other_results = store.search(
            "health check test",
            n_results=10,
            namespace="different-test-namespace-456"
        )
        
        if len(other_results) == 0:
            print_success("✓ Namespace isolation verified (other namespace has no test data)")
        else:
            print_warning(f"Found {len(other_results)} results in different namespace (unexpected)")
        
        # DELETE: Clean up test data from isolated namespace
        print_info("Step 4: Cleaning up test data from isolated namespace...")
        delete_success = store.delete(
            ids=vector_ids,
            namespace=TEST_NAMESPACE
        )
        
        if not delete_success:
            print_error("Delete operation failed")
            return False
        
        print_success(f"Deleted {len(vector_ids)} test vectors")
        
        # Verify cleanup
        time.sleep(1)
        verify_results = store.search(
            "health check test",
            n_results=10,
            namespace=TEST_NAMESPACE
        )
        
        if len(verify_results) == 0:
            print_success("✓ Cleanup verified (test namespace is empty)")
        else:
            print_warning(f"Still found {len(verify_results)} vectors (may take time to propagate)")
        
        return True
        
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_config_parity():
    """Test 3: Verify configuration matches expected production settings"""
    print_header("Test 3: Configuration Validation")
    
    try:
        # Verify expected production settings
        checks = {
            "pinecone_api_key": settings.pinecone_api_key is not None and len(settings.pinecone_api_key) > 0,
            "openai_api_key": settings.openai_api_key is not None and len(settings.openai_api_key) > 0,
            "embedding_model": settings.openai_embedding_model == "text-embedding-3-large",
            "index_name_set": settings.pinecone_index_name is not None and len(settings.pinecone_index_name) > 0,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                print_success(f"{check_name}: OK")
            else:
                print_error(f"{check_name}: FAILED")
                all_passed = False
        
        # Verify index dimension matches embedding model
        store = PineconeStore()
        expected_dim = 3072  # text-embedding-3-large
        stats = store.index.describe_index_stats()
        
        if stats.dimension == expected_dim:
            print_success(f"Index dimension ({stats.dimension}) matches embedding model")
        else:
            print_error(f"Index dimension ({stats.dimension}) doesn't match expected ({expected_dim})")
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_error(f"Config validation failed: {str(e)}")
        return False


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Production-safe Pinecone health check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_pinecone_prod_safe.py                    # Uses current settings
  python scripts/test_pinecone_prod_safe.py --index youtopia-prod  # Explicit index
  
Safety: All operations use isolated test namespace - zero customer impact
        """
    )
    
    parser.add_argument(
        '--index',
        help='Pinecone index name to test (default: uses current settings)'
    )
    
    return parser.parse_args()


def main():
    """Run production-safe health checks"""
    # Parse arguments
    args = parse_args()
    
    # Override index name if provided and not set in environment
    if args.index and 'PINECONE_INDEX_NAME' not in os.environ:
        settings.pinecone_index_name = args.index
        print_info(f"Using index: {args.index} (from command line)")
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Pinecone Production Health Check (SAFE)              ║")
    print("║     Uses isolated test namespace - No customer impact    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    # Verify environment and get user confirmation for prod
    if not verify_environment():
        return 1
    
    results = {}
    
    # Initialize store (for stats)
    try:
        store = PineconeStore()
    except Exception as e:
        print_error(f"Failed to initialize PineconeStore: {str(e)}")
        return 1
    
    # Test 1: Connection and Stats (Read-Only)
    results['connection'] = test_connection_and_stats(store)
    if not results['connection']:
        print_error("\n❌ Connection test failed")
        return 1
    
    # Test 2: Write/Read/Delete in Isolated Namespace
    results['operations'] = test_write_read_delete_isolated()
    if not results['operations']:
        print_error("\n❌ Operations test failed")
        return 1
    
    # Test 3: Config Validation
    results['config'] = test_config_parity()
    if not results['config']:
        print_warning("\n⚠️  Config validation failed")
        # Don't fail on config issues, just warn
    
    # Summary
    print_header("Health Check Summary")
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if passed else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"  {test_name.upper():20} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✓ All Health Checks Passed!                           ║")
        print("║     Production index is healthy                           ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 0
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✗ Some Health Checks Failed                           ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
