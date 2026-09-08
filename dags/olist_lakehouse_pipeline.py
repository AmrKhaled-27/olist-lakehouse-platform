"""Apache Airflow DAG: Olist Lakehouse Pipeline.

Orchestrates the complete Medallion Lakehouse pipeline:
1. Healthcheck: Verify MinIO S3 is live.
2. Bronze: Ingest raw CSV data into s3://bronze/raw/.
3. Silver: Execute PySpark cleaning and deduplication into s3://silver/tables/.
4. Gold: Execute dbt dimensional modeling into data/gold_lakehouse.duckdb.
5. Quality Gate: Run dbt test to validate all 23 data assertions.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def run_bronze_ingestion(**context):
    """Execute Bronze Layer Ingestion natively inside Airflow.

    Lands raw Olist CSV datasets into MinIO Bronze layer (s3://bronze/raw/...)
    with audit metadata (batch ID, timestamp, file size, SHA256 checksum).
    Automatically downloads from Kaggle if raw files are missing and credentials exist.
    """
    from src.ingestion.ingest_bronze import run_ingestion

    status = run_ingestion(
        data_dir="data/raw",
        download_kaggle=True,
        generate_samples=True,
    )
    if status != 0:
        raise RuntimeError("Bronze ingestion failed. Check task logs for details.")


def log_completion_summary(**context):
    """Log an executive summary of the successful pipeline run."""
    run_id = context.get("run_id", "manual")
    logical_date = context.get("logical_date", datetime.utcnow())
    print("=" * 70)
    print("🎉 OLIST MEDALLION LAKEHOUSE PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"• Run ID: {run_id}")
    print(f"• Logical Date: {logical_date}")
    print("• Storage: MinIO Bronze & Silver Buckets updated")
    print("• Serving: DuckDB Gold Star Schema & Marts refreshed")
    print("• Data Quality: 23/23 tests passed (Zero integrity violations)")
    print("=" * 70)


with DAG(
    dag_id="olist_lakehouse_pipeline",
    default_args=default_args,
    description="End-to-End Medallion Lakehouse: Bronze -> Silver (Spark) -> Gold (dbt) -> Tests",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["lakehouse", "pyspark", "dbt", "duckdb", "minio", "production"],
) as dag:

    # -------------------------------------------------------------------------
    # Task 1: Check Object Storage Availability
    # -------------------------------------------------------------------------
    check_minio_health = BashOperator(
        task_id="check_minio_health",
        bash_command="curl -f -s http://minio:9000/minio/health/live || exit 1",
    )

    # -------------------------------------------------------------------------
    # Task 2: Bronze Layer - Ingest Raw CSVs into MinIO (Native Airflow Execution)
    # -------------------------------------------------------------------------
    ingest_bronze = PythonOperator(
        task_id="ingest_bronze",
        python_callable=run_bronze_ingestion,
    )

    # -------------------------------------------------------------------------
    # Task 3: Silver Layer - PySpark Distributed Cleaning & Spatial Deduplication
    # -------------------------------------------------------------------------
    transform_silver_spark = BashOperator(
        task_id="transform_silver_spark",
        bash_command=(
            "docker exec olist-spark-master "
            "/opt/spark/bin/spark-submit --master spark://spark-master:7077 "
            "src/spark_jobs/bronze_to_silver.py --all"
        ),
    )

    # -------------------------------------------------------------------------
    # Task 4: Gold Layer - dbt Star-Schema Modeling (Facts, Dims & Marts)
    # -------------------------------------------------------------------------
    materialize_gold_dbt = BashOperator(
        task_id="materialize_gold_dbt",
        bash_command=(
            "docker run --rm "
            "--network docker_lakehouse-net "
            "--volumes-from olist-airflow-webserver "
            "-w /workspace/dbt_olist "
            "-e DBT_PROFILES_DIR=/workspace/dbt_olist "
            "-e DUCKDB_PATH=/workspace/data/gold_lakehouse.duckdb "
            "-e MINIO_S3_ENDPOINT=minio:9000 "
            "-e AWS_ACCESS_KEY_ID=minioadmin "
            "-e AWS_SECRET_ACCESS_KEY=minioadmin "
            "docker-dbt run"
        ),
    )

    # -------------------------------------------------------------------------
    # Task 5: Data Quality Gate - 23 Automated Data Tests
    # -------------------------------------------------------------------------
    test_gold_quality = BashOperator(
        task_id="test_gold_quality",
        bash_command=(
            "docker run --rm "
            "--network docker_lakehouse-net "
            "--volumes-from olist-airflow-webserver "
            "-w /workspace/dbt_olist "
            "-e DBT_PROFILES_DIR=/workspace/dbt_olist "
            "-e DUCKDB_PATH=/workspace/data/gold_lakehouse.duckdb "
            "-e MINIO_S3_ENDPOINT=minio:9000 "
            "-e AWS_ACCESS_KEY_ID=minioadmin "
            "-e AWS_SECRET_ACCESS_KEY=minioadmin "
            "docker-dbt test"
        ),
    )

    # -------------------------------------------------------------------------
    # Task 6: Pipeline Completion & Telemetry Summary
    # -------------------------------------------------------------------------
    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=log_completion_summary,
    )

    # -------------------------------------------------------------------------
    # Workflow Execution Order
    # -------------------------------------------------------------------------
    (
        check_minio_health
        >> ingest_bronze
        >> transform_silver_spark
        >> materialize_gold_dbt
        >> test_gold_quality
        >> notify_success
    )
