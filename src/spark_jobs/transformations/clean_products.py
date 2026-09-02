"""Clean and transform the Olist Products dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_products(df: DataFrame) -> DataFrame:
    """Clean products dataset.

    - Deduplicates on product_id
    - Fills missing category names with 'unknown'
    - Casts dimensions and weights to clean numeric values
    """
    cleaned = (
        df.filter(F.col("product_id").isNotNull())
        .dropDuplicates(["product_id"])
        .withColumn("product_id", F.trim(F.col("product_id")))
        .withColumn(
            "product_category_name",
            F.coalesce(F.trim(F.col("product_category_name")), F.lit("unknown")),
        )
        .withColumn(
            "product_name_lenght",
            F.col("product_name_lenght").cast("int"),
        )
        .withColumn(
            "product_description_lenght",
            F.col("product_description_lenght").cast("int"),
        )
        .withColumn(
            "product_photos_qty",
            F.col("product_photos_qty").cast("int"),
        )
        .withColumn(
            "product_weight_g",
            F.col("product_weight_g").cast("double"),
        )
        .withColumn(
            "product_length_cm",
            F.col("product_length_cm").cast("double"),
        )
        .withColumn(
            "product_height_cm",
            F.col("product_height_cm").cast("double"),
        )
        .withColumn(
            "product_width_cm",
            F.col("product_width_cm").cast("double"),
        )
    )

    return cleaned
