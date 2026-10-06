import re
from datetime import date


def extract_numbers(text: str) -> list[float]:
    """Extract numeric KPI values while ignoring ISO dates."""

    # Remove ISO dates such as 2018-07-01 before extracting numbers.
    text_without_dates = re.sub(
        r"\b\d{4}-\d{2}-\d{2}\b",
        "",
        text,
    )

    matches = re.findall(
        r"-?\d+(?:,\d{3})*(?:\.\d+)?",
        text_without_dates,
    )

    numbers = []

    for value in matches:
        cleaned = value.replace(",", "")
        numbers.append(float(cleaned))

    return numbers


def get_allowed_numbers(kpis: dict) -> set[float]:
    """Build the set of numeric values Gemini is allowed to mention."""
    allowed = set()

    for value in kpis.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric = float(value)

            # Signed growth and decline wording may use the same magnitude.
            for supported in (numeric, abs(numeric)):
                allowed.add(supported)
                allowed.add(round(supported, 1))
                allowed.add(round(supported, 2))
        elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            # Only valid structured dates support prose such as "August 2018".
            # Free text and numeric-looking strings do not authorize numbers.
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                continue
            allowed.update((float(parsed.year), float(parsed.month), float(parsed.day)))

    return allowed


def validate_generated_numbers(insights, kpis: dict) -> None:
    """
    Reject generated commentary containing numeric values
    that are not supported by the KPI payload.
    """

    text = " ".join(
        [
            insights.headline,
            insights.summary,
            *insights.key_observations,
            insights.watchout,
        ]
    )

    generated_numbers = extract_numbers(text)
    allowed_numbers = get_allowed_numbers(kpis)

    unsupported = [
        number
        for number in generated_numbers
        if number not in allowed_numbers
    ]

    if unsupported:
        raise ValueError(
            f"AI response contains unsupported numeric values: {unsupported}"
        )
