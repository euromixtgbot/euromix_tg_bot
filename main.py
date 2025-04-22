#!/usr/bin/env python3
import logging
import os
import ssl
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

from config import TOKEN, WEBHOOK_URL, SSL_CERT_PATH, SSL_KEY_PATH
import handlers

logging.basicConfig(level=logging.INFO)

async def error_handler(update, context):
    logging.error(f"Update {update} caused error {context.error}")

if __name__ == "__main__":
    # Налаштовуємо SSL‑контекст з TLS1.2+
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.options |= ssl.OP_NO_TLSv1       # вимикаємо TLSv1.0
    ssl_context.options |= ssl.OP_NO_TLSv1_1     # вимикаємо TLSv1.1
    ssl_context.load_cert_chain(
        certfile=SSL_CERT_PATH,
        keyfile=SSL_KEY_PATH
    )

    # Ініціалізуємо та налаштовуємо бота
    app = ApplicationBuilder().token(TOKEN).build()

    # Хендлери
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
    app.add_error_handler(error_handler)

    # Запускаємо webhook з SSL‑контекстом
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        ssl_context=ssl_context,
    )
