"""Strict StructType Schema definitions for all 9 Olist Lakehouse tables."""

from typing import Dict
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# -----------------------------------------------------------------------------
# 1. Orders
# -----------------------------------------------------------------------------
ORDERS_RAW_SCHEMA = StructType(
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

ORDERS_SILVER_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), False),
        StructField("customer_id", StringType(), False),
        StructField("order_status", StringType(), True),
        StructField("order_purchase_timestamp", TimestampType(), True),
        StructField("order_approved_at", TimestampType(), True),
        StructField("order_delivered_carrier_date", TimestampType(), True),
        StructField("order_delivered_customer_date", TimestampType(), True),
        StructField("order_estimated_delivery_date", TimestampType(), True),
        # Derived analytical features
        StructField("actual_delivery_days", DoubleType(), True),
        StructField("estimated_delivery_days", DoubleType(), True),
        StructField("approval_delay_hours", DoubleType(), True),
        StructField("is_delivered_on_time", IntegerType(), True),
        StructField("purchase_year", IntegerType(), True),
        StructField("purchase_month", IntegerType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 2. Order Items
# -----------------------------------------------------------------------------
ORDER_ITEMS_RAW_SCHEMA = StructType(
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

ORDER_ITEMS_SILVER_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), False),
        StructField("order_item_id", IntegerType(), False),
        StructField("product_id", StringType(), False),
        StructField("seller_id", StringType(), False),
        StructField("shipping_limit_date", TimestampType(), True),
        StructField("price", DoubleType(), True),
        StructField("freight_value", DoubleType(), True),
        StructField("total_item_value", DoubleType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 3. Customers
# -----------------------------------------------------------------------------
CUSTOMERS_SCHEMA = StructType(
    [
        StructField("customer_id", StringType(), False),
        StructField("customer_unique_id", StringType(), False),
        StructField("customer_zip_code_prefix", StringType(), True),
        StructField("customer_city", StringType(), True),
        StructField("customer_state", StringType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 4. Order Payments
# -----------------------------------------------------------------------------
ORDER_PAYMENTS_SCHEMA = StructType(
    [
        StructField("order_id", StringType(), False),
        StructField("payment_sequential", IntegerType(), False),
        StructField("payment_type", StringType(), True),
        StructField("payment_installments", IntegerType(), True),
        StructField("payment_value", DoubleType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 5. Order Reviews
# -----------------------------------------------------------------------------
ORDER_REVIEWS_RAW_SCHEMA = StructType(
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

ORDER_REVIEWS_SILVER_SCHEMA = StructType(
    [
        StructField("review_id", StringType(), False),
        StructField("order_id", StringType(), False),
        StructField("review_score", IntegerType(), True),
        StructField("review_comment_title", StringType(), True),
        StructField("review_comment_message", StringType(), True),
        StructField("review_creation_date", TimestampType(), True),
        StructField("review_answer_timestamp", TimestampType(), True),
        StructField("has_review_comment", IntegerType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 6. Products
# -----------------------------------------------------------------------------
PRODUCTS_SCHEMA = StructType(
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

# -----------------------------------------------------------------------------
# 7. Sellers
# -----------------------------------------------------------------------------
SELLERS_SCHEMA = StructType(
    [
        StructField("seller_id", StringType(), False),
        StructField("seller_zip_code_prefix", StringType(), True),
        StructField("seller_city", StringType(), True),
        StructField("seller_state", StringType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 8. Geolocation
# -----------------------------------------------------------------------------
GEOLOCATION_RAW_SCHEMA = StructType(
    [
        StructField("geolocation_zip_code_prefix", StringType(), False),
        StructField("geolocation_lat", DoubleType(), True),
        StructField("geolocation_lng", DoubleType(), True),
        StructField("geolocation_city", StringType(), True),
        StructField("geolocation_state", StringType(), True),
    ]
)

GEOLOCATION_SILVER_SCHEMA = StructType(
    [
        StructField("geolocation_zip_code_prefix", StringType(), False),
        StructField("geolocation_lat", DoubleType(), True),
        StructField("geolocation_lng", DoubleType(), True),
        StructField("geolocation_city", StringType(), True),
        StructField("geolocation_state", StringType(), True),
        StructField("record_count", IntegerType(), True),
    ]
)

# -----------------------------------------------------------------------------
# 9. Product Category Name Translation
# -----------------------------------------------------------------------------
CATEGORY_TRANSLATION_SCHEMA = StructType(
    [
        StructField("product_category_name", StringType(), False),
        StructField("product_category_name_english", StringType(), True),
    ]
)

# Master mapping of dataset key to raw schema
RAW_SCHEMAS: Dict[str, StructType] = {
    "orders": ORDERS_RAW_SCHEMA,
    "order_items": ORDER_ITEMS_RAW_SCHEMA,
    "customers": CUSTOMERS_SCHEMA,
    "order_payments": ORDER_PAYMENTS_SCHEMA,
    "order_reviews": ORDER_REVIEWS_RAW_SCHEMA,
    "products": PRODUCTS_SCHEMA,
    "sellers": SELLERS_SCHEMA,
    "geolocation": GEOLOCATION_RAW_SCHEMA,
    "product_category_name_translation": CATEGORY_TRANSLATION_SCHEMA,
}
