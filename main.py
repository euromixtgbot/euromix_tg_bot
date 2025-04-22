#!/usr/bin/env python3
import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

from config import TOKEN
import handlers

# Логування
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
    """Запускаємо бота у режимі long polling — без SSL‑конфігів вебхуку."""
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
    app.add_error_handler(error_handler)

    # Перехід на polling замість webhook
    app.run_polling()

if __name__ == "__main__":
    main()
    