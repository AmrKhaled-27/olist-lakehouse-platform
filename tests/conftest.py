"""PyTest shared fixtures for Olist Lakehouse Platform."""

import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test CSV dataset files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set default test environment variables."""
    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET_BRONZE", "test-bronze")
    monkeypatch.setenv("MINIO_BUCKET_SILVER", "test-silver")
    monkeypatch.setenv("MINIO_BUCKET_GOLD", "test-gold")
