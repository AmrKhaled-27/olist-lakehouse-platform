"""Unit tests for logger and MinIO client utilities."""

import logging
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from src.utils.logger import get_logger
from src.utils.minio_client import MinioLakehouseClient


def test_get_logger():
    """Verify logger instantiation and level setting."""
    logger = get_logger("test_logger", log_level="DEBUG")
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG


def test_minio_client_init():
    """Verify MinioLakehouseClient initialization parameters."""
    client = MinioLakehouseClient(
        endpoint_url="http://localhost:9000",
        access_key="test_key",
        secret_key="test_secret",
        region_name="us-east-1",
    )
    assert client.endpoint_url == "http://localhost:9000"
    assert client.access_key == "test_key"
    assert client.secret_key == "test_secret"


@patch("boto3.client")
def test_bucket_exists_true(mock_boto_client):
    """Test bucket_exists returns True on successful head_bucket."""
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.head_bucket.return_value = {}

    client = MinioLakehouseClient()
    assert client.bucket_exists("bronze") is True


@patch("boto3.client")
def test_bucket_exists_false(mock_boto_client):
    """Test bucket_exists returns False when 404 is encountered."""
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_s3.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

    client = MinioLakehouseClient()
    assert client.bucket_exists("nonexistent") is False
