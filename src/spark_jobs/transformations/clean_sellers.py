"""Clean and standardize the Olist Sellers dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_sellers(df: DataFrame) -> DataFrame:
    """Clean sellers dataset.

    - Validates seller_id
    - Pads zip code prefixes to 5 digits with leading zeros
    - Standardizes city and state names
    """
    cleaned = (
        df.filter(F.col("seller_id").isNotNull())
        .dropDuplicates(["seller_id"])
        .withColumn("seller_id", F.trim(F.col("seller_id")))
        .withColumn(
            "seller_zip_code_prefix",
            F.lpad(F.trim(F.col("seller_zip_code_prefix")), 5, "0"),
        )
        .withColumn("seller_city", F.lower(F.trim(F.col("seller_city"))))
        .withColumn("seller_state", F.upper(F.trim(F.col("seller_state"))))
    )

    return cleaned
