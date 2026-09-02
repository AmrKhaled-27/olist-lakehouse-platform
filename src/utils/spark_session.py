import os
import re
import sys
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pyspark.sql import SparkSession

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Ensure Spark workers use the exact Python executable running the driver
os.environ["PYSPARK_PYTHON"] = os.environ.get("PYSPARK_PYTHON", sys.executable)
os.environ["PYSPARK_DRIVER_PYTHON"] = os.environ.get("PYSPARK_DRIVER_PYTHON", sys.executable)

_spark_instance: Optional[SparkSession] = None


def load_spark_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load Spark configuration YAML with environment variable interpolation."""
    path = config_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "configs",
        "spark_config.yaml",
    )
    if not os.path.exists(path):
        logger.warning("Spark config file not found at '%s'. Using defaults.", path)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

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
        logger.error("Failed to parse spark_config.yaml: %s", e)
        return {}


def is_running_in_docker() -> bool:
    """Detect whether current process is running inside a Docker container."""
    return (
        os.path.exists("/.dockerenv")
        or os.environ.get("RUNNING_IN_DOCKER", "false").lower() == "true"
    )


def get_spark_session(
    app_name: Optional[str] = None,
    master: Optional[str] = None,
    config_path: Optional[str] = None,
    extra_configs: Optional[Dict[str, str]] = None,
    force_new: bool = False,
) -> SparkSession:
    """Create or return a singleton SparkSession configured for MinIO S3A storage.

    Args:
        app_name: Custom application name (overrides YAML config).
        master: Spark master URL (overrides YAML config).
        config_path: Path to custom spark_config.yaml.
        extra_configs: Dictionary of additional Spark configuration options.
        force_new: If True, stop any existing session and build a new one.

    Returns:
        Configured PySpark SparkSession instance.
    """
    global _spark_instance

    if _spark_instance is not None and not force_new:
        return _spark_instance

    if force_new and _spark_instance is not None:
        _spark_instance.stop()
        _spark_instance = None

    spark_cfg = load_spark_config(config_path)

    # Determine app name & master URL
    final_app_name = (
        app_name or spark_cfg.get("app", {}).get("name") or "Olist-Lakehouse-Processing"
    )
    final_master = (
        master
        or os.getenv("SPARK_MASTER_URL")
        or spark_cfg.get("app", {}).get("master")
        or "local[*]"
    )

    logger.info("Initializing SparkSession '%s' with master '%s'...", final_app_name, final_master)

    builder = SparkSession.builder.appName(final_app_name).master(final_master)
    builder = builder.config("spark.pyspark.python", sys.executable)
    builder = builder.config("spark.pyspark.driver.python", sys.executable)

    # Memory & Resource configs
    driver_mem = os.getenv("SPARK_DRIVER_MEMORY") or spark_cfg.get("resources", {}).get(
        "driver_memory", "2g"
    )
    executor_mem = os.getenv("SPARK_EXECUTOR_MEMORY") or spark_cfg.get("resources", {}).get(
        "executor_memory", "2g"
    )
    builder = builder.config("spark.driver.memory", driver_mem)
    builder = builder.config("spark.executor.memory", executor_mem)

    # Resolve MinIO S3A endpoint (localhost when running on Windows host, minio when in Docker)
    if is_running_in_docker():
        default_endpoint = os.getenv("MINIO_INTERNAL_ENDPOINT", "http://minio:9000")
    else:
        default_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")

    s3a_endpoint = spark_cfg.get("s3a", {}).get("fs.s3a.endpoint", default_endpoint)
    # Ensure proper endpoint string format
    if "${" in str(s3a_endpoint) or not s3a_endpoint:
        s3a_endpoint = default_endpoint

    access_key = (
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("MINIO_ROOT_USER")
        or spark_cfg.get("s3a", {}).get("fs.s3a.access.key", "minioadmin")
    )
    secret_key = (
        os.getenv("AWS_SECRET_ACCESS_KEY")
        or os.getenv("MINIO_ROOT_PASSWORD")
        or spark_cfg.get("s3a", {}).get("fs.s3a.secret.key", "minioadmin")
    )

    # Inject S3A MinIO Filesystem properties
    s3a_properties = {
        "spark.hadoop.fs.s3a.endpoint": s3a_endpoint,
        "spark.hadoop.fs.s3a.access.key": access_key,
        "spark.hadoop.fs.s3a.secret.key": secret_key,
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        "spark.hadoop.fs.s3a.fast.upload": "true",
        "spark.hadoop.fs.s3a.aws.credentials.provider": (
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
        ),
    }

    for key, val in s3a_properties.items():
        builder = builder.config(key, val)

    # Include Maven packages for hadoop-aws when running in local standalone Python mode
    # (Inside our Docker image, these JARs are already in /opt/spark/jars/)
    if not is_running_in_docker():
        builder = builder.config(
            "spark.jars.packages",
            "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262",
        )

    # Inject SQL and performance settings
    sql_settings = spark_cfg.get("sql", {})
    for key, val in sql_settings.items():
        builder = builder.config(key, str(val))

    # JVM options for modern Java 23 module access (only needed when running locally on Windows host)
    if not is_running_in_docker():
        jvm_extra_opts = (
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
        builder = builder.config("spark.driver.extraJavaOptions", jvm_extra_opts)
        builder = builder.config("spark.executor.extraJavaOptions", jvm_extra_opts)

    # Always ensure Snappy compression and UTC timezone
    builder = builder.config("spark.sql.session.timeZone", "UTC")
    builder = builder.config("spark.sql.parquet.compression.codec", "snappy")
    builder = builder.config("spark.sql.sources.partitionOverwriteMode", "dynamic")

    # Apply any custom caller-provided extra configs
    if extra_configs:
        for k, v in extra_configs.items():
            builder = builder.config(k, v)

    _spark_instance = builder.getOrCreate()
    logger.info("SparkSession successfully created (Spark version: %s)", _spark_instance.version)
    return _spark_instance
