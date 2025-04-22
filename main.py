import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import TOKEN, WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH
import handlers

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Команди та хендлери
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))

    # Запускаємо webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        cert=SSL_CERT_PATH,
        key=SSL_KEY_PATH,
    )