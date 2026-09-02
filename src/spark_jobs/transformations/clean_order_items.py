"""Clean and transform the Olist Order Items dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_order_items(df: DataFrame) -> DataFrame:
    """Clean order items dataset.

    - Validates order_id and order_item_id
    - Casts shipping_limit_date to TimestampType
    - Rounds monetary amounts and computes total item value
    """
    cleaned = (
        df.filter(F.col("order_id").isNotNull() & F.col("order_item_id").isNotNull())
        .dropDuplicates(["order_id", "order_item_id"])
        .withColumn("order_id", F.trim(F.col("order_id")))
        .withColumn("order_item_id", F.col("order_item_id").cast("int"))
        .withColumn("product_id", F.trim(F.col("product_id")))
        .withColumn("seller_id", F.trim(F.col("seller_id")))
        .withColumn(
            "shipping_limit_date",
            F.to_timestamp(F.col("shipping_limit_date")),
        )
        .withColumn(
            "price",
            F.when(F.col("price") < 0.0, F.lit(0.0)).otherwise(
                F.round(F.col("price").cast("double"), 2)
            ),
        )
        .withColumn(
            "freight_value",
            F.when(F.col("freight_value") < 0.0, F.lit(0.0)).otherwise(
                F.round(F.col("freight_value").cast("double"), 2)
            ),
        )
        .withColumn(
            "total_item_value",
            F.round(F.col("price") + F.col("freight_value"), 2),
        )
    )

    return cleaned
