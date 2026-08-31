"""MinIO client wrapper for Lakehouse storage operations using Boto3."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import yaml
from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Load .env variables into environment if available
load_dotenv()


class MinioLakehouseClient:
    """High-level S3/MinIO client for Lakehouse storage layers (Bronze, Silver, Gold)."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region_name: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        """Initialize the MinIO Lakehouse client.

        Args:
            endpoint_url: MinIO server URL (e.g., http://localhost:9000).
            access_key: MinIO access key / root user.
            secret_key: MinIO secret key / root password.
            region_name: S3 region name.
            config_path: Path to minio_config.yaml (optional).
        """
        self.yaml_config = self._load_yaml_config(config_path)

        # Resolve credentials with priority: Explicit args > Env variables > Config file defaults
        self.endpoint_url = (
            endpoint_url
            or os.getenv("MINIO_ENDPOINT")
            or self._get_nested_config("connection.endpoint_url", "http://localhost:9000")
        )
        self.access_key = (
            access_key
            or os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("MINIO_ROOT_USER")
            or self._get_nested_config("connection.access_key", "minioadmin")
        )
        self.secret_key = (
            secret_key
            or os.getenv("AWS_SECRET_ACCESS_KEY")
            or os.getenv("MINIO_ROOT_PASSWORD")
            or self._get_nested_config("connection.secret_key", "minioadmin")
        )
        self.region_name = (
            region_name
            or os.getenv("AWS_REGION")
            or os.getenv("MINIO_REGION")
            or self._get_nested_config("connection.region_name", "us-east-1")
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

        logger.info(
            "Initialized MinioLakehouseClient connecting to %s (region: %s)",
            self.endpoint_url,
            self.region_name,
        )

    def _load_yaml_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load YAML configuration with environment variable interpolation."""
        path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "configs",
            "minio_config.yaml",
        )
        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Interpolate ${VAR:-default} or ${VAR} syntax
            def env_replacer(match: re.Match) -> str:
                var_expr = match.group(1)
                if ":-" in var_expr:
                    var_name, default_val = var_expr.split(":-", 1)
                else:
                    var_name, default_val = var_expr, ""
                return os.getenv(var_name, default_val)

            interpolated = re.sub(r"\$\{([^}]+)\}", env_replacer, content)
            return yaml.safe_load(interpolated) or {}
        except Exception as e:
            logger.warning("Failed to parse config from %s: %s", path, e)
            return {}

    def _get_nested_config(self, key_path: str, default: Any = None) -> Any:
        """Retrieve nested config value by dot notation."""
        curr = self.yaml_config
        for key in key_path.split("."):
            if isinstance(curr, dict) and key in curr:
                curr = curr[key]
            else:
                return default
        return curr

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                return False
            logger.error("Error checking bucket %s: %s", bucket_name, e)
            raise

    def create_bucket_if_not_exists(self, bucket_name: str) -> bool:
        """Create a bucket if it does not already exist."""
        if not self.bucket_exists(bucket_name):
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
                logger.info("Created MinIO bucket: '%s'", bucket_name)
                return True
            except ClientError as e:
                logger.error("Failed to create bucket '%s': %s", bucket_name, e)
                raise
        return False

    def ensure_lakehouse_buckets(
        self,
        buckets: Optional[List[str]] = None,
    ) -> List[str]:
        """Ensure default Lakehouse buckets (bronze, silver, gold) exist."""
        target_buckets = buckets or [
            os.getenv("MINIO_BUCKET_BRONZE", "bronze"),
            os.getenv("MINIO_BUCKET_SILVER", "silver"),
            os.getenv("MINIO_BUCKET_GOLD", "gold"),
        ]
        created = []
        for bucket in target_buckets:
            if self.create_bucket_if_not_exists(bucket):
                created.append(bucket)
        return created

    def upload_file(
        self,
        local_path: str,
        bucket_name: str,
        object_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload a local file to MinIO object storage.

        Args:
            local_path: Path to the local file.
            bucket_name: Target bucket.
            object_name: S3 key/path. Defaults to the filename.
            metadata: Optional metadata dictionary to attach to S3 object.

        Returns:
            The S3 URI path (s3://bucket/object).
        """
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        target_key = object_name or path.name
        self.create_bucket_if_not_exists(bucket_name)

        extra_args: Dict[str, Any] = {}
        if metadata:
            extra_args["Metadata"] = metadata

        logger.info(
            "Uploading '%s' (%d bytes) to MinIO 's3://%s/%s'",
            path.name,
            path.stat().st_size,
            bucket_name,
            target_key,
        )

        self.s3_client.upload_file(
            Filename=str(path),
            Bucket=bucket_name,
            Key=target_key,
            ExtraArgs=extra_args if extra_args else None,
        )

        s3_uri = f"s3://{bucket_name}/{target_key}"
        logger.info("Successfully uploaded '%s' -> %s", path.name, s3_uri)
        return s3_uri

    def upload_bytes(
        self,
        data: bytes,
        bucket_name: str,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload in-memory bytes directly to MinIO object storage."""
        self.create_bucket_if_not_exists(bucket_name)

        put_kwargs: Dict[str, Any] = {
            "Bucket": bucket_name,
            "Key": object_name,
            "Body": data,
            "ContentType": content_type,
        }
        if metadata:
            put_kwargs["Metadata"] = metadata

        self.s3_client.put_object(**put_kwargs)
        s3_uri = f"s3://{bucket_name}/{object_name}"
        logger.info("Uploaded %d bytes to %s", len(data), s3_uri)
        return s3_uri

    def list_objects(self, bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in a bucket under a prefix."""
        if not self.bucket_exists(bucket_name):
            return []

        paginator = self.s3_client.get_paginator("list_objects_v2")
        results = []

        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for item in page.get("Contents", []):
                results.append(
                    {
                        "key": item["Key"],
                        "size": item["Size"],
                        "last_modified": item["LastModified"].isoformat(),
                        "etag": item.get("ETag", "").strip('"'),
                    }
                )
        return results

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if a specific object exists in a bucket."""
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=object_name)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise
