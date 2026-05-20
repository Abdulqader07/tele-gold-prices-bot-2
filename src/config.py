# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:8080/webhook')
    GOLD_API_URL = "https://api.gold-api.com/price/XAU"
    ALERT_PERCENT = 0.3
    CHECK_INTERVAL = 10
    ALERT_COOLDOWN_MINUTES = 0.5
    PORT = int(os.getenv('PORT', 8080))
    
    # Supabase configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    USE_SUPABASE = os.getenv('USE_SUPABASE', 'false').lower() == 'true'

config = Config()