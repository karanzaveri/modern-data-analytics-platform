from pathlib import Path

from google.cloud import bigquery


PROJECT_ID = "mda-platform-2026"
DATASET_ID = "raw"
DATA_DIR = Path("data/raw/olist")


TABLE_CONFIG = {
    "customers": {
        "file": "olist_customers_dataset.csv",
        "schema": [
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("customer_unique_id", "STRING"),
            bigquery.SchemaField("customer_zip_code_prefix", "STRING"),
            bigquery.SchemaField("customer_city", "STRING"),
            bigquery.SchemaField("customer_state", "STRING"),
        ],
    },
    "orders": {
        "file": "olist_orders_dataset.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("order_status", "STRING"),
            bigquery.SchemaField("order_purchase_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("order_approved_at", "TIMESTAMP"),
            bigquery.SchemaField("order_delivered_carrier_date", "TIMESTAMP"),
            bigquery.SchemaField("order_delivered_customer_date", "TIMESTAMP"),
            bigquery.SchemaField("order_estimated_delivery_date", "TIMESTAMP"),
        ],
    },
    "order_items": {
        "file": "olist_order_items_dataset.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("order_item_id", "INTEGER"),
            bigquery.SchemaField("product_id", "STRING"),
            bigquery.SchemaField("seller_id", "STRING"),
            bigquery.SchemaField("shipping_limit_date", "TIMESTAMP"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("freight_value", "FLOAT"),
        ],
    },

    "payments": {
    "file": "olist_order_payments_dataset.csv",
    "schema": [
        bigquery.SchemaField("order_id", "STRING"),
        bigquery.SchemaField("payment_sequential", "INTEGER"),
        bigquery.SchemaField("payment_type", "STRING"),
        bigquery.SchemaField("payment_installments", "INTEGER"),
        bigquery.SchemaField("payment_value", "FLOAT"),
        ],
    },
    "reviews": {
    "file": "olist_order_reviews_dataset.csv",
    "schema": [
        bigquery.SchemaField("review_id", "STRING"),
        bigquery.SchemaField("order_id", "STRING"),
        bigquery.SchemaField("review_score", "INTEGER"),
        bigquery.SchemaField("review_comment_title", "STRING"),
        bigquery.SchemaField("review_comment_message", "STRING"),
        bigquery.SchemaField("review_creation_date", "TIMESTAMP"),
        bigquery.SchemaField("review_answer_timestamp", "TIMESTAMP"),
        ],
    },
    "products": {
    "file": "olist_products_dataset.csv",
    "schema": [
        bigquery.SchemaField("product_id", "STRING"),
        bigquery.SchemaField("product_category_name", "STRING"),
        bigquery.SchemaField("product_name_lenght", "INTEGER"),
        bigquery.SchemaField("product_description_lenght", "INTEGER"),
        bigquery.SchemaField("product_photos_qty", "INTEGER"),
        bigquery.SchemaField("product_weight_g", "FLOAT"),
        bigquery.SchemaField("product_length_cm", "FLOAT"),
        bigquery.SchemaField("product_height_cm", "FLOAT"),
        bigquery.SchemaField("product_width_cm", "FLOAT"),
        ],
    },
    "sellers": {
    "file": "olist_sellers_dataset.csv",
    "schema": [
        bigquery.SchemaField("seller_id", "STRING"),
        bigquery.SchemaField("seller_zip_code_prefix", "STRING"),
        bigquery.SchemaField("seller_city", "STRING"),
        bigquery.SchemaField("seller_state", "STRING"),
        ],
    },
    "geolocation": {
    "file": "olist_geolocation_dataset.csv",
    "schema": [
        bigquery.SchemaField("geolocation_zip_code_prefix", "STRING"),
        bigquery.SchemaField("geolocation_lat", "FLOAT"),
        bigquery.SchemaField("geolocation_lng", "FLOAT"),
        bigquery.SchemaField("geolocation_city", "STRING"),
        bigquery.SchemaField("geolocation_state", "STRING"),
        ],
    },
    "product_category_translation": {
    "file": "product_category_name_translation.csv",
    "schema": [
        bigquery.SchemaField("product_category_name", "STRING"),
        bigquery.SchemaField("product_category_name_english", "STRING"),
        ],
    }
}


def load_table(table_name):
    client = bigquery.Client(project=PROJECT_ID)

    config = TABLE_CONFIG[table_name]

    file_path = DATA_DIR / config["file"]
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        schema=config["schema"],
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    with open(file_path, "rb") as file:
        load_job = client.load_table_from_file(
            file,
            table_id,
            job_config=job_config,
        )

    load_job.result()

    table = client.get_table(table_id)

    print(
        f"Loaded {table.num_rows} rows into {table_id}"
    )


if __name__ == "__main__":
    for table_name in TABLE_CONFIG:
        load_table(table_name)