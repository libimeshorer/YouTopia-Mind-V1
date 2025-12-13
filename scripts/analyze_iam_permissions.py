#!/usr/bin/env python3
"""
IAM Permissions Analyzer

This script helps you analyze what S3 permissions your IAM users have
and identifies what's missing.
"""

import sys
import os
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def test_permission(s3_client, bucket_name, action_description, test_func):
    """Test a specific permission"""
    try:
        result = test_func()
        print(f"✅ {action_description}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDenied':
            print(f"❌ {action_description}")
            print(f"   Missing permission: {e.response.get('Error', {}).get('Message', 'Unknown')}")
        else:
            print(f"⚠️  {action_description}")
            print(f"   Error: {error_code}")
        return False
    except Exception as e:
        print(f"⚠️  {action_description}")
        print(f"   Unexpected error: {str(e)}")
        return False


def analyze_permissions(env_file, env_name):
    """Analyze permissions for a specific environment"""
    print(f"\n{'='*70}")
    print(f"Analyzing {env_name.upper()} Environment Permissions")
    print(f"{'='*70}")
    
    # Clear existing env vars
    for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']:
        os.environ.pop(key, None)
    
    # Load the specific env file
    load_dotenv(env_file)
    
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    # Get bucket name
    if env_name == 'dev':
        bucket_name = os.getenv('S3_BUCKET_NAME_DEV') or os.getenv('S3_BUCKET_NAME')
    else:
        bucket_name = os.getenv('S3_BUCKET_NAME_PROD') or os.getenv('S3_BUCKET_NAME')
    
    if not access_key or not secret_key:
        print(f"❌ Could not load credentials from {env_file}")
        return
    
    print(f"\n📋 Configuration:")
    print(f"   Bucket: {bucket_name}")
    print(f"   Region: {region}")
    print(f"   Access Key: {access_key[:10]}...")
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    
    print(f"\n🔍 Testing Permissions:\n")
    
    results = {}
    
    # Test 1: List all buckets
    results['ListAllMyBuckets'] = test_permission(
        s3_client,
        bucket_name,
        "s3:ListAllMyBuckets - List all S3 buckets",
        lambda: s3_client.list_buckets()
    )
    
    # Test 2: Get bucket location
    results['GetBucketLocation'] = test_permission(
        s3_client,
        bucket_name,
        f"s3:GetBucketLocation - Get location of bucket '{bucket_name}'",
        lambda: s3_client.get_bucket_location(Bucket=bucket_name)
    )
    
    # Test 3: List objects in bucket
    results['ListBucket'] = test_permission(
        s3_client,
        bucket_name,
        f"s3:ListBucket - List objects in bucket '{bucket_name}'",
        lambda: s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
    )
    
    # Test 4: Put object
    test_key = f"__permission_test__/{os.urandom(8).hex()}.txt"
    results['PutObject'] = test_permission(
        s3_client,
        bucket_name,
        f"s3:PutObject - Upload test file to '{bucket_name}'",
        lambda: s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=b"test"
        )
    )
    
    # Test 5: Get object (only if put succeeded)
    if results['PutObject']:
        results['GetObject'] = test_permission(
            s3_client,
            bucket_name,
            f"s3:GetObject - Download test file from '{bucket_name}'",
            lambda: s3_client.get_object(Bucket=bucket_name, Key=test_key)
        )
        
        # Test 6: Delete object (cleanup)
        if results['GetObject']:
            results['DeleteObject'] = test_permission(
                s3_client,
                bucket_name,
                f"s3:DeleteObject - Delete test file from '{bucket_name}'",
                lambda: s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            )
        else:
            results['DeleteObject'] = False
    else:
        results['GetObject'] = False
        results['DeleteObject'] = False
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Permission Summary for {env_name.upper()}")
    print(f"{'='*70}")
    
    required_permissions = {
        'ListBucket': 'Required for application',
        'PutObject': 'Required for application',
        'GetObject': 'Required for application',
        'DeleteObject': 'Required for application',
        'GetBucketLocation': 'Required for tests',
        'ListAllMyBuckets': 'Required for tests'
    }
    
    for perm, status in results.items():
        status_icon = "✅" if status else "❌"
        purpose = required_permissions.get(perm, 'Unknown')
        print(f"{status_icon} {perm:20} - {purpose}")
    
    # Check if all required permissions are present
    critical_perms = ['ListBucket', 'PutObject', 'GetObject', 'DeleteObject']
    critical_ok = all(results.get(perm, False) for perm in critical_perms)
    
    if critical_ok:
        print(f"\n✅ All critical permissions are present! Your application should work.")
    else:
        print(f"\n❌ Missing critical permissions! Your application may not work correctly.")
        print(f"\n📝 Next Steps:")
        print(f"   1. Review the IAM policy for this user in AWS Console")
        print(f"   2. Add the missing permissions (see docs/AWS_IAM_SETUP.md)")
        print(f"   3. Wait 10-30 seconds for changes to propagate")
        print(f"   4. Run this script again to verify")
    
    return results


def main():
    """Main function"""
    print("🔍 AWS IAM Permissions Analyzer")
    print("="*70)
    print("\nThis script will test what S3 permissions your IAM users have.")
    print("It will help identify missing permissions.\n")
    
    # Analyze both environments
    dev_results = analyze_permissions('.dev.env', 'dev')
    prod_results = analyze_permissions('.prod.env', 'prod')
    
    print(f"\n{'='*70}")
    print("Analysis Complete!")
    print(f"{'='*70}")
    print("\n💡 Tip: If permissions are missing, see docs/AWS_IAM_SETUP.md")
    print("   for step-by-step instructions on fixing IAM policies.\n")


if __name__ == "__main__":
    main()
