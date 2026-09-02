"""Clean and transform the Olist Order Payments dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_payments(df: DataFrame) -> DataFrame:
    """Clean and standardize order payments DataFrame.

    - Validates order_id and payment_sequential keys
    - Normalizes payment_type strings
    - Ensures payment_installments is at least 1
    - Enforces non-negative payment values
    """
    cleaned = (
        df.filter(F.col("order_id").isNotNull() & F.col("payment_sequential").isNotNull())
        .withColumn("order_id", F.trim(F.col("order_id")))
        .withColumn("payment_sequential", F.col("payment_sequential").cast("int"))
        .withColumn("payment_type", F.lower(F.trim(F.col("payment_type"))))
        .withColumn(
            "payment_type",
            F.when(
                F.col("payment_type").isin(["not_defined", ""]),
                F.lit("other"),
            ).otherwise(F.col("payment_type")),
        )
        .withColumn(
            "payment_installments",
            F.when(
                F.col("payment_installments") < 1,
                F.lit(1),
            ).otherwise(F.col("payment_installments").cast("int")),
        )
        .withColumn(
            "payment_value",
            F.when(
                F.col("payment_value") < 0.0,
                F.lit(0.0),
            ).otherwise(F.round(F.col("payment_value").cast("double"), 2)),
        )
        .dropDuplicates(["order_id", "payment_sequential"])
    )

    return cleaned
