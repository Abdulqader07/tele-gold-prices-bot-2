import requests
from config import config

# The gold price API rejects requests without a browser-like User-Agent.
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'}


class GoldPriceFetcher:
    def __init__(self):
        self.api_url = config.GOLD_API

    def fetchPrice(self):
        try:
            response = requests.get(self.api_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f'Error fetching gold price: {e}')
            return None

        if 'price' not in data:
            print(f'Unexpected API response: {data}')
            return None

        try:
            return float(data['price'])
        except (TypeError, ValueError):
            print(f'Invalid price value: {data["price"]}')
            return None