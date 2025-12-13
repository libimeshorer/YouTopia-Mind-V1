import boto3
import os
from dotenv import load_dotenv

def test_s3_connection(env_file, env_name):
    """Test S3 connection for a specific environment"""
    print(f"\n{'='*60}")
    print(f"Testing {env_name.upper()} Environment")
    print(f"{'='*60}")
    
    # Clear existing env vars to avoid conflicts
    for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']:
        os.environ.pop(key, None)
    
    # Load the specific env file
    load_dotenv(env_file)
    
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    region = os.getenv('AWS_REGION')
    # Try to get bucket name - check for environment-specific variable first
    if env_name == 'dev':
        bucket_name = os.getenv('S3_BUCKET_NAME_DEV') or os.getenv('S3_BUCKET_NAME')
    else:  # prod
        bucket_name = os.getenv('S3_BUCKET_NAME_PROD') or os.getenv('S3_BUCKET_NAME')
    
    # Check if credentials are loaded
    if not access_key:
        print(f"❌ ERROR: Could not load credentials from {env_file}")
        print(f"   Make sure the file exists and has AWS_ACCESS_KEY_ID")
        return False
    
    print(f"✓ Loaded credentials from: {env_file}")
    print(f"✓ Access Key ID: {access_key[:10]}..." if access_key else "❌ Missing Access Key")
    print(f"✓ Region: {region}")
    print(f"✓ Bucket Name: {bucket_name}")
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=region
        )
        
        # Test 1: List all buckets
        print(f"\n📦 Listing all S3 buckets...")
        response = s3.list_buckets()
        all_buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"   Found {len(all_buckets)} bucket(s): {all_buckets}")
        
        # Test 2: Check if target bucket exists
        if bucket_name in all_buckets:
            print(f"✅ Target bucket '{bucket_name}' EXISTS")
        else:
            print(f"⚠️  WARNING: Target bucket '{bucket_name}' NOT FOUND")
            print(f"   Available buckets: {all_buckets}")
        
        # Test 3: Try to list objects in the bucket (even if empty)
        try:
            print(f"\n📂 Testing access to '{bucket_name}'...")
            objects_response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
            
            if 'Contents' in objects_response:
                num_objects = len(objects_response['Contents'])
                print(f"✅ Successfully accessed bucket - found {num_objects} object(s)")
                for obj in objects_response['Contents'][:3]:  # Show first 3 objects
                    print(f"   - {obj['Key']}")
            else:
                print(f"✅ Successfully accessed bucket - it's empty (no objects yet)")
                
        except Exception as e:
            print(f"❌ ERROR accessing bucket: {str(e)}")
            return False
        
        print(f"\n✅ {env_name.upper()} S3 CONNECTION SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"\n❌ {env_name.upper()} CONNECTION FAILED!")
        print(f"   Error: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    print("🚀 You.topia S3 Connection Test")
    print("="*60)
    
    # Test dev environment
    dev_success = test_s3_connection('.dev.env', 'dev')
    
    # Test prod environment
    prod_success = test_s3_connection('.prod.env', 'prod')
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"DEV:  {'✅ Connected' if dev_success else '❌ Failed'}")
    print(f"PROD: {'✅ Connected' if prod_success else '❌ Failed'}")
    print(f"{'='*60}\n")
    
    if dev_success and prod_success:
        print("🎉 All connections successful! You're ready to use S3.")
    else:
        print("⚠️  Some connections failed. Check the errors above.")


# ## Expected Output (Success):
#
# 🚀 You.topia S3 Connection Test
# ============================================================

# ============================================================
# Testing DEV Environment
# ============================================================
# ✓ Loaded credentials from: .dev.env
# ✓ Access Key ID: AKIAIOSFO...
# ✓ Region: us-east-1
# ✓ Bucket Name: youtopia-s3-dev

# 📦 Listing all S3 buckets...
#    Found 2 bucket(s): ['youtopia-s3-dev', 'youtopia-s3-prod']
# ✅ Target bucket 'youtopia-s3-dev' EXISTS

# 📂 Testing access to 'youtopia-s3-dev'...
# ✅ Successfully accessed bucket - it's empty (no objects yet)

# ✅ DEV S3 CONNECTION SUCCESSFUL!

# ============================================================
# Testing PROD Environment
# ============================================================
# ✓ Loaded credentials from: .prod.env
# ✓ Access Key ID: AKIAZXCVB...
# ✓ Region: us-east-1
# ✓ Bucket Name: youtopia-s3-prod

# 📦 Listing all S3 buckets...
#    Found 2 bucket(s): ['youtopia-s3-dev', 'youtopia-s3-prod']
# ✅ Target bucket 'youtopia-s3-prod' EXISTS

# 📂 Testing access to 'youtopia-s3-prod'...
# ✅ Successfully accessed bucket - it's empty (no objects yet)

# ✅ PROD S3 CONNECTION SUCCESSFUL!

# ============================================================
# SUMMARY
# ============================================================
# DEV:  ✅ Connected
# PROD: ✅ Connected
# ============================================================

# 🎉 All connections successful! You're ready to use S3.
