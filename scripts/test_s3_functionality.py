#!/usr/bin/env python3
"""
AWS S3 Connection Test Script

Tests S3 bucket access, file upload, download, presigned URLs, and deletion.
Run with: python scripts/test_s3.py
"""

import sys
import os
import uuid
import tempfile
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment before importing settings to ensure correct env file is loaded
# Default to development if not specified (as per user requirement)
if not os.getenv("ENVIRONMENT"):
    os.environ["ENVIRONMENT"] = "development"

from src.utils.aws import S3Client
from src.config.settings import settings
from src.utils.logging import get_logger
import boto3
from botocore.exceptions import ClientError

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
        print_info(f"S3 Bucket Name: {settings.s3_bucket_name}")
        print_info(f"AWS Region: {settings.aws_region}")
        print_info(f"AWS Access Key ID: {'*' * 20}...{settings.aws_access_key_id[-4:] if settings.aws_access_key_id and len(settings.aws_access_key_id) > 4 else '***'}")
        print_info(f"AWS Secret Access Key: {'*' * 20}...{settings.aws_secret_access_key[-4:] if settings.aws_secret_access_key and len(settings.aws_secret_access_key) > 4 else '***'}")
        
        if not settings.s3_bucket_name:
            print_error("S3_BUCKET_NAME is not set!")
            return False
        
        if not settings.aws_access_key_id:
            print_error("AWS_ACCESS_KEY_ID is not set!")
            return False
        
        if not settings.aws_secret_access_key:
            print_error("AWS_SECRET_ACCESS_KEY is not set!")
            return False
        
        print_success("Settings loaded successfully")
        return True
    except Exception as e:
        print_error(f"Failed to load settings: {str(e)}")
        return False


def test_s3_client_initialization():
    """Test 2: Test S3Client initialization"""
    print_header("Test 2: S3Client Initialization")
    
    try:
        s3_client = S3Client()
        print_info(f"Bucket name: {s3_client.bucket_name}")
        print_info(f"Region: {settings.aws_region}")
        
        print_success("S3Client initialized successfully")
        return True, s3_client
    except Exception as e:
        print_error(f"S3Client initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_bucket_access(s3_client: S3Client):
    """Test 3: Test bucket access and existence"""
    print_header("Test 3: Bucket Access")
    
    try:
        # Try to head the bucket to verify access
        s3_resource = boto3.resource(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        
        bucket = s3_resource.Bucket(s3_client.bucket_name)
        
        # Check if bucket exists and is accessible
        print_info(f"Checking access to bucket: {s3_client.bucket_name}")
        bucket.load()
        
        print_info(f"Bucket location: {bucket.meta.client.get_bucket_location(Bucket=s3_client.bucket_name).get('LocationConstraint', 'us-east-1')}")
        print_info(f"Bucket creation date: {bucket.creation_date}")
        
        print_success("Bucket is accessible")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            print_error(f"Bucket '{s3_client.bucket_name}' does not exist!")
        elif error_code == '403':
            print_error(f"Access denied to bucket '{s3_client.bucket_name}'. Check your IAM permissions.")
        else:
            print_error(f"Error accessing bucket: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Bucket access test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_file_upload(s3_client: S3Client):
    """Test 4: Test file upload"""
    print_header("Test 4: File Upload")
    
    test_key = f"test/{uuid.uuid4()}/test_file.txt"
    test_content = b"This is a test file for S3 connection testing.\nGenerated by test_s3.py"
    
    try:
        print_info(f"Uploading test file to: {test_key}")
        print_info(f"File size: {len(test_content)} bytes")
        
        success = s3_client.put_object(test_key, test_content, content_type="text/plain")
        
        if not success:
            print_error("File upload returned False")
            return False, None
        
        print_success("File uploaded successfully")
        return True, test_key
    except Exception as e:
        print_error(f"File upload failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def test_file_download(s3_client: S3Client, test_key: str):
    """Test 5: Test file download"""
    print_header("Test 5: File Download")
    
    try:
        print_info(f"Downloading file from: {test_key}")
        
        content = s3_client.get_object(test_key)
        
        if content is None:
            print_error("File download returned None")
            return False
        
        print_info(f"Downloaded {len(content)} bytes")
        print_info(f"Content preview: {content[:50].decode('utf-8', errors='ignore')}...")
        
        print_success("File downloaded successfully")
        return True
    except Exception as e:
        print_error(f"File download failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_presigned_url(s3_client: S3Client, test_key: str):
    """Test 6: Test presigned URL generation"""
    print_header("Test 6: Presigned URL Generation")
    
    try:
        s3_client_boto = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        
        print_info(f"Generating presigned URL for: {test_key}")
        print_info("Expiry: 1 hour")
        
        url = s3_client_boto.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_client.bucket_name, "Key": test_key},
            ExpiresIn=3600,  # 1 hour
        )
        
        print_info(f"Presigned URL: {url[:80]}...")
        print_success("Presigned URL generated successfully")
        return True
    except Exception as e:
        print_error(f"Presigned URL generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_list_objects(s3_client: S3Client):
    """Test 7: Test listing objects"""
    print_header("Test 7: List Objects")
    
    try:
        print_info("Listing objects with prefix 'test/'...")
        
        objects = s3_client.list_objects(prefix="test/")
        
        print_info(f"Found {len(objects)} object(s) with prefix 'test/'")
        if objects:
            print_info("Sample objects:")
            for obj_key in objects[:5]:
                print(f"  - {obj_key}")
            if len(objects) > 5:
                print_info(f"  ... and {len(objects) - 5} more")
        
        print_success("List objects operation successful")
        return True
    except Exception as e:
        print_error(f"List objects failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_file_deletion(s3_client: S3Client, test_key: str):
    """Test 8: Test file deletion"""
    print_header("Test 8: File Deletion")
    
    try:
        print_info(f"Deleting test file: {test_key}")
        
        success = s3_client.delete_object(test_key)
        
        if not success:
            print_error("File deletion returned False")
            return False
        
        # Verify deletion by trying to get the object
        print_info("Verifying deletion...")
        content = s3_client.get_object(test_key)
        
        if content is not None:
            print_warning("File still exists after deletion (may take time to propagate)")
        else:
            print_success("File deleted successfully")
        
        return True
    except Exception as e:
        print_error(f"File deletion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_upload_fileobj(s3_client: S3Client):
    """Test 9: Test uploading file-like object"""
    print_header("Test 9: Upload File Object")
    
    test_key = f"test/{uuid.uuid4()}/test_fileobj.txt"
    test_content = b"This is a test file object upload.\nGenerated by test_s3.py"
    
    try:
        print_info(f"Uploading file object to: {test_key}")
        
        file_obj = BytesIO(test_content)
        success = s3_client.upload_fileobj(file_obj, test_key)
        
        if not success:
            print_error("File object upload returned False")
            return False, None
        
        # Clean up
        s3_client.delete_object(test_key)
        
        print_success("File object uploaded and cleaned up successfully")
        return True, None
    except Exception as e:
        print_error(f"File object upload failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    """Run all S3 connection tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     AWS S3 Connection Test Suite                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    results = {}
    test_key = None
    
    # Test 1: Settings
    results['settings'] = test_settings()
    if not results['settings']:
        print_error("\n❌ Settings test failed. Please check your .env.local file.")
        print_info("\nRequired environment variables:")
        print_info("  - S3_BUCKET_NAME")
        print_info("  - AWS_ACCESS_KEY_ID")
        print_info("  - AWS_SECRET_ACCESS_KEY")
        print_info("  - AWS_REGION (optional, defaults to us-east-1)")
        return 1
    
    # Test 2: S3Client Initialization
    results['initialization'], s3_client = test_s3_client_initialization()
    if not results['initialization'] or s3_client is None:
        print_error("\n❌ S3Client initialization test failed.")
        return 1
    
    # Test 3: Bucket Access
    results['bucket_access'] = test_bucket_access(s3_client)
    if not results['bucket_access']:
        print_error("\n❌ Bucket access test failed.")
        return 1
    
    # Test 4: File Upload
    results['upload'], test_key = test_file_upload(s3_client)
    if not results['upload'] or test_key is None:
        print_error("\n❌ File upload test failed.")
        return 1
    
    # Test 5: File Download
    results['download'] = test_file_download(s3_client, test_key)
    if not results['download']:
        print_error("\n❌ File download test failed.")
        # Continue to cleanup
    
    # Test 6: Presigned URL
    results['presigned_url'] = test_presigned_url(s3_client, test_key)
    if not results['presigned_url']:
        print_warning("\n⚠ Presigned URL test failed (non-critical).")
    
    # Test 7: List Objects
    results['list'] = test_list_objects(s3_client)
    if not results['list']:
        print_warning("\n⚠ List objects test failed (non-critical).")
    
    # Test 8: File Deletion
    results['delete'] = test_file_deletion(s3_client, test_key)
    if not results['delete']:
        print_warning("\n⚠ File deletion test failed (non-critical).")
    
    # Test 9: Upload File Object
    results['upload_fileobj'], _ = test_upload_fileobj(s3_client)
    if not results['upload_fileobj']:
        print_warning("\n⚠ File object upload test failed (non-critical).")
    
    # Summary
    print_header("Test Summary")
    
    critical_tests = ['settings', 'initialization', 'bucket_access', 'upload']
    critical_passed = all(results.get(test, False) for test in critical_tests)
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if passed else f"{Colors.RED}FAILED{Colors.RESET}"
        critical_marker = " (critical)" if test_name in critical_tests else ""
        print(f"  {test_name.upper():20} {status}{critical_marker}")
    
    if critical_passed:
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✓ All Critical S3 Tests Passed!                       ║")
        print("║     Your S3 bucket is ready to use!                        ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 0
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     ✗ Critical Tests Failed                               ║")
        print("║     Please check your S3 configuration                    ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(Colors.RESET)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
