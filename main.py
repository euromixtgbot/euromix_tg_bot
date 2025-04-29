#!/usr/bin/env python3
import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,  # <-- Додаємо для inline кнопок!
    filters
)
from telegram.error import TelegramError
from dotenv import load_dotenv

from config import TOKEN
import handlers

# Завантаження змінних оточення
load_dotenv()

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

    # Обробники команд
    app.add_handler(CommandHandler("start", handlers.start))
    
    # Обробники повідомлень (медіа, текст)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handlers.universal_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.universal_handler))
    
    # Обробник callback-кнопок (inline-клавіатури)
    app.add_handler(CallbackQueryHandler(handlers.handle_comment_callback))

    # Обробник помилок
    app.add_error_handler(error_handler)

    # Стартуємо бота
    app.run_polling()

if __name__ == "__main__":
    main()
