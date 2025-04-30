#!/usr/bin/env python3
import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
from config import TOKEN
import handlers

# Завантаження змінних оточення з файлу .env
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and getattr(update, 'message', None):
        try:
            await update.message.reply_text("⚠️ Сталася помилка. Спробуйте знову.")
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # --- Командний хендлер — старт бота ---
    app.add_handler(
        CommandHandler("start", handlers.start)
    )

    # --- CallbackQueryHandler для інлайн-кнопок «comment_task_...» ---
    # Паттерн має точно відповідати префіксу, який ви задаєте в handlers.my­tickets_handler:
    app.add_handler(
        CallbackQueryHandler(
            handlers.handle_comment_callback,
            pattern=r"^comment_task_"
        )
    )

    # --- MessageHandler для тексту в режимі коментаря ---
    # Виконується першим (group=0), перед universal_handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.add_comment_handler
        ),
        group=0
    )

    # --- Основні обробники універсальних повідомлень (group=1) ---
    # Спочатку медіа → handlers.handle_media всередині universal_handler
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
            handlers.universal_handler
        ),
        group=1
    )
    # Потім будь-який інший текст → universal_handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.universal_handler
        ),
        group=1
    )

    # --- Обробник помилок ---
    app.add_error_handler(error_handler)

    # --- Старт polling ---
    app.run_polling()

if __name__ == "__main__":
    main()
