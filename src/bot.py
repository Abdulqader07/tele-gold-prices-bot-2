import requests
import time
import traceback
from datetime import datetime

from config import config
import database as db

def send_message(chat_id, text):
    try:
        url = f'https://api.telegram.org/bot{config.TOKEN}/sendMessage'
        response = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def send_to_all_subscribers(message):
    try:
        subs = db.get_all_subscribers()
        success_count = 0
        for sub in subs:
            if send_message(sub[0], message):
                success_count += 1
            time.sleep(0.05)
        print(f"Sent alert to {success_count}/{len(subs)} subscribers")
    except Exception as e:
        print(f"Error in send_to_all_subscribers: {e}")

def get_gold_price():
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'}
    try:
        response = requests.get(config.GOLD_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def check_and_alert():
    """
    Checks gold price and sends alerts based on daily min/max.
    Uses database cooldown tracking instead of time.sleep().
    """
    try:
        current = get_gold_price()
        
        if current is None:
            print("Could not fetch price")
            return
        
        # Check cooldown FIRST (non-blocking)
        can_send, remaining_seconds = db.can_send_alert()
        if not can_send:
            print(f"Cooldown active: {remaining_seconds/60:.1f} minutes remaining")
            return
        
        last_price = db.get_last_price()
        
        if last_price is None:
            print(f"First price recorded: ${current:.2f}")
            db.save_price(current)
            return
        
        min_price, max_price = db.get_todays_range()
        
        db.save_price(current)
        db.update_daily_range(current)

        if min_price is None or max_price is None:
            print(f"First price of the day: ${current:.2f}")
            return

        up_from_min = ((current - min_price) / min_price) * 100
        down_from_max = ((max_price - current) / max_price) * 100

        max_change = max(up_from_min, down_from_max)
        
        should_alert = False
        direction = None
        move_percent = None
        trigger = None
        
        if max_change >= config.ALERT_PERCENT:
            if up_from_min > down_from_max:
                should_alert = True
                direction = "UP"
                move_percent = up_from_min
                trigger = f"from daily low of ${min_price:.2f}"
            elif down_from_max > up_from_min:
                should_alert = True
                direction = "DOWN"
                move_percent = down_from_max
                trigger = f"from daily high of ${max_price:.2f}"
            else:
                # Equal movement from both sides (rare)
                print(f"Equal movement: UP:{up_from_min:.2f}% DOWN:{down_from_max:.2f}%")
        
        if should_alert:
            total_range = max_price - min_price
            message = f"""
GOLD MOVEMENT ALERT

Price: ${current:.2f}
Moved {direction} {move_percent:.2f}% {trigger}

Today's Range:
Low: ${min_price:.2f}
High: ${max_price:.2f}
Total range: ${total_range:.2f}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            send_to_all_subscribers(message)
            db.log_alert(current, move_percent, direction)
            db.mark_alert_sent()  # Start cooldown
            print(f"Alert sent - {direction} {move_percent:.2f}% move | Cooldown: {db.get_cooldown_minutes()} min")
        else:
            print(f"No alert - Current: ${current:.2f} | Move: {max_change:.2f}% (need {config.ALERT_PERCENT}%)")
    
    except Exception as e:
        print(f"Error in check_and_alert: {e}")
        traceback.print_exc()

def backup_to_telegram():
    try:
        import os
        if not os.path.exists('database.db'):
            print("No database to backup")
            return False
        
        sub_count = db.get_subscriber_count()
        last_price = db.get_last_price()
        min_price, max_price = db.get_todays_range()
        cooldown_remaining = db.get_cooldown_remaining()
        
        backup_text = f"""
<b>GoldBot Daily Backup</b>

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Subscribers: {sub_count}
Last price: ${last_price if last_price else 'N/A'}
Alert threshold: {config.ALERT_PERCENT}%
Cooldown: {db.get_cooldown_minutes()} min
Cooldown remaining: {cooldown_remaining} min

Today's Range:
Low: ${min_price if min_price else 'N/A'}
High: ${max_price if max_price else 'N/A'}

Backup completed successfully
        """
        
        url = f'https://api.telegram.org/bot{config.TOKEN}/sendMessage'
        requests.post(url, json={'chat_id': config.ADMIN_CHAT_ID, 'text': backup_text, 'parse_mode': 'HTML'}, timeout=10)
        
        with open('database.db', 'rb') as f:
            files = {'document': f}
            requests.post(url, data={'chat_id': config.ADMIN_CHAT_ID}, files=files, timeout=30)
        
        print(f"Telegram backup sent at {datetime.now()}")
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False