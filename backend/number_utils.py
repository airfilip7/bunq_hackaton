import re

_DUTCH_NUM_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")

_EUR_KEYS = {"gross_monthly_eur", "net_monthly_eur"}


def normalize_dutch_numbers(data: dict) -> dict:
    for key in _EUR_KEYS:
        val = data.get(key)
        if isinstance(val, str) and _DUTCH_NUM_RE.match(val):
            data[key] = float(val.replace(".", "").replace(",", "."))
    return data
