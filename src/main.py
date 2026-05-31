# main.py for the main entry point of the bot, setting up the Telegram bot and scheduling price checks

import asyncio
from telegram.ext import Application, CommandHandler
from bot import (
    start, price, gram, unsubscribe, status, removeSubscriber,
    donate, help, threshold, subscribers, broadcast
)
from alert import Alert
from config import config
from http import web
import json
from datetime import datetime

alert = Alert()

async def setCommands(application: Application):
    commands = [
        ('start', 'Subscribe to gold prices alerts'),
        ('price', 'Get current gold price'),
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
        await alert.sendAlerts()
        await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)  # Sleep for the configured interval in minutes

# Health check endpoint for Render
async def health_check(request):
    return web.Response(
        text=json.dumps({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "bot_running": True
        }),
        content_type="application/json"
    )

# Root endpoint
async def root(request):
    return web.Response(
        text=json.dumps({
            "name": "Gold Price Bot",
            "version": "1.0.0",
            "status": "running"
        }),
        content_type="application/json"
    )

async def run_health_server():
    """Run a separate web server for health checks"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', root)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.HEALTH_PORT or 8080)
    await site.start()
    print(f"Health check server running on port {config.HEALTH_PORT or 8080}")
    
    # Keep the server running
    await asyncio.Event().wait()


def main():
    if hasattr(config, 'WEBHOOK_URL') and config.WEBHOOK_URL:
        # Run health server in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(run_health_server())


    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('price', price))
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

    loop.create_task(price_check_loop())  # Start the price check loop

    if hasattr(config, 'WEBHOOK_URL') and config.WEBHOOK_URL:
        print("Running in webhook mode")
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=f"/webhook/{config.BOT_TOKEN}",
            webhook_url=f"{config.WEBHOOK_URL}/webhook/{config.BOT_TOKEN}"
        )
    else:
        print("No WEBHOOK_URL configured, running in polling mode")
        application.run_polling()

if __name__ == '__main__':
    main()