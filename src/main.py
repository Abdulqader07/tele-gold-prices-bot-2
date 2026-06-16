# main.py for the main entry point of the bot, setting up the Telegram bot and scheduling price checks

import asyncio
import health
from telegram.ext import Application, CommandHandler
from bot import (
    start, price, gram, unsubscribe, status, removeSubscriber,
    donate, help, threshold, subscribers, broadcast, prices 
)
from alert import Alert
from config import config

alert = Alert()

async def setCommands(application: Application):
    commands = [
        ('start', 'Subscribe to gold prices alerts'),
        ('price', 'Get current gold price'),
        ('prices', 'Get last n gold prices (usage: /prices <n>)'),
        ('gram', 'Get gold price per gram for specified karat (usage: /gram <24|22|18>)'),
        ('unsubscribe', 'Unsubscribe from gold price alerts'),
        ('status', 'Get bot status (admin only)'),
        ('remove', 'Remove a subscriber (admin only, usage: /remove <chat_id>)'),
        ('threshold', 'Set price threshold (admin only, usage: /threshold <price>)'),
        ('subscribers', 'List all subscribers (admin only)'),
        ('broadcast', 'Broadcast a message to all subscribers (admin only, usage: /broadcast <message>)'),
        ('donate', 'Get donation information'),
        ('help', 'Show help message')
    ]

    await application.bot.set_my_commands(commands)

async def price_check_loop():
    while True:
        try:
            await alert.checkPriceChange()

        except Exception as e:
            print(f"Error in price check loop: {e}")
        
        await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)

def main():
    application = Application.builder().token(config.BOT_TOKEN).build()

    alert.bot = application.bot

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('price', price))
    application.add_handler(CommandHandler('prices', prices))
    application.add_handler(CommandHandler('gram', gram))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('remove', removeSubscriber))
    application.add_handler(CommandHandler('threshold', threshold))
    application.add_handler(CommandHandler('subscribers', subscribers))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('donate', donate))
    application.add_handler(CommandHandler('help', help))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setCommands(application))

    loop.create_task(price_check_loop())
    
    application.run_polling()

if __name__ == '__main__':
    main()
