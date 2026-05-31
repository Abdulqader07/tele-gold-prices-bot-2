# alert.py for the algorithm that checks for price changes and sends alerts to subscribers

from fetch import GoldPriceFetcher
from dbfile import database
from config import config

fetcher = GoldPriceFetcher()

class Alert:
    def __init__(self):
        self.cooldown = config.COOLDOWN_MINUTES * 60  # Convert minutes to seconds

    def checkPrice(self):
        current_price = fetcher.fetchPrice()
        if current_price is None:
            return None, None, -1  # Failed to fetch price, skip alerting
        
        database.savePrice(current_price)  # Save the current price to the database
        last_price = database.getLastPrice()
        
        if last_price is None:
            return current_price, None, -1  # No previous price to compare, skip alerting

        price_diff = abs(current_price - last_price)
            
        if price_diff >= config.DIFF_THRESHOLD:  # Alert if price changes by the threshold or more
            return current_price, last_price, price_diff 
        
        return current_price, last_price, -1  # No significant change
    
    async def sendAlerts(self, context=None):
        subscribers = database.getSubscribers()
        current, last, diff = self.checkPrice()

        if diff == -1 or current is None or last is None:
            return
        
        for subscriber in subscribers:
            if subscriber['is_active']:
                try:
                    message = f"Alert: Gold price has changed by ${diff:.2f} or more!\n<b>Current price: ${current:.2f}</b> per ounce\n<b>Previous price: ${last:.2f}</b> per ounce"
                    await context.bot.send_message(chat_id=subscriber['chat_id'], text=message, parse_mode='HTML')                    
                except Exception as e:
                    print(f"Error formatting alert message: {e}")
