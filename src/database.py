# database.py
import sqlite3
import traceback
from datetime import datetime

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
# SQLITE FUNCTIONS (Fallback)
# ============================================================

def init_sqlite():
    try:
        conn = sqlite3.connect(DB_FILE)
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
        conn.commit()
        conn.close()
        print("SQLite database initialized")
        return True
    except Exception as e:
        print(f"SQLite initialization error: {e}")
        return False

def get_sqlite_connection():
    return sqlite3.connect(DB_FILE)

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

def supabase_already_alerted_today():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        result = supabase_client.table("bot_settings").select("value").eq("key", "last_alert_date").execute()
        return result.data and result.data[0]['value'] == today
    except Exception as e:
        print(f"Supabase already_alerted_today error: {e}")
        return False

def supabase_mark_alerted_today():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        supabase_client.table("bot_settings").upsert({
            "key": "last_alert_date",
            "value": today
        }).execute()
        return True
    except Exception as e:
        print(f"Supabase mark_alerted_today error: {e}")
        return False

# ============================================================
# UNIFIED DATABASE FUNCTIONS (Auto-detect backend)
# ============================================================

def init_db():
    if config.USE_SUPABASE and supabase_client:
        print("Using Supabase as database backend")
        # Supabase tables are created via SQL migrations
        # You need to run the SQL script in Supabase SQL editor once
        return True
    else:
        print("Using SQLite as database backend")
        return init_sqlite()

def add_subscriber(chat_id, username, first_name):
    if config.USE_SUPABASE and supabase_client:
        return supabase_add_subscriber(chat_id, username, first_name)
    else:
        try:
            conn = get_sqlite_connection()
            conn.execute('INSERT OR IGNORE INTO subscribers (chat_id, username, first_name) VALUES (?, ?, ?)',
                        (chat_id, username, first_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite add_subscriber error: {e}")
            return False

def remove_subscriber(chat_id):
    if config.USE_SUPABASE and supabase_client:
        return supabase_remove_subscriber(chat_id)
    else:
        try:
            conn = get_sqlite_connection()
            conn.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite remove_subscriber error: {e}")
            return False

def get_all_subscribers():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_all_subscribers()
    else:
        try:
            conn = get_sqlite_connection()
            subs = conn.execute('SELECT chat_id, username, first_name, subscribed_at FROM subscribers').fetchall()
            conn.close()
            return subs
        except Exception as e:
            print(f"SQLite get_all_subscribers error: {e}")
            return []

def get_subscriber_count():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_subscriber_count()
    else:
        try:
            conn = get_sqlite_connection()
            count = conn.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

def save_price(price):
    if config.USE_SUPABASE and supabase_client:
        return supabase_save_price(price)
    else:
        try:
            conn = get_sqlite_connection()
            conn.execute('INSERT INTO price_history (price) VALUES (?)', (price,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"SQLite save_price error: {e}")
            return False

def get_last_price():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_last_price()
    else:
        try:
            conn = get_sqlite_connection()
            result = conn.execute('SELECT price FROM price_history ORDER BY recorded_at DESC LIMIT 1').fetchone()
            conn.close()
            return result[0] if result else None
        except Exception:
            return None

def get_price_history_count():
    if config.USE_SUPABASE and supabase_client:
        return supabase_get_price_history_count()
    else:
        try:
            conn = get_sqlite_connection()
            count = conn.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

def update_daily_range(price):
    if config.USE_SUPABASE and supabase_client:
        return supabase_update_daily_range(price)
    else:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = get_sqlite_connection()
            existing = conn.execute('SELECT min_price, max_price FROM daily_range WHERE date = ?', (today,)).fetchone()
            
            if existing is None:
                conn.execute('INSERT INTO daily_range (date, min_price, max_price) VALUES (?, ?, ?)',
                            (today, price, price))
            else:
                current_min, current_max = existing
                conn.execute('UPDATE daily_range SET min_price = ?, max_price = ? WHERE date = ?',
                            (min(current_min, price), max(current_max, price), today))
            
            conn.commit()
            conn.close()
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
            conn = get_sqlite_connection()
            result = conn.execute('SELECT min_price, max_price FROM daily_range WHERE date = ?', (today,)).fetchone()
            conn.close()
            return result if result else (None, None)
        except Exception:
            return None, None

def already_alerted_today():
    if config.USE_SUPABASE and supabase_client:
        return supabase_already_alerted_today()
    else:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = get_sqlite_connection()
            result = conn.execute('SELECT value FROM bot_settings WHERE key = "last_alert_date"').fetchone()
            conn.close()
            return result and result[0] == today
        except Exception:
            return False

def mark_alerted_today():
    if config.USE_SUPABASE and supabase_client:
        return supabase_mark_alerted_today()
    else:
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = get_sqlite_connection()
            conn.execute('INSERT OR REPLACE INTO bot_settings (key, value) VALUES ("last_alert_date", ?)', (today,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False