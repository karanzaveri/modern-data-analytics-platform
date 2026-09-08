from datetime import datetime, timezone

from google.cloud import bigquery


PROJECT_ID = "mda-platform-2026"
DATASET_ID = "raw"
TABLE_ID = "fx_rates"


def transform_fx_for_bigquery(data):
    ingested_at = datetime.now(timezone.utc).isoformat()

    rows = []

    for currency, rate in data["rates"].items():
        rows.append(
            {
                "rate_date": data["date"],
                "base_currency": data["base"],
                "target_currency": currency,
                "rate": rate,
                "ingested_at": ingested_at,
                "source": "frankfurter",
            }
        )

    return rows


def load_fx_to_bigquery(data):
    client = bigquery.Client(project=PROJECT_ID)

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    schema = [
        bigquery.SchemaField("rate_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("base_currency", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_currency", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("rate", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    ]

    rows = transform_fx_for_bigquery(data)

    requested_date = data["date"]

    check_sql = f"""
    SELECT COUNT(*) AS row_count
    FROM `{table_ref}`
    WHERE rate_date = @requested_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "requested_date",
                "DATE",
                requested_date,
            )
        ]
    )

    try:
        result = client.query(
            check_sql,
            job_config=job_config,
        ).result()

        existing_rows = next(result).row_count

        if existing_rows > 0:
            print(
                f"FX rates for {requested_date} already exist "
                f"in {table_ref}. Skipping load."
            )
            return

    except Exception:
        # Table may not exist yet on the first run.
        pass

    load_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    load_job = client.load_table_from_json(
        rows,
        table_ref,
        job_config=load_config,
    )

    load_job.result()

    print(f"Loaded {len(rows)} rows into {table_ref}")