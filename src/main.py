# main.py (same as before, no changes needed - database functions work the same)
import threading
import time
import os
import requests
from flask import Flask, request

from config import config
import database as db
import bot

app = Flask(__name__)

# Initialize database
db.init_db()

# === WEBHOOK HANDLER ===
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return 'ok', 200
        
        msg = data['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '')
        username = msg['from'].get('username', 'no_username')
        first_name = msg['from'].get('first_name', 'User')
        
        if text == '/start':
            if db.add_subscriber(chat_id, username, first_name):
                bot.send_message(chat_id, f"<b>{first_name}</b>, you're subscribed to gold price alerts!\n\n/price - Current price\n/unsubscribe - Stop alerts")
        elif text == '/price':
            price = bot.get_gold_price()
            if price:
                bot.send_message(chat_id, f"<b>Gold price:</b> ${price:.2f}")
            else:
                bot.send_message(chat_id, "Unable to fetch price")
        elif text == '/unsubscribe':
            if db.remove_subscriber(chat_id):
                bot.send_message(chat_id, "Unsubscribed. Send /start to resubscribe.")
        elif text == '/view' and chat_id == config.ADMIN_CHAT_ID:
            subs = db.get_all_subscribers()
            last_price = db.get_last_price()
            if not subs:
                bot.send_message(chat_id, "No subscribers yet.")
                return 'ok', 200
            message = f"<b>Subscribers ({len(subs)})</b>\nLast price: ${last_price if last_price else 'N/A'}\n\n"
            for i, sub in enumerate(subs, 1):
                message += f"{i}. <b>{sub[2]}</b> (@{sub[1]})\n"
            bot.send_message(chat_id, message)
        elif text == '/stats' and chat_id == config.ADMIN_CHAT_ID:
            sub_count = db.get_subscriber_count()
            price_count = db.get_price_history_count()
            last_price = db.get_last_price()
            min_price, max_price = db.get_todays_range()
            message = f"""
<b>Bot Statistics</b>

Subscribers: {sub_count}
Price checks: {price_count}
Last price: ${last_price if last_price else 'N/A'}
Alert threshold: {config.ALERT_PERCENT}%
Check interval: {config.CHECK_INTERVAL} min

Today's Range:
Low: ${min_price if min_price else 'N/A'}
High: ${max_price if max_price else 'N/A'}

Status: Online
            """
            bot.send_message(chat_id, message)
        elif text.startswith('/remove') and chat_id == config.ADMIN_CHAT_ID:
            parts = text.split()
            if len(parts) > 1:
                target = parts[1]
                if target.isdigit():
                    db.remove_subscriber(int(target))
                bot.send_message(chat_id, f"Removed {target}")
        else:
            bot.send_message(chat_id, "Commands:\n/start - Subscribe\n/price - Current price\n/unsubscribe - Stop alerts")
        
        return 'ok', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'ok', 200

@app.route('/health')
def health():
    return 'ok', 200

def set_webhook():
    try:
        url = f'https://api.telegram.org/bot{config.TOKEN}/setWebhook'
        response = requests.post(url, json={'url': config.WEBHOOK_URL})
        print(f"Webhook response: {response.json()}")
    except Exception as e:
        print(f"Error setting webhook: {e}")

def price_monitor_loop():
    print(f"Price monitor started - checking every {config.CHECK_INTERVAL} minutes")
    while True:
        try:
            bot.check_and_alert()
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(config.CHECK_INTERVAL * 60)

def backup_loop():
    print("Backup system started - backing up every 24 hours")
    while True:
        try:
            bot.backup_to_telegram()
        except Exception as e:
            print(f"Backup error: {e}")
        time.sleep(24 * 60 * 60)

def main():
    set_webhook()
    
    monitor_thread = threading.Thread(target=price_monitor_loop, daemon=True)
    monitor_thread.start()
    
    backup_thread = threading.Thread(target=backup_loop, daemon=True)
    backup_thread.start()
    
    print(f"Starting Flask app on port {config.PORT}")
    app.run(host='0.0.0.0', port=config.PORT)

if __name__ == '__main__':
    main()