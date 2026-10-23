import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    USE_SUPABASE = os.getenv('USE_SUPABASE', 'True').lower() == 'true'

    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 25))
    COOLDOWN_MINUTES = int(os.getenv('COOLDOWN_MINUTES', 40))
    DIFF_THRESHOLD = float(os.getenv('DIFF_THRESHOLD', 0.3))  # percent, e.g. 0.3 = 0.3%
    PORT = int(os.getenv('PORT', 8080))

    GOLD_API = os.getenv('GOLD_API')


config = Config()

if not config.BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN is not set')
if not config.USE_SUPABASE or not config.SUPABASE_URL or not config.SUPABASE_KEY:
    raise RuntimeError('Supabase is required: set USE_SUPABASE=True, SUPABASE_URL, SUPABASE_KEY')
if config.ADMIN_CHAT_ID == 0:
    print('Warning: ADMIN_CHAT_ID is 0 — admin commands will not work.')