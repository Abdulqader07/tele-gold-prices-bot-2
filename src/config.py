# config file for the project

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings
class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))  # Default to 0 if not set

    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    USE_SUPABASE = os.getenv('USE_SUPABASE', 'False').lower() == 'true'

    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 60)) # Default to 60 minutes if not set
    COOLDOWN_MINUTES = int(os.getenv('COOLDOWN_MINUTES', 40)) # Default to 40 minutes if not set
    DIFF_THRESHOLD = float(os.getenv('DIFF_THRESHOLD', 30)) # Default to 30.0 if not set
    PORT = int(os.getenv('PORT', 8080))
    HEALTH_PORT = int(os.getenv('HEALTH_PORT', 8080))

    GOLD_API = os.getenv('GOLD_API')
    
config = Config()