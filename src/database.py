from datetime import datetime
from supabase import create_client

from config import config

_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self.supabase = _client
        self._initialized = True

    def addSubscriber(self, chat_id, username, fname):
        try:
            existing = self.supabase.table('subscribers') \
                .select('chat_id').eq('chat_id', chat_id).execute()

            if existing.data:
                response = self.supabase.table('subscribers') \
                    .update({'is_active': True}).eq('chat_id', chat_id).execute()
                return len(response.data) > 0

            data = {
                'chat_id': chat_id,
                'username': username or 'no_username',
                'first_name': fname,
                'is_active': True,
                'subscribed_at': datetime.now().isoformat(),
                'role': 'user',
            }
            response = self.supabase.table('subscribers').insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f'Error adding subscriber: {e}')
            return False

    def getSubscribers(self):
        try:
            response = self.supabase.table('subscribers').select('*').execute()
            return response.data or []
        except Exception as e:
            print(f'Error fetching subscribers: {e}')
            return []

    def removeSubscriber(self, chat_id):
        try:
            response = self.supabase.table('subscribers') \
                .update({'is_active': False}).eq('chat_id', chat_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f'Error removing subscriber: {e}')
            return False

    def savePrice(self, price):
        try:
            self.supabase.table('historical_prices').insert({'price': price}).execute()
            return True
        except Exception as e:
            print(f'Error saving price: {e}')
            return False

    def getLastPrice(self):
        try:
            result = self.supabase.table('historical_prices') \
                .select('price').order('recorded_at', desc=True).limit(1).execute()
            return result.data[0]['price'] if result.data else None
        except Exception as e:
            print(f'Error fetching last price: {e}')
            return None

    def getLastNPrices(self, n):
        try:
            result = self.supabase.table('historical_prices') \
                .select('price').order('recorded_at', desc=True).limit(n).execute()
            return [float(row['price']) for row in result.data] if result.data else []
        except Exception as e:
            print(f'Error fetching last {n} prices: {e}')
            return []

    def setThreshold(self, threshold):
        try:
            self.supabase.table('bot_settings') \
                .upsert({'key': 'diff_threshold', 'value': str(threshold)}).execute()
            return True
        except Exception as e:
            print(f'Error setting threshold: {e}')
            return False

    def setCooldown(self, expires_at_iso):
        try:
            self.supabase.table('bot_settings') \
                .upsert({'key': 'cooldown_expiry', 'value': expires_at_iso}).execute()
            return True
        except Exception as e:
            print(f'Error setting cooldown: {e}')
            return False

    def checkCooldown(self):
        try:
            result = self.supabase.table('bot_settings') \
                .select('value').eq('key', 'cooldown_expiry').execute()
            if not result.data:
                return 0
            raw = result.data[0]['value']
            if not raw:
                return 0
            expiry = datetime.fromisoformat(raw)
            return max(0, (expiry - datetime.now()).total_seconds() / 60)
        except Exception as e:
            print(f'Error checking cooldown: {e}')
            return 0


database = Database()