#!/usr/bin/env python3
import logging, os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import handlers
from config import TOKEN, SSL_CERT_PATH, SSL_KEY_PATH, WEBHOOK_URL  # WEBHOOK_URL якщо потрібен

logging.basicConfig(level=logging.INFO)

async def error_handler(update, context):
    logging.error("Error:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("⚠️ Сталася помилка. Спробуйте пізніше.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
    app.add_error_handler(error_handler)

    # для локального polling
    app.run_polling()

if __name__=="__main__":
    main()
