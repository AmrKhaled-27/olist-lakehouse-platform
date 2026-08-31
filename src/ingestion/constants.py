"""Constants, metadata schemas, and test fixtures for Olist Bronze Ingestion."""

from typing import Any, Dict

# Kaggle & Default Path Configuration
KAGGLE_DATASET_SLUG: str = "olistbr/brazilian-ecommerce"
DEFAULT_BRONZE_BUCKET: str = "bronze"
DEFAULT_RAW_DATA_PATH: str = "./data/raw"

# Expected 9 Olist CSV dataset metadata definitions
OLIST_DATASET_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "orders": {
        "filename": "olist_orders_dataset.csv",
        "description": "Core orders dataset containing purchase timestamps and status",
        "target_prefix": "raw/orders",
    },
    "order_items": {
        "filename": "olist_order_items_dataset.csv",
        "description": "Item details, prices, freight values, and seller assignments",
        "target_prefix": "raw/order_items",
    },
    "customers": {
        "filename": "olist_customers_dataset.csv",
        "description": "Customer zip codes and geographic location references",
        "target_prefix": "raw/customers",
    },
    "order_payments": {
        "filename": "olist_order_payments_dataset.csv",
        "description": "Payment types, installments, and payment amounts",
        "target_prefix": "raw/order_payments",
    },
    "order_reviews": {
        "filename": "olist_order_reviews_dataset.csv",
        "description": "Customer review scores, comments, and review timestamps",
        "target_prefix": "raw/order_reviews",
    },
    "products": {
        "filename": "olist_products_dataset.csv",
        "description": "Product dimensions, weight, photos, and category names",
        "target_prefix": "raw/products",
    },
    "sellers": {
        "filename": "olist_sellers_dataset.csv",
        "description": "Seller identification and location zip codes",
        "target_prefix": "raw/sellers",
    },
    "geolocation": {
        "filename": "olist_geolocation_dataset.csv",
        "description": "Brazilian zip code to latitude/longitude and city mappings",
        "target_prefix": "raw/geolocation",
    },
    "product_category_name_translation": {
        "filename": "product_category_name_translation.csv",
        "description": "Portuguese to English product category translation mapping",
        "target_prefix": "raw/product_category_name_translation",
    },
}

# Minimal valid starter sample CSV payloads for local testing and CI/CD
SAMPLE_DATASETS_PAYLOAD: Dict[str, str] = {
    "olist_orders_dataset.csv": (
        "order_id,customer_id,order_status,order_purchase_timestamp,"
        "order_approved_at,order_delivered_carrier_date,"
        "order_delivered_customer_date,order_estimated_delivery_date\n"
        "e481f51cbdc54678b7cc49136f2d6af7,9ef432eb62512f359111f59e6801bdd0,"
        "delivered,2017-10-02 10:56:33,2017-10-02 11:07:15,"
        "2017-10-04 19:55:00,2017-10-10 21:25:13,2017-10-18 00:00:00\n"
        "53cdb2fc8bc7dce0b6741e2150273451,b0830fb4747a6c6d20dea0b8c802d777,"
        "delivered,2018-07-24 20:41:37,2018-07-26 03:24:27,"
        "2018-07-26 14:31:00,2018-08-07 15:27:45,2018-08-13 00:00:00\n"
    ),
    "olist_order_items_dataset.csv": (
        "order_id,order_item_id,product_id,seller_id,"
        "shipping_limit_date,price,freight_value\n"
        "e481f51cbdc54678b7cc49136f2d6af7,1,87285b34884572647811a353c7acb740,"
        "3504c0c36d244408fedbc0ee45e4f377,2017-10-06 11:07:15,29.99,8.72\n"
    ),
    "olist_customers_dataset.csv": (
        "customer_id,customer_unique_id,customer_zip_code_prefix,"
        "customer_city,customer_state\n"
        "9ef432eb62512f359111f59e6801bdd0,7c396fd4830fd04220f3174c4ce21a84,"
        "03176,sao paulo,SP\n"
        "b0830fb4747a6c6d20dea0b8c802d777,af8613a04217b18e3ce838dbb2585fe7,"
        "47813,barreiras,BA\n"
    ),
    "olist_order_payments_dataset.csv": (
        "order_id,payment_sequential,payment_type,payment_installments,payment_value\n"
        "e481f51cbdc54678b7cc49136f2d6af7,1,credit_card,1,18.12\n"
        "e481f51cbdc54678b7cc49136f2d6af7,2,voucher,1,20.59\n"
    ),
    "olist_order_reviews_dataset.csv": (
        "review_id,order_id,review_score,review_comment_title,"
        "review_comment_message,review_creation_date,review_answer_timestamp\n"
        "7bc249e13d9a73b28534b5bc3fc67257,e481f51cbdc54678b7cc49136f2d6af7,"
        "4,,Parabens rapidez na entrega,2017-10-11 00:00:00,2017-10-12 03:43:48\n"
    ),
    "olist_products_dataset.csv": (
        "product_id,product_category_name,product_name_lenght,"
        "product_description_lenght,product_photos_qty,"
        "product_weight_g,product_length_cm,product_height_cm,product_width_cm\n"
        "87285b34884572647811a353c7acb740,utilidades_domesticas,40,268,4,500,19,8,13\n"
    ),
    "olist_sellers_dataset.csv": (
        "seller_id,seller_zip_code_prefix,seller_city,seller_state\n"
        "3504c0c36d244408fedbc0ee45e4f377,22780,rio de janeiro,RJ\n"
    ),
    "olist_geolocation_dataset.csv": (
        "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,"
        "geolocation_city,geolocation_state\n"
        "03176,-23.548318,-46.595262,sao paulo,SP\n"
    ),
    "product_category_name_translation.csv": (
        "product_category_name,product_category_name_english\n" "utilidades_domesticas,housewares\n"
    ),
}
