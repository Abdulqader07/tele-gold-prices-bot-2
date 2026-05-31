# fetch.py file for fetching gold price and sending to subscribers

import requests
from config import config

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'}


class GoldPriceFetcher:
    def __init__(self):
        self.api_url = config.GOLD_API

    def fetchPrice(self):
        try:
            response = requests.get(self.api_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            price = float(data.get("price"))

            return price
        
        except Exception as e:
            print(f"Error fetching gold price: {e}")
            return None