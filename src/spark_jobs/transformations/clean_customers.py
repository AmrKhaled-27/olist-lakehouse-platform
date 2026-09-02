"""Clean and standardize the Olist Customers dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_customers(df: DataFrame) -> DataFrame:
    """Clean customers dataset.

    - Validates customer_id and customer_unique_id
    - Pads zip code prefixes to 5 digits with leading zeros
    - Standardizes city and state names
    """
    cleaned = (
        df.filter(F.col("customer_id").isNotNull() & F.col("customer_unique_id").isNotNull())
        .dropDuplicates(["customer_id"])
        .withColumn("customer_id", F.trim(F.col("customer_id")))
        .withColumn("customer_unique_id", F.trim(F.col("customer_unique_id")))
        .withColumn(
            "customer_zip_code_prefix",
            F.lpad(F.trim(F.col("customer_zip_code_prefix")), 5, "0"),
        )
        .withColumn("customer_city", F.lower(F.trim(F.col("customer_city"))))
        .withColumn("customer_state", F.upper(F.trim(F.col("customer_state"))))
    )

    return cleaned
