# alert.py for the algorithm that checks for price changes and sends alerts to subscribers

from datetime import datetime, timedelta

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

    def checkPriceChange(self):
        current_price = fetcher.fetchPrice()
        
        if current_price is None:
            return None  # Failed to fetch price, skip alerting
        
        last_prices = database.getLastNPrices(5)

        if None in last_prices or len(last_prices) < 5:
            return None  # Not enough historical data to compare, skip alerting
        
        max_price = max(last_prices)
        min_price = min(last_prices)

        max_diff = abs(current_price - max_price) / max_price * 100
        min_diff = abs(current_price - min_price) / min_price * 100

        remaining_cooldown = database.checkCooldown()

        if remaining_cooldown > 0:
            return None  # Still in cooldown, skip alerting

        if max_diff >= min_diff:
            if max_diff >= config.DIFF_THRESHOLD:
                # Set cooldown for 60 minutes from now
                expiry = datetime.now() + timedelta(minutes=120)
                database.setCooldown(expiry.isoformat())

                self.sendNotification(difference=max_diff, direction="UP", current_price=current_price, reference_price=max_price)
                
                return True
        else:
            if min_diff >= config.DIFF_THRESHOLD:
                expiry = datetime.now() + timedelta(minutes=120)
                database.setCooldown(expiry.isoformat())

                self.sendNotification(difference=min_diff, direction="DOWN", current_price=current_price, reference_price=min_price)
                
                return True
            
        return None  # No significant change
    

    async def sendNotification(self, context=None, difference=None, direction=None, current=None, price=None):
        subscribers = database.getSubscribers()

        for subscriber in subscribers:
            if subscriber['is_active']:
                try:
                    message = f"Alert: Gold price has changed by {difference:.2f}% {direction}!\n<b>Current price: ${current:.2f}</b> per ounce\n<b>Reference price: ${price:.2f}</b> per ounce"
                    await context.bot.send_message(chat_id=subscriber['chat_id'], text=message, parse_mode='HTML')                    
                except Exception as e:
                    print(f"Error formatting alert message: {e}")
