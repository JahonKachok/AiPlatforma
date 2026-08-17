import re

import requests

CBU_USD_RATE_URL = "https://cbu.uz/en/arkhiv-kursov-valyut/json/USD/"
POYTAXTBANK_RATES_URL = "https://poytaxtbank.uz/uz/services/exchange-rates/"

# A browser-like User-Agent, since the homepage (unlike this rates page)
# serves an empty stub to non-browser clients on a cold request.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
}

# The page repeats one exchange__table per branch; the first is the main
# office. Within it, the USD row lists buy rate, sell rate, then the bank's
# quoted CBU rate — e.g. <span>USD</span> ... <span>11805</span>
# ... <span>11940</span> ... <span>11891.18</span>.
_POYTAXTBANK_TABLE_RE = re.compile(r'<table class="exchange__table">(.*?)</table>', re.DOTALL)
_POYTAXTBANK_USD_ROW_RE = re.compile(
    r"<span>USD</span>.*?<span>([\d.]+)</span>.*?<span>([\d.]+)</span>.*?<span>([\d.]+)</span>",
    re.DOTALL,
)


def fetch_usd_rate():
    """Fetch today's official USD/UZS rate from the Central Bank of
    Uzbekistan. Returns a float, or None if the rate could not be fetched."""
    try:
        response = requests.get(CBU_USD_RATE_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data[0]["Rate"])
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None


def fetch_usd_rate_poytaxtbank():
    """Fetch today's USD/UZS sell rate from Poytaxt Bank's public exchange
    rates page. Returns a float, or None if the rate could not be fetched
    or parsed."""
    try:
        response = requests.get(POYTAXTBANK_RATES_URL, headers=_BROWSER_HEADERS, timeout=5)
        response.raise_for_status()
        table_match = _POYTAXTBANK_TABLE_RE.search(response.text)
        if not table_match:
            return None
        row_match = _POYTAXTBANK_USD_ROW_RE.search(table_match.group(1))
        if not row_match:
            return None
        _buy, sell, _cbu = row_match.groups()
        return float(sell)
    except (requests.RequestException, ValueError, AttributeError):
        return None
