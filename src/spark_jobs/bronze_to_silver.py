"""Bronze to Silver PySpark Lakehouse Transformation Job.

Reads raw CSV datasets from MinIO Bronze layer (s3a://bronze/raw/...),
applies schema validation, data quality cleaning, feature derivation,
and writes optimized, partitioned Parquet tables into MinIO Silver (s3a://silver/tables/...).
"""

import argparse
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.spark_jobs.schemas import RAW_SCHEMAS
from src.spark_jobs.transformations import (
    clean_customers,
    clean_geolocation,
    clean_order_items,
    clean_orders,
    clean_payments,
    clean_products,
    clean_reviews,
    clean_sellers,
)
from src.utils.logger import get_logger
from src.utils.spark_session import get_spark_session

logger = get_logger(__name__)

# Registry of dataset processing rules
DATASET_TRANSFORMATION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "orders": {
        "raw_path": "s3a://{bronze_bucket}/raw/orders/olist_orders_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/orders",
        "schema": RAW_SCHEMAS["orders"],
        "clean_fn": clean_orders,
        "partition_by": ["purchase_year", "purchase_month"],
    },
    "order_items": {
        "raw_path": "s3a://{bronze_bucket}/raw/order_items/olist_order_items_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/order_items",
        "schema": RAW_SCHEMAS["order_items"],
        "clean_fn": clean_order_items,
        "partition_by": None,
    },
    "customers": {
        "raw_path": "s3a://{bronze_bucket}/raw/customers/olist_customers_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/customers",
        "schema": RAW_SCHEMAS["customers"],
        "clean_fn": clean_customers,
        "partition_by": None,
    },
    "order_payments": {
        "raw_path": "s3a://{bronze_bucket}/raw/order_payments/olist_order_payments_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/order_payments",
        "schema": RAW_SCHEMAS["order_payments"],
        "clean_fn": clean_payments,
        "partition_by": None,
    },
    "order_reviews": {
        "raw_path": "s3a://{bronze_bucket}/raw/order_reviews/olist_order_reviews_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/order_reviews",
        "schema": RAW_SCHEMAS["order_reviews"],
        "clean_fn": clean_reviews,
        "partition_by": None,
    },
    "products": {
        "raw_path": "s3a://{bronze_bucket}/raw/products/olist_products_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/products",
        "schema": RAW_SCHEMAS["products"],
        "clean_fn": clean_products,
        "partition_by": None,
    },
    "sellers": {
        "raw_path": "s3a://{bronze_bucket}/raw/sellers/olist_sellers_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/sellers",
        "schema": RAW_SCHEMAS["sellers"],
        "clean_fn": clean_sellers,
        "partition_by": None,
    },
    "geolocation": {
        "raw_path": "s3a://{bronze_bucket}/raw/geolocation/olist_geolocation_dataset.csv",
        "silver_path": "s3a://{silver_bucket}/tables/geolocation",
        "schema": RAW_SCHEMAS["geolocation"],
        "clean_fn": clean_geolocation,
        "partition_by": ["geolocation_state"],
    },
    "product_category_name_translation": {
        "raw_path": (
            "s3a://{bronze_bucket}/raw/product_category_name_translation/"
            "product_category_name_translation.csv"
        ),
        "silver_path": "s3a://{silver_bucket}/tables/product_category_name_translation",
        "schema": RAW_SCHEMAS["product_category_name_translation"],
        "clean_fn": lambda df: df.withColumn(
            "product_category_name", F.trim("product_category_name")
        ).withColumn("product_category_name_english", F.trim("product_category_name_english")),
        "partition_by": None,
    },
}


class BronzeToSilverJob:
    """Orchestrates Bronze-to-Silver PySpark batch transformations."""

    def __init__(
        self,
        spark: Optional[SparkSession] = None,
        bronze_bucket: Optional[str] = None,
        silver_bucket: Optional[str] = None,
    ):
        """Initialize the Bronze to Silver transformation job."""
        self.spark = spark or get_spark_session()
        self.bronze_bucket = bronze_bucket or os.getenv("MINIO_BUCKET_BRONZE", "bronze")
        self.silver_bucket = silver_bucket or os.getenv("MINIO_BUCKET_SILVER", "silver")

    def process_table(
        self,
        table_name: str,
        batch_id: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Process a single table from Bronze CSV to Silver Parquet.

        Args:
            table_name: Table identifier from registry.
            batch_id: Unique batch execution ID.
            dry_run: If True, inspect schema and rows without writing Parquet.

        Returns:
            Dictionary with processing metrics and status.
        """
        if table_name not in DATASET_TRANSFORMATION_REGISTRY:
            available = list(DATASET_TRANSFORMATION_REGISTRY.keys())
            raise ValueError(f"Unknown table '{table_name}'. Available: {available}")

        config = DATASET_TRANSFORMATION_REGISTRY[table_name]
        raw_uri = config["raw_path"].format(bronze_bucket=self.bronze_bucket)
        silver_uri = config["silver_path"].format(silver_bucket=self.silver_bucket)
        schema = config["schema"]
        clean_fn: Callable[[DataFrame], DataFrame] = config["clean_fn"]
        partition_by: Optional[List[str]] = config["partition_by"]

        start_time = time.time()
        logger.info("----------------------------------------------------------------------")
        logger.info("Processing [%s]: %s -> %s", table_name, raw_uri, silver_uri)

        # 1. Read raw CSV with strict schema
        raw_df = (
            self.spark.read.format("csv")
            .option("header", "true")
            .option("mode", "DROPMALFORMED")
            .schema(schema)
            .load(raw_uri)
        )

        input_rows = raw_df.count()
        logger.info("[%s] Read %d raw rows from Bronze.", table_name, input_rows)

        # 2. Execute table-specific cleaning transformation
        transformed_df = clean_fn(raw_df)

        # 3. Add audit lineage metadata
        current_ts = F.current_timestamp()
        enriched_df = (
            transformed_df.withColumn("_bronze_loaded_at", current_ts)
            .withColumn("_silver_processed_at", current_ts)
            .withColumn("_batch_id", F.lit(batch_id))
        )

        output_rows = enriched_df.count()
        elapsed_sec = round(time.time() - start_time, 2)

        # 4. Write optimized Parquet
        if dry_run:
            logger.info(
                "[DRY-RUN] [%s] Cleaned %d -> %d rows (%.2fs). Would write to %s (partitions: %s)",
                table_name,
                input_rows,
                output_rows,
                elapsed_sec,
                silver_uri,
                partition_by,
            )
        else:
            writer = enriched_df.write.format("parquet").mode("overwrite")

            if partition_by:
                logger.info(
                    "[%s] Writing partitioned by %s to %s...", table_name, partition_by, silver_uri
                )
                writer = writer.partitionBy(*partition_by)
            else:
                # Coalesce small tables to 1 partition to avoid small file fragmentation
                writer = enriched_df.coalesce(1).write.format("parquet").mode("overwrite")

            writer.save(silver_uri)
            logger.info(
                "[%s] Successfully wrote %d Parquet rows to %s in %.2fs",
                table_name,
                output_rows,
                silver_uri,
                elapsed_sec,
            )

        return {
            "table": table_name,
            "input_rows": input_rows,
            "output_rows": output_rows,
            "dropped_rows": input_rows - output_rows,
            "destination": silver_uri,
            "partition_by": partition_by or "None (Coalesced)",
            "duration_sec": elapsed_sec,
            "status": "SUCCESS",
        }

    def process_all(
        self,
        tables: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run Bronze to Silver transformation for all requested tables."""
        target_tables = tables or list(DATASET_TRANSFORMATION_REGISTRY.keys())
        batch_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        batch_id = f"silver_batch_{batch_ts}_{uuid.uuid4().hex[:6]}"

        logger.info("======================================================================")
        logger.info("Starting Bronze -> Silver Transformation Pipeline [Batch: %s]", batch_id)
        logger.info("Tables to process (%d): %s", len(target_tables), target_tables)
        logger.info("======================================================================")

        results: List[Dict[str, Any]] = []

        for table in target_tables:
            try:
                res = self.process_table(table, batch_id=batch_id, dry_run=dry_run)
                results.append(res)
            except Exception as e:
                logger.error("Failed processing table '%s': %s", table, e, exc_info=True)
                results.append(
                    {
                        "table": table,
                        "status": "FAILED",
                        "error": str(e),
                    }
                )

        # Print summary report
        logger.info("======================================================================")
        logger.info("Bronze to Silver Transformation Summary")
        logger.info("======================================================================")
        for r in results:
            if r.get("status") == "SUCCESS":
                logger.info(
                    "  • %-25s | In: %7d | Out: %7d | Drop: %5d | Time: %5.2fs | %s",
                    r["table"],
                    r["input_rows"],
                    r["output_rows"],
                    r["dropped_rows"],
                    r["duration_sec"],
                    r["partition_by"],
                )
            else:
                logger.error("  • %-25s | FAILED: %s", r["table"], r.get("error"))
        logger.info("======================================================================")

        return results


def run_bronze_to_silver(
    tables: Optional[List[str]] = None,
    dry_run: bool = False,
    bronze_bucket: Optional[str] = None,
    silver_bucket: Optional[str] = None,
) -> int:
    """CLI entry point for bronze-to-silver spark execution."""
    job = BronzeToSilverJob(
        bronze_bucket=bronze_bucket,
        silver_bucket=silver_bucket,
    )
    results = job.process_all(tables=tables, dry_run=dry_run)
    failed = [r for r in results if r.get("status") != "SUCCESS"]
    return 0 if not failed else 1


def main():
    """Parse CLI arguments and run Bronze to Silver job."""
    parser = argparse.ArgumentParser(
        description="Transform Bronze CSVs into Silver Parquet tables in MinIO Lakehouse."
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Specific tables to transform (e.g. --tables orders customers)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all 9 Olist tables",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect schemas and calculate metrics without writing Parquet",
    )
    parser.add_argument(
        "--bronze-bucket",
        type=str,
        default=os.getenv("MINIO_BUCKET_BRONZE", "bronze"),
        help="Source Bronze bucket",
    )
    parser.add_argument(
        "--silver-bucket",
        type=str,
        default=os.getenv("MINIO_BUCKET_SILVER", "silver"),
        help="Target Silver bucket",
    )

    args = parser.parse_args()
    target_tables = None
    if args.tables:
        target_tables = args.tables
    elif not args.all:
        logger.info("No tables specified. Defaulting to all 9 tables.")

    sys.exit(
        run_bronze_to_silver(
            tables=target_tables,
            dry_run=args.dry_run,
            bronze_bucket=args.bronze_bucket,
            silver_bucket=args.silver_bucket,
        )
    )


if __name__ == "__main__":
    main()
