"""Clean and transform the Olist Orders dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_orders(df: DataFrame) -> DataFrame:
    """Clean and enrich raw orders DataFrame.

    - Deduplicates on order_id
    - Drops invalid records with missing primary keys
    - Parses all timestamps to UTC TimestampType
    - Computes delivery duration, approval delay, on-time delivery flags
    - Extracts purchase_year and purchase_month for partitioning
    """
    cleaned = (
        df.filter(F.col("order_id").isNotNull() & F.col("customer_id").isNotNull())
        .dropDuplicates(["order_id"])
        .withColumn("order_id", F.trim(F.col("order_id")))
        .withColumn("customer_id", F.trim(F.col("customer_id")))
        .withColumn("order_status", F.lower(F.trim(F.col("order_status"))))
        .withColumn(
            "order_purchase_timestamp",
            F.to_timestamp(F.col("order_purchase_timestamp")),
        )
        .withColumn(
            "order_approved_at",
            F.to_timestamp(F.col("order_approved_at")),
        )
        .withColumn(
            "order_delivered_carrier_date",
            F.to_timestamp(F.col("order_delivered_carrier_date")),
        )
        .withColumn(
            "order_delivered_customer_date",
            F.to_timestamp(F.col("order_delivered_customer_date")),
        )
        .withColumn(
            "order_estimated_delivery_date",
            F.to_timestamp(F.col("order_estimated_delivery_date")),
        )
    )

    # Derived analytical features
    enriched = (
        cleaned.withColumn(
            "actual_delivery_days",
            F.round(
                (
                    F.unix_timestamp("order_delivered_customer_date")
                    - F.unix_timestamp("order_purchase_timestamp")
                )
                / 86400.0,
                2,
            ),
        )
        .withColumn(
            "estimated_delivery_days",
            F.round(
                (
                    F.unix_timestamp("order_estimated_delivery_date")
                    - F.unix_timestamp("order_purchase_timestamp")
                )
                / 86400.0,
                2,
            ),
        )
        .withColumn(
            "approval_delay_hours",
            F.round(
                (
                    F.unix_timestamp("order_approved_at")
                    - F.unix_timestamp("order_purchase_timestamp")
                )
                / 3600.0,
                2,
            ),
        )
        .withColumn(
            "is_delivered_on_time",
            F.when(
                F.col("order_delivered_customer_date").isNotNull()
                & F.col("order_estimated_delivery_date").isNotNull(),
                F.when(
                    F.col("order_delivered_customer_date")
                    <= F.col("order_estimated_delivery_date"),
                    1,
                ).otherwise(0),
            ).otherwise(None),
        )
        .withColumn("purchase_year", F.year("order_purchase_timestamp"))
        .withColumn("purchase_month", F.month("order_purchase_timestamp"))
    )

    return enriched
