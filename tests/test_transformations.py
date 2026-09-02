"""Unit tests for modular PySpark data transformations."""

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

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


def test_clean_orders(spark_session: SparkSession):
    """Test orders cleaning, date parsing, duration metrics, and partitioning features."""
    schema = StructType(
        [
            StructField("order_id", StringType(), False),
            StructField("customer_id", StringType(), False),
            StructField("order_status", StringType(), True),
            StructField("order_purchase_timestamp", StringType(), True),
            StructField("order_approved_at", StringType(), True),
            StructField("order_delivered_carrier_date", StringType(), True),
            StructField("order_delivered_customer_date", StringType(), True),
            StructField("order_estimated_delivery_date", StringType(), True),
        ]
    )

    data = [
        (
            "ord_1",
            "cust_1",
            "DELIVERED ",
            "2018-05-01 10:00:00",
            "2018-05-01 12:00:00",
            "2018-05-02 10:00:00",
            "2018-05-05 10:00:00",
            "2018-05-10 00:00:00",
        ),
        (
            "ord_2",
            "cust_2",
            "delivered",
            "2017-10-01 10:00:00",
            "2017-10-01 11:00:00",
            "2017-10-02 10:00:00",
            "2017-10-20 10:00:00",  # Delivered after estimated date
            "2017-10-15 00:00:00",
        ),
        (
            "ord_1",  # Duplicate order_id
            "cust_1",
            "delivered",
            "2018-05-01 10:00:00",
            "2018-05-01 12:00:00",
            "2018-05-02 10:00:00",
            "2018-05-05 10:00:00",
            "2018-05-10 00:00:00",
        ),
    ]

    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_orders(raw_df)
    results = {row["order_id"]: row for row in cleaned_df.collect()}

    assert len(results) == 2  # Duplicate removed

    # Test ord_1 (delivered on time, 4 days actual duration, 2 hours approval delay)
    ord1 = results["ord_1"]
    assert ord1["order_status"] == "delivered"
    assert ord1["actual_delivery_days"] == 4.0
    assert ord1["approval_delay_hours"] == 2.0
    assert ord1["is_delivered_on_time"] == 1
    assert ord1["purchase_year"] == 2018
    assert ord1["purchase_month"] == 5

    # Test ord_2 (delivered late)
    ord2 = results["ord_2"]
    assert ord2["is_delivered_on_time"] == 0
    assert ord2["purchase_year"] == 2017
    assert ord2["purchase_month"] == 10


def test_clean_payments(spark_session: SparkSession):
    """Test payments cleaning, installment floor, and negative value protection."""
    schema = StructType(
        [
            StructField("order_id", StringType(), False),
            StructField("payment_sequential", IntegerType(), False),
            StructField("payment_type", StringType(), True),
            StructField("payment_installments", IntegerType(), True),
            StructField("payment_value", DoubleType(), True),
        ]
    )

    data = [
        ("ord_1", 1, "CREDIT_CARD ", 0, 150.50),  # 0 installments -> 1
        ("ord_1", 2, "not_defined", 1, 20.0),  # not_defined -> other
        ("ord_2", 1, "voucher", 3, -10.0),  # negative value -> 0.0
    ]

    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_payments(raw_df)
    rows = cleaned_df.collect()

    assert len(rows) == 3
    assert rows[0]["payment_type"] == "credit_card"
    assert rows[0]["payment_installments"] == 1
    assert rows[0]["payment_value"] == 150.50

    assert rows[1]["payment_type"] == "other"
    assert rows[2]["payment_value"] == 0.0


def test_clean_geolocation(spark_session: SparkSession):
    """Test geolocation zip code padding, centroid calculation, and boundary filtering."""
    schema = StructType(
        [
            StructField("geolocation_zip_code_prefix", StringType(), False),
            StructField("geolocation_lat", DoubleType(), True),
            StructField("geolocation_lng", DoubleType(), True),
            StructField("geolocation_city", StringType(), True),
            StructField("geolocation_state", StringType(), True),
        ]
    )

    data = [
        ("3176", -23.50, -46.50, "Sao Paulo ", "sp "),  # Zip padding needed
        ("03176", -23.60, -46.60, "sao paulo", "SP"),  # Same zip, will be averaged
        ("99999", 50.0, -100.0, "Invalid Country", "XX"),  # Outlier coords (outside Brazil)
    ]

    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_geolocation(raw_df)
    rows = cleaned_df.collect()

    assert len(rows) == 1  # Outlier filtered, 2 valid rows grouped into 1 centroid
    geo = rows[0]
    assert geo["geolocation_zip_code_prefix"] == "03176"
    assert geo["geolocation_lat"] == -23.55
    assert geo["geolocation_lng"] == -46.55
    assert geo["geolocation_city"] == "sao paulo"
    assert geo["geolocation_state"] == "SP"
    assert geo["record_count"] == 2


def test_clean_reviews(spark_session: SparkSession):
    """Test review score clamping and comment newline stripping."""
    schema = StructType(
        [
            StructField("review_id", StringType(), False),
            StructField("order_id", StringType(), False),
            StructField("review_score", IntegerType(), True),
            StructField("review_comment_title", StringType(), True),
            StructField("review_comment_message", StringType(), True),
            StructField("review_creation_date", StringType(), True),
            StructField("review_answer_timestamp", StringType(), True),
        ]
    )

    data = [
        (
            "rev_1",
            "ord_1",
            6,  # Clamped to 5
            "Great ",
            "Fast shipping!\r\nVery happy.",
            "2018-05-06 00:00:00",
            "2018-05-07 10:00:00",
        ),
        (
            "rev_2",
            "ord_2",
            0,  # Clamped to 1
            None,
            None,
            "2018-05-06 00:00:00",
            "2018-05-07 10:00:00",
        ),
    ]

    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_reviews(raw_df)
    results = {row["review_id"]: row for row in cleaned_df.collect()}

    assert results["rev_1"]["review_score"] == 5
    assert results["rev_1"]["review_comment_message"] == "Fast shipping! Very happy."
    assert results["rev_1"]["has_review_comment"] == 1

    assert results["rev_2"]["review_score"] == 1
    assert results["rev_2"]["has_review_comment"] == 0


def test_clean_products(spark_session: SparkSession):
    """Test product category fallback and dimension casting."""
    schema = StructType(
        [
            StructField("product_id", StringType(), False),
            StructField("product_category_name", StringType(), True),
            StructField("product_name_lenght", IntegerType(), True),
            StructField("product_description_lenght", IntegerType(), True),
            StructField("product_photos_qty", IntegerType(), True),
            StructField("product_weight_g", DoubleType(), True),
            StructField("product_length_cm", DoubleType(), True),
            StructField("product_height_cm", DoubleType(), True),
            StructField("product_width_cm", DoubleType(), True),
        ]
    )

    data = [
        ("prod_1", None, 50, 200, 2, 500.0, 20.0, 10.0, 15.0),
        ("prod_2", " beleza_saude ", 45, 150, 1, 300.0, 15.0, 5.0, 10.0),
    ]

    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_products(raw_df)
    results = {row["product_id"]: row for row in cleaned_df.collect()}

    assert results["prod_1"]["product_category_name"] == "unknown"
    assert results["prod_2"]["product_category_name"] == "beleza_saude"


def test_clean_customers_and_sellers(spark_session: SparkSession):
    """Test customer and seller zip code padding and case normalization."""
    cust_schema = StructType(
        [
            StructField("customer_id", StringType(), False),
            StructField("customer_unique_id", StringType(), False),
            StructField("customer_zip_code_prefix", StringType(), True),
            StructField("customer_city", StringType(), True),
            StructField("customer_state", StringType(), True),
        ]
    )
    cust_data = [("c1", "u1", "123", " Rio de Janeiro ", "rj ")]
    cust_df = clean_customers(spark_session.createDataFrame(cust_data, cust_schema))
    c_row = cust_df.collect()[0]

    assert c_row["customer_zip_code_prefix"] == "00123"
    assert c_row["customer_city"] == "rio de janeiro"
    assert c_row["customer_state"] == "RJ"

    seller_schema = StructType(
        [
            StructField("seller_id", StringType(), False),
            StructField("seller_zip_code_prefix", StringType(), True),
            StructField("seller_city", StringType(), True),
            StructField("seller_state", StringType(), True),
        ]
    )
    seller_data = [("s1", "5432", " Curitiba", "pr")]
    seller_df = clean_sellers(spark_session.createDataFrame(seller_data, seller_schema))
    s_row = seller_df.collect()[0]

    assert s_row["seller_zip_code_prefix"] == "05432"
    assert s_row["seller_city"] == "curitiba"
    assert s_row["seller_state"] == "PR"


def test_clean_order_items(spark_session: SparkSession):
    """Test order items price rounding and total value calculation."""
    schema = StructType(
        [
            StructField("order_id", StringType(), False),
            StructField("order_item_id", IntegerType(), False),
            StructField("product_id", StringType(), False),
            StructField("seller_id", StringType(), False),
            StructField("shipping_limit_date", StringType(), True),
            StructField("price", DoubleType(), True),
            StructField("freight_value", DoubleType(), True),
        ]
    )

    data = [("ord_1", 1, "p1", "s1", "2018-05-02 10:00:00", 29.99, 8.71)]
    raw_df = spark_session.createDataFrame(data, schema)
    cleaned_df = clean_order_items(raw_df)
    row = cleaned_df.collect()[0]

    assert row["price"] == 29.99
    assert row["freight_value"] == 8.71
    assert row["total_item_value"] == 38.70
