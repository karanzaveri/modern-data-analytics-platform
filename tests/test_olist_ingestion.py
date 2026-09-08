from ingestion.olist.load_olist_bigquery import TABLE_CONFIG


def test_expected_olist_tables_present():
    expected_tables = {
        "customers",
        "orders",
        "order_items",
        "payments",
        "reviews",
        "products",
        "sellers",
        "geolocation",
        "product_category_translation",
    }

    assert set(TABLE_CONFIG.keys()) == expected_tables


def test_each_table_has_file_and_schema():
    for config in TABLE_CONFIG.values():
        assert "file" in config
        assert "schema" in config
        assert config["schema"]


def test_zip_code_fields_are_strings():
    customers_schema = {
        field.name: field.field_type
        for field in TABLE_CONFIG["customers"]["schema"]
    }

    sellers_schema = {
        field.name: field.field_type
        for field in TABLE_CONFIG["sellers"]["schema"]
    }

    assert customers_schema["customer_zip_code_prefix"] == "STRING"
    assert sellers_schema["seller_zip_code_prefix"] == "STRING"