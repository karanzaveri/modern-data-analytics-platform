import argparse
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.frankfurter.app"
RAW_DIR = Path("data/raw/fx")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def create_session():
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount("https://", adapter)

    return session


def validate_fx_data(data):
    required_fields = {"amount", "base", "date", "rates"}
    missing_fields = required_fields - data.keys()

    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    if not isinstance(data["rates"], dict):
        raise ValueError("Rates must be a dictionary")

    if not data["rates"]:
        raise ValueError("Rates cannot be empty")


def build_url(requested_date=None):
    if requested_date:
        return f"{BASE_URL}/{requested_date}"

    return f"{BASE_URL}/latest"


def fetch_fx_rates(requested_date=None):
    session = create_session()
    url = build_url(requested_date)

    logger.info("Fetching FX rates from %s", url)

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        validate_fx_data(data)

        logger.info(
            "FX data received | base=%s | date=%s | rates=%s",
            data["base"],
            data["date"],
            len(data["rates"]),
        )

        return data

    except requests.RequestException as error:
        logger.error("API request failed: %s", error)
        raise

    except ValueError as error:
        logger.error("FX data validation failed: %s", error)
        raise


def save_raw_data(data):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    raw_record = {
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": "frankfurter",
        "payload": data,
    }

    output_file = RAW_DIR / f"fx_rates_{data['date']}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(raw_record, file, indent=2)

    logger.info("Raw FX data saved to %s", output_file)

def validate_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return date_string
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Date must be in YYYY-MM-DD format"
        ) from exc

def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch FX rates from the Frankfurter API"
    )

    parser.add_argument(
    "--date",
    type=validate_date,
    help="Historical date in YYYY-MM-DD format",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    fx_data = fetch_fx_rates(args.date)
    save_raw_data(fx_data)