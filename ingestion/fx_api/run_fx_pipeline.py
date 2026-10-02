import argparse

from ingestion.fx_api.fetch_fx_rates import (
    fetch_fx_rates,
    save_raw_data,
    validate_date,
)
from ingestion.fx_api.load_bigquery import load_fx_to_bigquery


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the FX ingestion pipeline"
    )

    parser.add_argument(
        "--date",
        type=validate_date,
        help="Historical date in YYYY-MM-DD format",
    )

    return parser.parse_args()


def run_pipeline(requested_date=None):
    fx_data = fetch_fx_rates(requested_date)

    save_raw_data(fx_data)

    load_fx_to_bigquery(fx_data)


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.date)