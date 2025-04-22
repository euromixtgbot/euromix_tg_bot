# main.py
#!/usr/bin/env python3
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TOKEN
import handlers

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error("Exception while handling update:", exc_info=context.error)
    if update and update.message:
        try:
            await update.message.reply_text("⚠️ Сталася помилка. Спробуйте ще раз.")
        except Exception:
            pass


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()