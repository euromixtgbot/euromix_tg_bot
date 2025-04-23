#!/usr/bin/env python3
import logging
import os
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from config import TOKEN, WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH
import handlers

# Logging
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
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handlers.handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
app.add_error_handler(error_handler)

# Run as webhook
app.run_webhook(
    listen="127.0.0.1",  # вместо 0.0.0.0
    port=8443,
    url_path="webhook",
    webhook_url=WEBHOOK_URL,  # всё так же https://botemix.com/webhook
    cert=None,  # Убери сертификаты — теперь их обрабатывает nginx
    key=None,
)

if __name__ == "__main__":
    main()
