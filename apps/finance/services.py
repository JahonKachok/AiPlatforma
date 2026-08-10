import requests

CBU_USD_RATE_URL = "https://cbu.uz/en/arkhiv-kursov-valyut/json/USD/"


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
