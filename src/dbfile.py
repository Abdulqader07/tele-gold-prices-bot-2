# supabase database.py

from datetime import datetime
from config import config
from supabase import create_client, Client


supabase_client = None
use_supabase = False

if config.USE_SUPABASE and config.SUPABASE_URL and config.SUPABASE_KEY:
    try:
        supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        use_supabase = True
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        use_supabase = False

class Database:
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(Database, cls).__new__(cls)
        return cls.instance
    

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.supabase = supabase_client
            self.use_supabase = use_supabase

        if self.use_supabase:
            # Database is initialized, you can perform any setup if needed
            pass
        else:
            # Database is not available, you can set up a fallback mechanism if needed
            pass

    def addSubscriber(self, chat_id, username, fname):
        if not self.use_supabase:
            return False
        
        exist = self.supabase.table("subscribers").select("chat_id").eq("chat_id", chat_id)\
        .execute()

        if exist.data:
            response = self.supabase.table("subscribers").update({"is_active": True})\
            .eq("chat_id", chat_id).execute()

            return len(response.data) > 0
        
        try:
            data = {
                "chat_id": chat_id,
                "username": username,
                "first_name": fname,
                "is_active": True,
                "subscribed_at": datetime.now().isoformat(),
                "role": "user"
            }

            response = self.supabase.table("subscribers").insert(data).execute()
            return len(response.data) > 0
        
        except Exception as e:
            print(f"Error adding subscriber: {e}")
            return False
        
    def getSubscribers(self):
        if not self.use_supabase:
            return []
        
        try:
            response = self.supabase.table("subscribers").select("*").execute()
            if len(response.data) > 0:
                return response.data
            else:
                print(f"Error fetching subscribers")
                
                return []
        except Exception as e:
            print(f"Error fetching subscribers: {e}")
            
            return []
        
    def removeSubscriber(self, chat_id):
        if not self.use_supabase:
            return False
        
        try:
            response = self.supabase.table("subscribers").update({"is_active": False})\
            .eq("chat_id", chat_id).execute()
            
            return len(response.data) > 0
        
        except Exception as e:
            print(f"Error removing subscriber: {e}")
            return False
    
    def savePrice(self, price):
        if not self.use_supabase:
            return False
        
        try:
            data = {"price": price}
            result = self.supabase.table("historical_prices").insert(data).execute()

            return True
        
        except Exception as e:
            print(f"Error saving price: {e}")
            return False
        
    def getLastPrice(self):
        if not self.use_supabase:
            return None
        
        try:
            result = self.supabase.table("historical_prices").select("price")\
            .order("recorded_at", desc=True).limit(1).execute()

            if result.data:
                return result.data[0]["price"]
            
            return None
        
        except Exception as e:
            return None
    
    def setThreshold(self, threshold):
        if not self.use_supabase:
            return False
        
        try:
            result = self.supabase.table("bot_settings")\
            .upsert({"key": "diff_threshold", "value": str(threshold)})\
            .execute()

            return True
        
        except Exception as e:
            print(f"Error setting threshold: {e}")
            return False
        
    def getLastNPrices(self, n):
        if not self.use_supabase:
            return []

        try:
            result = self.supabase.table("historical_prices").select("price")\
            .order("recorded_at", desc=True).limit(n).execute()

            return [float(entry["price"]) for entry in result.data] if result.data else []
        
        except Exception as e:
            print(f"Error fetching last {n} prices: {e}")
            return []
        
    def setCooldown(self, date):
        if not self.use_supabase:
            return False
        
        try:
            result = self.supabase.table("bot_settings")\
            .upsert({"key": "cooldown_expiry", "value": date})\
            .execute()
    
            return True
        
        except Exception as e:
            print(f"Error setting cooldown: {e}")
            return False
        
    def checkCooldown(self):
        if not self.use_supabase:
            return None
        
        try:
            result = self.supabase.table("bot_settings").select("value")\
            .eq("key", "cooldown_expiry").execute()

            if not result.data:
                return 0
            
            expiry_str = result.data[0]["value"]
            expiry_time = datetime.fromisoformat(expiry_str)

            remaining = (expiry_time - datetime.now()).total_seconds() / 60
            
            return max(0, remaining)
        
        except Exception as e:
            print(f"Error fetching cooldown: {e}")
            return 0

# Create a singleton instance of the Database class
database = Database()

tables = [
    """
    CREATE TABLE IF NOT EXISTS subscribers (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        role TEXT DEFAULT 'user'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_prices (
        id SERIAL PRIMARY KEY,
        price NUMERIC NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT NOT NULL,
        price NUMERIC NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES subscribers(chat_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_prices (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        current_price NUMERIC NOT NULL,
        high NUMERIC NOT NULL,
        low NUMERIC NOT NULL,
        UNIQUE (date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_settings (
        id SERIAL PRIMARY KEY,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT NOT NULL
    );
    """
]