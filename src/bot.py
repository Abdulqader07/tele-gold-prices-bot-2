# bot.py handler for telegram bot

import logging
from realtime import message
from telegram import Update
from telegram.ext import ContextTypes
from dbfile import database
from fetch import GoldPriceFetcher
from config import config

# Fetching price from official source
fetcher = GoldPriceFetcher()

# Handling bot commands

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    subscribers = database.getSubscribers()

    for subscriber in subscribers:
        if subscriber['chat_id'] == chat_id and subscriber['is_active']:
            await update.message.reply_text("You're already subscribed to gold price updates.")
            return

        elif subscriber['chat_id'] == chat_id and not subscriber['is_active']:
            database.addSubscriber(chat_id, user.username, user.first_name)
            await update.message.reply_text("Welcome back! You've been re-subscribed to gold price updates.")
            return
        elif subscriber['chat_id'] == chat_id and subscriber['is_active'] == False:
            database.addSubscriber(chat_id, user.username, user.first_name)
            await update.message.reply_text("Welcome back! You've been re-subscribed to gold price updates.")
            return
        

    if database.addSubscriber(chat_id, user.username, user.first_name):
        message = f'''
<b>Hello, {user.first_name}</b>, you're subscribed to gold prices bot!

Commands:

/price - Get current gold price
/unsubscribe - Unsubscribe from gold price updates
'''
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("Failed to subscribe. Please try again later.")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = fetcher.fetchPrice()
    if price is not None:
        await update.message.reply_text(f"Current gold price: ${price:.2f} per ounce")
    else:
        await update.message.reply_text("Failed to fetch gold price. Please try again later.")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not len(context.args) > 0:
        await update.message.reply_text("Usage: /prices 5 (returns last 5 price updates)")
        return
    
    try:
        count = int(context.args[0])
        prices = database.getLastPrices(count)
        if prices:
            message = "<b>Last {} gold price updates:\n</b>".format(count)
            for price in prices:
                message += f"${price:.2f} per ounce\n"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("No price data available.")
    except ValueError:
        await update.message.reply_text("Invalid argument. Please enter a valid number.")

async def gram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not len(context.args) > 0:
        await update.message.reply_text("Usage: /gram <24|22|18>\nExample: /gram 24")
        return
    
    price = fetcher.fetchPrice()
    
    if price is not None:
        if len(context.args) > 0:
            if context.args[0] == '24':
                price_per_gram = price / 31.1035
                await update.message.reply_text(f"Current gold price: ${price_per_gram:.2f} per gram")
            elif context.args[0] == '22':
                price_per_gram = (price * 22) / (31.1035 * 24)
                await update.message.reply_text(f"Current gold price: ${price_per_gram:.2f} per gram")
            elif context.args[0] == '21':
                price_per_gram = (price * 21) / (31.1035 * 24)
                await update.message.reply_text(f"Current gold price: ${price_per_gram:.2f} per gram")
            elif context.args[0] == '18':
                price_per_gram = (price * 18) / (31.1035 * 24)
                await update.message.reply_text(f"Current gold price: ${price_per_gram:.2f} per gram")
            else:
                await update.message.reply_text("Invalid argument. Use /gram 24, /gram 22, /gram 21, or /gram 18.")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if database.removeSubscriber(chat_id):
        await update.message.reply_text("You've been unsubscribed from gold price updates.")
    else:
        await update.message.reply_text("Failed to unsubscribe. Please try again later.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != config.ADMIN_CHAT_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    subscribers = database.getSubscribers()
    active_subscribers = [s for s in subscribers if s['is_active']]
    unactive_subscribers = [s for s in subscribers if not s['is_active']]

    message = f'''<b>Bot Status</b>

Total Subscribers: {len(subscribers)}

Active Subscribers: {len(active_subscribers)}

Inactive Subscribers: {len(unactive_subscribers)}

Last Gold Price: ${database.getLastPrice():.2f} per ounce
'''
    await update.message.reply_text(message, parse_mode='HTML')

async def removeSubscriber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id != config.ADMIN_CHAT_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /remove <chat_id>")
        return
    
    remove_chat_id = int(context.args[0])
    
    if database.removeSubscriber(remove_chat_id):
        await update.message.reply_text("Subscriber removed successfully.")
    else:
        await update.message.reply_text("Failed to remove subscriber. Please try again later.")

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = f'''<b>Support the Bot</b>

If you find this bot useful and would like to support its development, you can donate using the following methods:

- PayPal: [paypal.me/yourusername](https://paypal.me/yourusername)

- Bitcoin: `your-bitcoin-address`

- Ethereum: `your-ethereum-address`

Thank you for your support!'''
    await update.message.reply_text(message, parse_mode='HTML')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id == config.ADMIN_CHAT_ID:
        message = '''Available commands:

/start - Subscribe to gold price updates
/subscribers - List all subscribers (admin only)
/price - Get current gold price
/gram <24|22|21|18> - Get gold price per gram for specified karat
/unsubscribe - Unsubscribe from gold price updates
/status - Get bot status (admin only)
/remove <chat_id> - Remove a subscriber (admin only)
/threshold <price> - Set price threshold (admin only)
/broadcast <message> - Broadcast a message to all subscribers (admin only)
/donate - Get donation information
/help - Show this help message'''
    else:
        message = '''Available commands:

/start - Subscribe to gold price updates
/price - Get current gold price
/gram <24|22|21|18> - Get gold price per gram for specified karat
/unsubscribe - Unsubscribe from gold price updates
/donate - Get donation information
/help - Show this help message'''
    await update.message.reply_text(message)

async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != config.ADMIN_CHAT_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /threshold <price>")
        return
    
    try:
        threshold_price = float(context.args[0])
        database.setThreshold(threshold_price)
        await update.message.reply_text(f"Price threshold set to ${threshold_price:.2f}")
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a valid number.")

async def subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != config.ADMIN_CHAT_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    subscribers = database.getSubscribers()
    active_subscribers = [s for s in subscribers if s['is_active']]
    unactive_subscribers = [s for s in subscribers if not s['is_active']]

    active_list = ''
    inactive_list = ''

    for subs in active_subscribers[:20]:  # Show only first 20 active subscribers
        if subs['username'] == 'no_username':
            active_list += f"{subs['chat_id']} - {subs['first_name']}\n"
        else:
            active_list += f"{subs['chat_id']} - @{subs['username']} ({subs['first_name']})\n"

    for subs in unactive_subscribers[:20]:  # Show only first 20 inactive subscribers
        if subs['username'] == 'no_username':
            inactive_list += f"{subs['chat_id']} - {subs['first_name']} [Inactive]\n"
        else:
            inactive_list += f"{subs['chat_id']} - @{subs['username']} ({subs['first_name']}) [Inactive]\n"

    message = f'''<b>Subscribers List</b>

Active Subscribers:
{active_list if active_list else "No active subscribers."}

Inactive Subscribers:
{inactive_list if inactive_list else "No inactive subscribers."}'''

    await update.message.reply_text(message, parse_mode='HTML')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != config.ADMIN_CHAT_ID:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    broadcast_message = ' '.join(context.args)
    subscribers = database.getSubscribers()
    
    for subscriber in subscribers:
        if subscriber['is_active']:
            try:
                await context.bot.send_message(chat_id=subscriber["chat_id"], text=broadcast_message)
            except Exception as e:
                print(f"Error sending broadcast to {subscriber['chat_id']}: {e}")
