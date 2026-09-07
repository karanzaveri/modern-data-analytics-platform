import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


URL = "https://api.frankfurter.app/latest"
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
        raise ValueError(
            f"Missing required fields: {missing_fields}"
        )

    if not isinstance(data["rates"], dict):
        raise ValueError("Rates must be a dictionary")

    if not data["rates"]:
        raise ValueError("Rates cannot be empty")

    return True


def fetch_fx_rates():
    session = create_session()

    logger.info("Fetching FX rates from Frankfurter API")

    try:
        response = session.get(URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        validate_fx_data(data)

        logger.info(
            "FX data received successfully | base=%s | date=%s | rates=%s",
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

    ingestion_timestamp = datetime.now(timezone.utc).isoformat()

    raw_record = {
        "ingested_at": ingestion_timestamp,
        "source": "frankfurter",
        "payload": data,
    }

    output_file = RAW_DIR / f"fx_rates_{data['date']}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(raw_record, file, indent=2)

    logger.info("Raw FX data saved to %s", output_file)


if __name__ == "__main__":
    fx_data = fetch_fx_rates()
    save_raw_data(fx_data)