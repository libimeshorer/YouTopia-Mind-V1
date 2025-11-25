"""AWS utilities for S3 and Secrets Manager"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import json
from pathlib import Path

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """S3 client wrapper for document storage"""
    
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    
    def upload_file(self, file_path: str, s3_key: str) -> bool:
        """Upload a file to S3"""
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            logger.info("File uploaded to S3", s3_key=s3_key, bucket=self.bucket_name)
            return True
        except ClientError as e:
            logger.error("Error uploading file to S3", error=str(e), s3_key=s3_key)
            return False
    
    def upload_fileobj(self, file_obj: BinaryIO, s3_key: str) -> bool:
        """Upload a file-like object to S3"""
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, s3_key)
            logger.info("File object uploaded to S3", s3_key=s3_key, bucket=self.bucket_name)
            return True
        except ClientError as e:
            logger.error("Error uploading file object to S3", error=str(e), s3_key=s3_key)
            return False
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info("File downloaded from S3", s3_key=s3_key, local_path=local_path)
            return True
        except ClientError as e:
            logger.error("Error downloading file from S3", error=str(e), s3_key=s3_key)
            return False
    
    def get_object(self, s3_key: str) -> Optional[bytes]:
        """Get an object from S3 as bytes"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read()
        except ClientError as e:
            logger.error("Error getting object from S3", error=str(e), s3_key=s3_key)
            return None
    
    def put_object(self, s3_key: str, content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Put an object to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
            )
            logger.info("Object put to S3", s3_key=s3_key, bucket=self.bucket_name)
            return True
        except ClientError as e:
            logger.error("Error putting object to S3", error=str(e), s3_key=s3_key)
            return False
    
    def list_objects(self, prefix: str = "") -> list[str]:
        """List objects in S3 with given prefix"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except ClientError as e:
            logger.error("Error listing objects in S3", error=str(e), prefix=prefix)
            return []
    
    def delete_object(self, s3_key: str) -> bool:
        """Delete an object from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info("Object deleted from S3", s3_key=s3_key, bucket=self.bucket_name)
            return True
        except ClientError as e:
            logger.error("Error deleting object from S3", error=str(e), s3_key=s3_key)
            return False


def save_personality_profile_to_s3(profile: dict, s3_key: str = "profiles/personality_profile.json") -> bool:
    """Save personality profile to S3"""
    s3_client = S3Client()
    content = json.dumps(profile, indent=2).encode("utf-8")
    return s3_client.put_object(s3_key, content, content_type="application/json")


def load_personality_profile_from_s3(s3_key: str = "profiles/personality_profile.json") -> Optional[dict]:
    """Load personality profile from S3"""
    s3_client = S3Client()
    content = s3_client.get_object(s3_key)
    if content:
        return json.loads(content.decode("utf-8"))
    return None


