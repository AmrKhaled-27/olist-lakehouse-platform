"""Clean and transform the Olist Order Reviews dataset."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_reviews(df: DataFrame) -> DataFrame:
    """Clean and transform order reviews DataFrame.

    - Deduplicates on review_id
    - Clamps review_score to valid range [1, 5]
    - Cleans review comment text and removes line breaks
    - Parses creation and answer timestamps
    - Adds has_review_comment indicator
    """
    cleaned = (
        df.filter(F.col("review_id").isNotNull() & F.col("order_id").isNotNull())
        .dropDuplicates(["review_id"])
        .withColumn("review_id", F.trim(F.col("review_id")))
        .withColumn("order_id", F.trim(F.col("order_id")))
        .withColumn(
            "review_score",
            F.when(F.col("review_score") > 5, F.lit(5))
            .when(F.col("review_score") < 1, F.lit(1))
            .otherwise(F.col("review_score").cast("int")),
        )
        .withColumn("review_comment_title", F.trim(F.col("review_comment_title")))
        .withColumn(
            "review_comment_message",
            F.regexp_replace(F.trim(F.col("review_comment_message")), r"[\r\n]+", " "),
        )
        .withColumn(
            "review_creation_date",
            F.to_timestamp(F.col("review_creation_date")),
        )
        .withColumn(
            "review_answer_timestamp",
            F.to_timestamp(F.col("review_answer_timestamp")),
        )
        .withColumn(
            "has_review_comment",
            F.when(
                F.col("review_comment_message").isNotNull()
                & (F.length(F.trim(F.col("review_comment_message"))) > 0),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
    )

    return cleaned
