from datetime import datetime, timedelta

from config import config
from database import database
from fetch import GoldPriceFetcher

fetcher = GoldPriceFetcher()


class Alert:
    def __init__(self):
        self.cooldown_minutes = config.COOLDOWN_MINUTES
        self.threshold = config.DIFF_THRESHOLD  # percent
        self.bot = None

    async def checkPriceChange(self):
        current = fetcher.fetchPrice()
        if current is None:
            return None

        database.savePrice(current)
        recent = database.getLastNPrices(5)
        if len(recent) < 5:
            return None

        if database.checkCooldown() > 0:
            return None

        high = max(recent)
        low = min(recent)
        change_from_high = abs(current - high) / high * 100
        change_from_low = abs(current - low) / low * 100

        if change_from_high >= change_from_low:
            change, direction, reference = change_from_high, 'DOWN', high
        else:
            change, direction, reference = change_from_low, 'UP', low

        if change < self.threshold:
            return None

        expiry = datetime.now() + timedelta(minutes=self.cooldown_minutes)
        database.setCooldown(expiry.isoformat())

        await self.sendNotification(
            difference=change,
            direction=direction,
            current_price=current,
            reference_price=reference,
        )
        return True

    async def sendNotification(self, difference, direction, current_price, reference_price):
        if self.bot is None:
            print('Bot not set on Alert; skipping notification.')
            return

        text = (
            f'Alert: Gold price moved {difference:.2f}% {direction}.\n'
            f'<b>Current: ${current_price:.2f}/oz</b>\n'
            f'<b>Reference: ${reference_price:.2f}/oz</b>'
        )

        for subscriber in database.getSubscribers():
            if not subscriber['is_active']:
                continue
            try:
                await self.bot.send_message(
                    chat_id=subscriber['chat_id'], text=text, parse_mode='HTML'
                )
            except Exception as e:
                print(f'Error sending to {subscriber["chat_id"]}: {e}')