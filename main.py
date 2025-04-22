#!/usr/bin/env python3
import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

from config import TOKEN, WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH
import handlers

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Логування помилки та повідомлення користувачу."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and update.message:
        try:
            await update.message.reply_text(
                "⚠️ Сталася внутрішня помилка. Спробуйте знову."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

def main():
    """Точка входу — побудова та запуск бота через webhook."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Реєстрація хендлерів
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))

    # Обробник помилок
    app.add_error_handler(error_handler)

    # Запуск webhook із сертифікатом і ключем
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        cert=SSL_CERT_PATH,
        key=SSL_KEY_PATH,
    )

if __name__ == "__main__":
    main()
