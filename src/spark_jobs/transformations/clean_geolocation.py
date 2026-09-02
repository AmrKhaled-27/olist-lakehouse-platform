"""Clean and deduplicate the Olist Geolocation dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_geolocation(df: DataFrame) -> DataFrame:
    """Clean and deduplicate geolocation records.

    - Pads zip codes to 5 digits with leading zeros
    - Filters out invalid/outlier coordinates outside Brazil's bounding box
    - Computes the centroid (mean latitude and longitude) per zip code prefix
    - Standardizes city and state names
    """
    valid_coords = (
        df.filter(F.col("geolocation_zip_code_prefix").isNotNull())
        .withColumn(
            "geolocation_zip_code_prefix",
            F.lpad(F.trim(F.col("geolocation_zip_code_prefix")), 5, "0"),
        )
        .withColumn("geolocation_lat", F.col("geolocation_lat").cast("double"))
        .withColumn("geolocation_lng", F.col("geolocation_lng").cast("double"))
        .withColumn("geolocation_city", F.lower(F.trim(F.col("geolocation_city"))))
        .withColumn("geolocation_state", F.upper(F.trim(F.col("geolocation_state"))))
        # Filter valid Brazilian coordinate boundaries
        .filter(
            (F.col("geolocation_lat") >= -35.0)
            & (F.col("geolocation_lat") <= 6.0)
            & (F.col("geolocation_lng") >= -75.0)
            & (F.col("geolocation_lng") <= -30.0)
        )
    )

    # Deduplicate by zip code prefix computing centroid
    deduplicated = (
        valid_coords.groupBy("geolocation_zip_code_prefix")
        .agg(
            F.round(F.avg("geolocation_lat"), 6).alias("geolocation_lat"),
            F.round(F.avg("geolocation_lng"), 6).alias("geolocation_lng"),
            F.first("geolocation_city").alias("geolocation_city"),
            F.first("geolocation_state").alias("geolocation_state"),
            F.count("*").cast("int").alias("record_count"),
        )
        .orderBy("geolocation_zip_code_prefix")
    )

    return deduplicated
