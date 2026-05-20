# database.py
import sqlite3
import threading
import time
from datetime import datetime
from config import config 

# SQLite file for local fallback
DB_FILE = 'database.db'

# Try to import Supabase if configured
supabase_client = None
try:
    if config.USE_SUPABASE and config.SUPABASE_URL and config.SUPABASE_KEY:
        from supabase import create_client
        supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        print("Supabase client initialized")
except ImportError:
    print("Supabase package not installed. Using SQLite only.")
except Exception as e:
    print(f"Supabase initialization error: {e}")

# ============================================================
# SINGLETON DATABASE MANAGER
# ============================================================

class DatabaseManager:
    """
    Singleton pattern for database connection management.
    Ensures only one connection instance per thread exists.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._local = threading.local()
        self._connection_lock = threading.Lock()
        self._alert_lock = threading.Lock()
        self._last_alert_time = 0
        self._alert_cooldown_minutes = getattr(config, 'ALERT_COOLDOWN_MINUTES', 30)
    
    def get_connection(self):
        """Get or create a connection for the current thread"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            with self._connection_lock:
                if not hasattr(self._local, 'connection') or self._local.connection is None:
                    self._local.connection = sqlite3.connect(DB_FILE, check_same_thread=False)
                    self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def close_connection(self):
        """Close the connection for the current thread"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def can_send_alert(self):
        """Check if enough time has passed since last alert (cooldown)"""
        with self._alert_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_alert_time
            cooldown_seconds = self._alert_cooldown_minutes * 60
            
            if time_since_last >= cooldown_seconds:
                return True, 0
            else:
                remaining = cooldown_seconds - time_since_last
                return False, remaining
    
    def mark_alert_sent(self):
        """Update the last alert timestamp"""
        with self._alert_lock:
            self._last_alert_time = time.time()
    
    def get_cooldown_minutes(self):
        """Get the current cooldown setting"""
        return self._alert_cooldown_minutes

# Create singleton instance
db_manager = DatabaseManager()

# ============================================================
# SQLITE FUNCTIONS (using Singleton)
# ============================================================

def init_sqlite():
    try:
        conn = db_manager.get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS daily_range (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                min_price REAL,
                max_price REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                move_percent REAL,
                direction TEXT
            )
        ''')
        conn.commit()
        print("SQLite database initialized")
        return True
    except Exception as e:
        print(f"SQLite initialization error: {e}")
        return False

def get_sqlite_connection():
    """Returns connection from singleton manager"""
    return db_manager.get_connection()

# ============================================================
# SUPABASE FUNCTIONS (Production)
# ============================================================

def supabase_add_subscriber(chat_id, username, first_name):
    try:
        data = {
            "chat_id": chat_id,
            "username": username,
            "first_name": first_name,
            "subscribed_at": datetime.now().isoformat()
        }
        supabase_client.table("subscribers").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Supabase add_subscriber error: {e}")
        return False

def supabase_remove_subscriber(chat_id):
    try:
        supabase_client.table("subscribers").delete().eq("chat_id", chat_id).execute()
        return True
    except Exception as e:
        print(f"Supabase remove_subscriber error: {e}")
        return False

def supabase_get_all_subscribers():
    try:
        result = supabase_client.table("subscribers").select("*").execute()
        return [(row['chat_id'], row['username'], row['first_name'], row['subscribed_at']) for row in result.data]
    except Exception as e:
        print(f"Supabase get_all_subscribers error: {e}")
        return []

def supabase_get_subscriber_count():
    try:
        result = supabase_client.table("subscribers").select("*", count="exact").execute()
        return result.count or 0
    except Exception as e:
        print(f"Supabase get_subscriber_count error: {e}")
        return 0

def supabase_save_price(price):
    try:
        data = {
            "price": price,
            "recorded_at": datetime.now().isoformat()
        }
        supabase_client.table("price_history").insert(data).execute()
        return True
    except Exception as e:
        print(f"Supabase save_price error: {e}")
        return False

def supabase_get_last_price():
    try:
        result = supabase_client.table("price_history").select("price").order("recorded_at", desc=True).limit(1).execute()
        return result.data[0]['price'] if result.data else None
    except Exception as e:
        print(f"Supabase get_last_price error: {e}")
        return None

def supabase_get_price_history_count():
    try:
        result = supabase_client.table("price_history").select("*", count="exact").execute()
        return result.count or 0
    except Exception as e:
        print(f"Supabase get_price_history_count error: {e}")
        return 0

def supabase_update_daily_range(price):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        existing = supabase_client.table("daily_range").select("min_price,max_price").eq("date", today).execute()
        
        if not existing.data:
            supabase_client.table("daily_range").insert({
                "date": today,
                "min_price": price,
                "max_price": price
            }).execute()
        else:
            current_min = existing.data[0]['min_price']
            current_max = existing.data[0]['max_price']
            supabase_client.table("daily_range").update({
                "min_price": min(current_min, price),
                "max_price": max(current_max, price)
            }).eq("date", today).execute()
        return True
    except Exception as e:
        print(f"Supabase update_daily_range error: {e}")
        return False

def supabase_get_todays_range():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        result = supabase_client.table("daily_range").select("min_price,max_price").eq("date", today).execute()
        if result.data:
            return result.data[0]['min_price'], result.data[0]['max_price']
        return None, None
    except Exception as e:
        print(f"Supabase get_todays_range error: {e}")
        return None, None

def supabase_log_alert(price, move_percent, direction):
    """Log alert to Supabase for history"""
    try:
        data = {
            "alert_time": datetime.now().isoformat(),
            "price": price,
            "move_percent": move_percent,
            "direction": direction
        }
        supabase_client.table("alert_log").insert(data).execute()
        return True
    except Exception as e:
        print(f"Supabase log_alert error: {e}")
        return False

# ============================================================
# ALERT FUNCTIONS (Now using cooldown instead of daily limit)
# ============================================================

def already_alerted_today():
    """
    REPLACED: Now checks cooldown instead of daily limit.
    Returns True if alert is still in cooldown (cannot send new alert).
    """
    can_send, _ = db_manager.can_send_alert()
    return not can_send  # Return True if we CANNOT send (cooldown active)

def mark_alerted_today():
    """
    REPLACED: Now marks the time of last alert for cooldown tracking.
    Also logs the alert to database.
    """
    db_manager.mark_alert_sent()
    return True

def get_cooldown_remaining():
    """Get remaining cooldown time in minutes"""
    can_send, remaining_seconds = db_manager.can_send_alert()
    if can_send:
        return 0
    return round(remaining_seconds / 60, 1)

# ============================================================
# UNIFIED DATABASE FUNCTIONS (Auto-detect backend)
# ============================================================

def init_db():
    if config.USE_SUPABASE and supabase_client:
        print("Using Supabase as database backend")
        print("NOTE: Please create the alert_log table in Supabase SQL editor:")
        print("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id SERIAL PRIMARY KEY,
            alert_time TIMESTAMP DEFAULT NOW(),
            price DECIMAL(10,2),
            move_percent DECIMAL(5,2),
            direction VARCHAR(10)
        );
        """)
        return True
    else:
        print("Using SQLite as database backend with Singleton pattern")
        return init_sqlite()

def add_subscriber(chat_id, username, first_name):
    if config.USE_SUPABASE and supabase_client:
        return supabase_add_subscriber(chat_id, username, first_name)
    else:
        try:
            conn = db_manager.get_connection()
            conn.execute('INSERT OR IGNORE INTO subscribers (chat_id, username, first_name) VALUES (?, ?, ?)',
                        (chat_id, username, first_name))
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite add_subscriber error: {e}")
            return False

def remove_subscriber(chat_id):
    if config.USE_SUPABASE and supabase_client:
        return supabase_remove_subscriber(chat_id)
    else:
        try:
            conn = db_manager.get_connection()
            conn.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite remove_subscriber error: {e}")
            return False

def get_all_subscribers():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_all_subscribers()
    else:
        try:
            conn = db_manager.get_connection()
            subs = conn.execute('SELECT chat_id, username, first_name, subscribed_at FROM subscribers').fetchall()
            return subs
        except Exception as e:
            print(f"SQLite get_all_subscribers error: {e}")
            return []

def get_subscriber_count():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_subscriber_count()
    else:
        try:
            conn = db_manager.get_connection()
            count = conn.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0]
            return count
        except Exception:
            return 0

def save_price(price):
    if config.USE_SUPABASE and supabase_client:
        return supabase_save_price(price)
    else:
        try:
            conn = db_manager.get_connection()
            conn.execute('INSERT INTO price_history (price) VALUES (?)', (price,))
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite save_price error: {e}")
            return False

def get_last_price():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_last_price()
    else:
        try:
            conn = db_manager.get_connection()
            result = conn.execute('SELECT price FROM price_history ORDER BY recorded_at DESC LIMIT 1').fetchone()
            return result[0] if result else None
        except Exception:
            return None

def get_price_history_count():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_price_history_count()
    else:
        try:
            conn = db_manager.get_connection()
            count = conn.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
            return count
        except Exception:
            return 0

def update_daily_range(price):
    if config.USE_SUPABASE and supabase_client:
        return supabase_update_daily_range(price)
    else:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = db_manager.get_connection()
            existing = conn.execute('SELECT min_price, max_price FROM daily_range WHERE date = ?', (today,)).fetchone()
            
            if existing is None:
                conn.execute('INSERT INTO daily_range (date, min_price, max_price) VALUES (?, ?, ?)',
                            (today, price, price))
            else:
                current_min, current_max = existing
                conn.execute('UPDATE daily_range SET min_price = ?, max_price = ? WHERE date = ?',
                            (min(current_min, price), max(current_max, price), today))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite update_daily_range error: {e}")
            return False

def get_todays_range():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_todays_range()
    else:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = db_manager.get_connection()
            result = conn.execute('SELECT min_price, max_price FROM daily_range WHERE date = ?', (today,)).fetchone()
            return (result['min_price'], result['max_price']) if result else (None, None)
        except Exception:
            return None, None
        
def save_last_alerted_percent(percent):
    """Save the last alerted movement percentage to prevent repeat alerts"""
    if config.USE_SUPABASE and supabase_client:
        try:
            supabase_client.table("bot_settings").upsert({
                "key": "last_alerted_percent",
                "value": str(percent)
            }).execute()
        except:
            pass
    else:
        try:
            conn = db_manager.get_connection()
            conn.execute('INSERT OR REPLACE INTO bot_settings (key, value) VALUES ("last_alerted_percent", ?)', (str(percent),))
            conn.commit()
        except Exception as e:
            print(f"Error saving last alerted percent: {e}")

def get_last_alerted_percent():
    """Get the last alerted movement percentage"""
    if config.USE_SUPABASE and supabase_client:
        try:
            result = supabase_client.table("bot_settings").select("value").eq("key", "last_alerted_percent").execute()
            return float(result.data[0]['value']) if result.data else None
        except:
            return None
    else:
        try:
            conn = db_manager.get_connection()
            result = conn.execute('SELECT value FROM bot_settings WHERE key = "last_alerted_percent"').fetchone()
            return float(result[0]) if result else None
        except:
            return None