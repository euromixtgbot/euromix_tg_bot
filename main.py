#!/usr/bin/env python3
import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError
from aiohttp import web

import handlers
from config import TOKEN, WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and update.message:
        try:
            await update.message.reply_text("⚠️ Сталася помилка. Спробуйте знову.")
        except Exception:
            pass

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # передаємо bot у aiohttp app для handlers.jira_webhook
    application.bot_app['bot'] = application.bot

    # Telegram-хендлери
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(MessageHandler(filters.ALL, handlers.universal_handler))
    application.add_error_handler(error_handler)

    # додаємо маршрут для Jira
    application.bot_app.router.add_post("/jira-webhook", handlers.jira_webhook)

    # запускаємо webhook (Telegram)
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        cert=SSL_CERT_PATH,
        key=SSL_KEY_PATH,
    )

if __name__ == "__main__":
    main()
