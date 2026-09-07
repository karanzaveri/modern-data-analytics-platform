import json
from pathlib import Path

import requests


URL = "https://api.frankfurter.app/latest"
RAW_DIR = Path("data/raw/fx")


def fetch_fx_rates():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("Base currency:", data["base"])
        print("Date:", data["date"])
        print("Number of rates:", len(data["rates"]))

        return data

    except requests.RequestException as error:
        print(f"API request failed: {error}")
        return None


def save_raw_data(data):
    if data is None:
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_file = RAW_DIR / f"fx_rates_{data['date']}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print(f"Saved raw data to: {output_file}")


if __name__ == "__main__":
    fx_data = fetch_fx_rates()
    save_raw_data(fx_data)