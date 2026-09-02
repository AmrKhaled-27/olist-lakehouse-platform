"""PyTest shared fixtures for Olist Lakehouse Platform."""

import os
import sys
import tempfile
from pathlib import Path
import pytest
from pyspark.sql import SparkSession

# Ensure worker processes spawned by PySpark use this exact Python executable
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test CSV dataset files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set default test environment variables."""
    monkeypatch.setenv("PYSPARK_PYTHON", sys.executable)
    monkeypatch.setenv("PYSPARK_DRIVER_PYTHON", sys.executable)
    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET_BRONZE", "test-bronze")
    monkeypatch.setenv("MINIO_BUCKET_SILVER", "test-silver")
    monkeypatch.setenv("MINIO_BUCKET_GOLD", "test-gold")


@pytest.fixture(scope="session")
def spark_session():
    """Create a lightweight local SparkSession for unit testing transformations."""
    java_options = (
        "-Djava.security.manager=allow "
        "--add-opens=java.base/java.lang=ALL-UNNAMED "
        "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
        "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
        "--add-opens=java.base/java.io=ALL-UNNAMED "
        "--add-opens=java.base/java.net=ALL-UNNAMED "
        "--add-opens=java.base/java.nio=ALL-UNNAMED "
        "--add-opens=java.base/java.util=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
        "--add-opens=java.base/javax.security.auth=ALL-UNNAMED"
    )
    spark = (
        SparkSession.builder.appName("Olist-PyTest-Session")
        .master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .config("spark.driver.extraJavaOptions", java_options)
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    yield spark
    spark.stop()
