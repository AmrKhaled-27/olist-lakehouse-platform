"""Unit tests for Spark StructType Schema definitions."""

from src.spark_jobs.schemas import (
    CATEGORY_TRANSLATION_SCHEMA,
    CUSTOMERS_SCHEMA,
    GEOLOCATION_RAW_SCHEMA,
    GEOLOCATION_SILVER_SCHEMA,
    ORDER_ITEMS_RAW_SCHEMA,
    ORDER_PAYMENTS_SCHEMA,
    ORDER_REVIEWS_RAW_SCHEMA,
    ORDERS_RAW_SCHEMA,
    ORDERS_SILVER_SCHEMA,
    PRODUCTS_SCHEMA,
    RAW_SCHEMAS,
    SELLERS_SCHEMA,
)


def test_raw_schemas_coverage():
    """Verify that all 9 Olist datasets have defined schemas in the registry."""
    expected_tables = {
        "orders",
        "order_items",
        "customers",
        "order_payments",
        "order_reviews",
        "products",
        "sellers",
        "geolocation",
        "product_category_name_translation",
    }
    assert set(RAW_SCHEMAS.keys()) == expected_tables


def test_orders_schema_fields():
    """Verify orders schema fields and types."""
    field_names = ORDERS_RAW_SCHEMA.fieldNames()
    assert "order_id" in field_names
    assert "customer_id" in field_names
    assert "order_status" in field_names
    assert "order_purchase_timestamp" in field_names

    silver_fields = ORDERS_SILVER_SCHEMA.fieldNames()
    assert "actual_delivery_days" in silver_fields
    assert "purchase_year" in silver_fields
    assert "purchase_month" in silver_fields


def test_order_items_schema_fields():
    """Verify order items schema fields."""
    field_names = ORDER_ITEMS_RAW_SCHEMA.fieldNames()
    assert "order_id" in field_names
    assert "order_item_id" in field_names
    assert "price" in field_names
    assert "freight_value" in field_names


def test_customers_schema_fields():
    """Verify customers schema fields."""
    field_names = CUSTOMERS_SCHEMA.fieldNames()
    assert "customer_id" in field_names
    assert "customer_unique_id" in field_names
    assert "customer_zip_code_prefix" in field_names


def test_payments_schema_fields():
    """Verify payments schema fields."""
    field_names = ORDER_PAYMENTS_SCHEMA.fieldNames()
    assert "order_id" in field_names
    assert "payment_type" in field_names
    assert "payment_value" in field_names


def test_reviews_schema_fields():
    """Verify reviews raw schema fields."""
    field_names = ORDER_REVIEWS_RAW_SCHEMA.fieldNames()
    assert "review_id" in field_names
    assert "order_id" in field_names
    assert "review_score" in field_names
    assert "review_comment_message" in field_names


def test_geolocation_schemas():
    """Verify geolocation raw and silver schema fields."""
    raw_fields = GEOLOCATION_RAW_SCHEMA.fieldNames()
    assert "geolocation_zip_code_prefix" in raw_fields
    assert "geolocation_lat" in raw_fields
    assert "geolocation_lng" in raw_fields

    silver_fields = GEOLOCATION_SILVER_SCHEMA.fieldNames()
    assert "record_count" in silver_fields


def test_products_and_sellers_schemas():
    """Verify products, sellers, and translations schema fields."""
    prod_fields = PRODUCTS_SCHEMA.fieldNames()
    assert "product_id" in prod_fields
    assert "product_category_name" in prod_fields

    seller_fields = SELLERS_SCHEMA.fieldNames()
    assert "seller_id" in seller_fields
    assert "seller_zip_code_prefix" in seller_fields

    trans_fields = CATEGORY_TRANSLATION_SCHEMA.fieldNames()
    assert "product_category_name" in trans_fields
    assert "product_category_name_english" in trans_fields
